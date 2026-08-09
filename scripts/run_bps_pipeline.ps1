[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot

Push-Location $repositoryRoot
try {
    docker compose run --rm worker python -m app.pipeline.cli --all --live
    if ($LASTEXITCODE -ne 0) {
        throw "BPS pipeline failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
