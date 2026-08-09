[CmdletBinding()]
param(
    [switch]$SkipDocker
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$pythonPath = Join-Path $backendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "Backend virtual environment not found. Follow README local setup first."
}

$npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCommand) {
    throw "npm.cmd was not found on PATH."
}

Push-Location $backendRoot
try {
    & $pythonPath -m ruff check app tests migrations
    & $pythonPath -m ruff format --check app tests migrations
    & $pythonPath -m mypy app
    & $pythonPath -m pytest
} finally {
    Pop-Location
}

Push-Location $frontendRoot
try {
    & $npmCommand.Source run lint
    & $npmCommand.Source run typecheck
    & $npmCommand.Source test
    & $npmCommand.Source run build
} finally {
    Pop-Location
}

Push-Location $projectRoot
try {
    docker compose config --quiet
    if (-not $SkipDocker) {
        docker compose up --build --detach
        docker compose ps
    }
} finally {
    Pop-Location
}

Write-Output "Phase 1 verification passed."
