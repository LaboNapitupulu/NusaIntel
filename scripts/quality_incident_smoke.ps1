[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

function Assert-ExitCode {
    param([string]$Step, [int]$ExitCode)
    if ($ExitCode -ne 0) {
        throw "$Step failed with exit code $ExitCode."
    }
}

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$scratchDatabase = "nusa_intel_quality_case_smoke"
$expectedScratchDatabase = "nusa_intel_quality_case_smoke"
$caseScript = Join-Path $PSScriptRoot "quality_incident_case.py"
$fixture = Join-Path $repositoryRoot "tests\fixtures\bps\tpt_august_543_2023_2025_live.json"

if ($scratchDatabase -ne $expectedScratchDatabase) {
    throw "Refusing to operate on an unexpected database name."
}
if (-not (Test-Path -LiteralPath $caseScript)) {
    throw "Quality incident case script not found."
}
if (-not (Test-Path -LiteralPath $fixture)) {
    throw "Quality incident fixture not found."
}

Push-Location $repositoryRoot
try {
    docker compose exec -T db dropdb `
        --username=nusa_intel `
        --if-exists `
        $scratchDatabase
    Assert-ExitCode "Quality scratch cleanup" $LASTEXITCODE
    docker compose exec -T db createdb `
        --username=nusa_intel `
        $scratchDatabase
    Assert-ExitCode "Quality scratch creation" $LASTEXITCODE

    try {
        docker compose cp $caseScript worker:/tmp/quality_incident_case.py
        Assert-ExitCode "Quality case script copy" $LASTEXITCODE
        docker compose cp $fixture worker:/tmp/tpt_quality_case.json
        Assert-ExitCode "Quality fixture copy" $LASTEXITCODE
        docker compose exec -T worker python /tmp/quality_incident_case.py `
            --database $scratchDatabase `
            --fixture /tmp/tpt_quality_case.json
        Assert-ExitCode "Quality incident case" $LASTEXITCODE
    } finally {
        docker compose exec -T db dropdb `
            --username=nusa_intel `
            --if-exists `
            $scratchDatabase
        Assert-ExitCode "Quality scratch removal" $LASTEXITCODE
    }
} finally {
    Pop-Location
}
