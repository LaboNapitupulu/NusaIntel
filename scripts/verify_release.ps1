[CmdletBinding()]
param(
    [switch]$SkipSecurityAudit,
    [switch]$FullStack
)

$ErrorActionPreference = "Stop"

function Assert-ExitCode {
    param([string]$Step, [int]$ExitCode)
    if ($ExitCode -ne 0) {
        throw "$Step failed with exit code $ExitCode."
    }
}

$releaseRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $releaseRoot "backend"
$frontendRoot = Join-Path $releaseRoot "frontend"
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Backend virtual environment not found. Follow README local setup first."
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
$nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
if (-not $npmCommand -or -not $nodeCommand) {
    throw "Node.js and npm.cmd must be available on PATH."
}

Push-Location $backendRoot
try {
    & $pythonPath -m ruff check app tests migrations
    Assert-ExitCode "Ruff lint" $LASTEXITCODE
    & $pythonPath -m ruff format --check app tests migrations
    Assert-ExitCode "Ruff format" $LASTEXITCODE
    & $pythonPath -m mypy app
    Assert-ExitCode "Mypy" $LASTEXITCODE
    & $pythonPath -m pytest `
        --cov=app.opportunity.engine `
        --cov=app.regional_analytics.engine `
        --cov=app.control_tower.engine `
        --cov=app.pipeline.normalize `
        --cov=app.pipeline.quality `
        --cov-report=term-missing `
        --cov-fail-under=85
    Assert-ExitCode "Backend tests and coverage" $LASTEXITCODE
    if (-not $SkipSecurityAudit) {
        & $pythonPath -m pip_audit
        Assert-ExitCode "Python dependency audit" $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Push-Location $frontendRoot
$webProcess = $null
try {
    & $npmCommand.Source run lint
    Assert-ExitCode "Frontend lint" $LASTEXITCODE
    & $npmCommand.Source run typecheck
    Assert-ExitCode "Frontend typecheck" $LASTEXITCODE
    & $npmCommand.Source test
    Assert-ExitCode "Frontend component tests" $LASTEXITCODE
    & $npmCommand.Source run build
    Assert-ExitCode "Frontend production build" $LASTEXITCODE
    if (-not $SkipSecurityAudit) {
        & $npmCommand.Source audit --audit-level=high
        Assert-ExitCode "Frontend dependency audit" $LASTEXITCODE
    }

    $nextPath = Join-Path $frontendRoot "node_modules\next\dist\bin\next"
    $webProcess = Start-Process `
        -FilePath $nodeCommand.Source `
        -ArgumentList @($nextPath, "start", "--hostname", "127.0.0.1", "--port", "3101") `
        -WorkingDirectory $frontendRoot `
        -WindowStyle Hidden `
        -PassThru
    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt += 1) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:3101" -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                $ready = $true
                break
            }
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    if (-not $ready) {
        throw "Production web server did not become ready within 30 seconds."
    }
    $env:E2E_EXTERNAL_SERVER = "1"
    & $npmCommand.Source run test:e2e
    Assert-ExitCode "Frontend E2E and accessibility" $LASTEXITCODE
} finally {
    Remove-Item Env:E2E_EXTERNAL_SERVER -ErrorAction SilentlyContinue
    if ($webProcess -and -not $webProcess.HasExited) {
        Stop-Process -Id $webProcess.Id -Force
    }
    Pop-Location
}

Push-Location $releaseRoot
try {
    docker compose config --quiet
    Assert-ExitCode "Compose configuration" $LASTEXITCODE
    if ($FullStack) {
        docker compose up --build --detach --wait --wait-timeout 180
        Assert-ExitCode "Compose stack startup" $LASTEXITCODE
        docker compose ps
        Assert-ExitCode "Compose status" $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Output "NusaIntel release verification passed."
