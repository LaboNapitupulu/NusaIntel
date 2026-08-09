[CmdletBinding()]
param(
    [switch]$Fixture
)

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repositoryRoot
try {
    if ($Fixture) {
        $pythonPath = Join-Path $repositoryRoot "backend\.venv\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $pythonPath)) {
            throw "Backend virtual environment not found. Create backend/.venv first."
        }
        Push-Location (Join-Path $repositoryRoot "backend")
        try {
            & $pythonPath -m app.pipeline.cli `
                --indicator tpt `
                --fixture "..\tests\fixtures\bps\tpt_august_543_2023_2025_live.json"
        }
        finally {
            Pop-Location
        }
    }
    else {
        docker compose run --rm worker python -m app.pipeline.cli --indicator tpt --live
    }

    if ($LASTEXITCODE -ne 0) {
        throw "TPT pipeline failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
