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
$projectName = "nusa-intel-phase6-clean-smoke"
$expectedProjectName = "nusa-intel-phase6-clean-smoke"

if ($projectName -ne $expectedProjectName) {
    throw "Refusing to clean an unexpected Docker Compose project."
}

$env:DB_PORT = "55432"
$env:API_PORT = "18000"
$env:WEB_PORT = "13100"

Push-Location $repositoryRoot
try {
    docker compose --project-name $projectName up `
        --build `
        --detach `
        --wait `
        --wait-timeout 180
    Assert-ExitCode "Clean stack startup" $LASTEXITCODE

    $domainTableCount = docker compose --project-name $projectName exec -T db psql `
        --username=nusa_intel `
        --dbname=nusa_intel `
        --tuples-only `
        --no-align `
        --command="SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('ops', 'bronze', 'silver', 'gold') AND table_type = 'BASE TABLE';"
    Assert-ExitCode "Clean migration table verification" $LASTEXITCODE
    if ([int]$domainTableCount -lt 17) {
        throw "Clean migration produced only $domainTableCount of 17 expected domain tables."
    }

    $latestViewCount = docker compose --project-name $projectName exec -T db psql `
        --username=nusa_intel `
        --dbname=nusa_intel `
        --tuples-only `
        --no-align `
        --command="SELECT count(*) FROM information_schema.views WHERE table_schema = 'gold' AND table_name = 'latest_regional_observations';"
    Assert-ExitCode "Clean migration view verification" $LASTEXITCODE
    if ([int]$latestViewCount -ne 1) {
        throw "Clean migration did not create gold.latest_regional_observations."
    }

    $revision = docker compose --project-name $projectName exec -T db psql `
        --username=nusa_intel `
        --dbname=nusa_intel `
        --tuples-only `
        --no-align `
        --command="SELECT version_num FROM public.alembic_version;"
    Assert-ExitCode "Clean migration revision verification" $LASTEXITCODE
    if ($revision.Trim() -ne "20260811_0003") {
        throw "Clean migration found unexpected Alembic revision '$($revision.Trim())'."
    }

    $apiHealth = Invoke-RestMethod -Uri "http://127.0.0.1:18000/api/v1/health" -TimeoutSec 10
    if ($apiHealth.status -ne "healthy") {
        throw "Clean API health check returned '$($apiHealth.status)'."
    }
    $webResponse = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:13100" -TimeoutSec 10
    if ($webResponse.StatusCode -ne 200) {
        throw "Clean web health check returned HTTP $($webResponse.StatusCode)."
    }

    Write-Output "Clean stack verified $domainTableCount domain tables, analytics view, revision $($revision.Trim()), API, and web."
} finally {
    docker compose --project-name $projectName down --volumes --remove-orphans
    Assert-ExitCode "Clean stack cleanup" $LASTEXITCODE
    Pop-Location
}
