[CmdletBinding()]
param(
    [switch]$RunLivePipeline,
    [ValidateRange(100, 5000)]
    [int]$SampleIntervalMs = 500,
    [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"

function Assert-ExitCode {
    param([string]$Step, [int]$ExitCode)
    if ($ExitCode -ne 0) {
        throw "$Step failed with exit code $ExitCode."
    }
}

function Get-GzipLength {
    param([string]$Path)
    $bytes = [System.IO.File]::ReadAllBytes($Path)
    $stream = New-Object System.IO.MemoryStream
    try {
        $gzip = New-Object System.IO.Compression.GZipStream(
            $stream,
            [System.IO.Compression.CompressionMode]::Compress,
            $true
        )
        try {
            $gzip.Write($bytes, 0, $bytes.Length)
        } finally {
            $gzip.Dispose()
        }
        return [int64]$stream.Length
    } finally {
        $stream.Dispose()
    }
}

function Convert-ToMiB {
    param([string]$Value)
    if ($Value -notmatch '^([0-9.]+)(B|KiB|MiB|GiB)$') {
        throw "Unsupported Docker memory value '$Value'."
    }
    $amount = [double]$Matches[1]
    switch ($Matches[2]) {
        "B" { return $amount / 1MB }
        "KiB" { return $amount / 1KB }
        "MiB" { return $amount }
        "GiB" { return $amount * 1KB }
    }
}

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $repositoryRoot "frontend"
$routeStatsPath = Join-Path $frontendRoot ".next\diagnostics\route-bundle-stats.json"
$containerNames = @(
    "nusa-intel-db-1",
    "nusa-intel-api-1",
    "nusa-intel-worker-1",
    "nusa-intel-web-1"
)

if (-not (Test-Path -LiteralPath $routeStatsPath)) {
    throw "Production bundle statistics are missing. Run npm run build in frontend first."
}

$routeStats = Get-Content -Raw -LiteralPath $routeStatsPath | ConvertFrom-Json
$bundleRows = foreach ($route in $routeStats) {
    $gzipBytes = 0
    foreach ($relativeChunk in $route.firstLoadChunkPaths) {
        $chunkPath = Join-Path $frontendRoot $relativeChunk
        $gzipBytes += Get-GzipLength $chunkPath
    }
    [ordered]@{
        route = $route.route
        first_load_raw_bytes = [int64]$route.firstLoadUncompressedJsBytes
        first_load_gzip_bytes = [int64]$gzipBytes
    }
}

$pipelineProcess = $null
$pipelineStartedAt = $null
$pipelineDurationSeconds = $null
$resourceSamples = New-Object System.Collections.Generic.List[object]

Push-Location $repositoryRoot
try {
    if ($RunLivePipeline) {
        $pipelineStartedAt = Get-Date
        $pipelineProcess = Start-Process `
            -FilePath "docker" `
            -ArgumentList @(
                "compose", "exec", "-T", "worker", "python", "-m", "app.pipeline.cli",
                "--all", "--live"
            ) `
            -WindowStyle Hidden `
            -PassThru
    }

    do {
        $lines = docker stats --no-stream --format "{{json .}}" $containerNames
        Assert-ExitCode "Docker resource snapshot" $LASTEXITCODE
        $capturedAt = (Get-Date).ToUniversalTime().ToString("o")
        foreach ($line in $lines) {
            $row = $line | ConvertFrom-Json
            $usedMemory = ($row.MemUsage -split '/')[0].Trim()
            $resourceSamples.Add([pscustomobject][ordered]@{
                captured_at = $capturedAt
                container = $row.Name
                cpu_percent = [double]($row.CPUPerc.TrimEnd('%'))
                memory_mib = [math]::Round((Convert-ToMiB $usedMemory), 3)
                pids = [int]$row.PIDs
            })
        }
        if ($pipelineProcess -and -not $pipelineProcess.HasExited) {
            Start-Sleep -Milliseconds $SampleIntervalMs
            $pipelineProcess.Refresh()
        }
    } while ($pipelineProcess -and -not $pipelineProcess.HasExited)

    if ($pipelineProcess) {
        $pipelineProcess.WaitForExit()
        Assert-ExitCode "Live pipeline benchmark" $pipelineProcess.ExitCode
        $pipelineDurationSeconds = [math]::Round(
            ((Get-Date) - $pipelineStartedAt).TotalSeconds,
            3
        )
    }
} finally {
    Pop-Location
}

$containerSummary = foreach ($containerName in $containerNames) {
    $samples = @($resourceSamples | Where-Object { $_.container -eq $containerName })
    [ordered]@{
        container = $containerName
        samples = $samples.Count
        peak_cpu_percent = [math]::Round(
            [double](($samples | Measure-Object -Property cpu_percent -Maximum).Maximum),
            2
        )
        peak_memory_mib = [math]::Round(
            [double](($samples | Measure-Object -Property memory_mib -Maximum).Maximum),
            3
        )
    }
}

$result = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    live_pipeline = [bool]$RunLivePipeline
    pipeline_duration_seconds = $pipelineDurationSeconds
    bundles = @($bundleRows)
    resources = @($containerSummary)
}
$json = $result | ConvertTo-Json -Depth 6

if ($OutputPath) {
    $resolvedOutput = Join-Path $repositoryRoot $OutputPath
    $outputDirectory = Split-Path -Parent $resolvedOutput
    if (-not (Test-Path -LiteralPath $outputDirectory)) {
        New-Item -ItemType Directory -Path $outputDirectory | Out-Null
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($resolvedOutput, $json, $utf8NoBom)
}

Write-Output $json
