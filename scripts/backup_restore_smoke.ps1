[CmdletBinding()]
param(
    [string]$BackupPath = "artifacts/nusa-intel-backup.dump",
    [switch]$RestoreSmoke
)

$ErrorActionPreference = "Stop"

function Assert-ExitCode {
    param([string]$Step, [int]$ExitCode)
    if ($ExitCode -ne 0) {
        throw "$Step failed with exit code $ExitCode."
    }
}

$backupRoot = Split-Path -Parent $PSScriptRoot
$resolvedBackup = Join-Path $backupRoot $BackupPath
$backupDirectory = Split-Path -Parent $resolvedBackup
$containerBackup = "/tmp/nusa-intel-backup.dump"
$restoreDatabase = "nusa_intel_restore_smoke"

if (-not (Test-Path -LiteralPath $backupDirectory)) {
    New-Item -ItemType Directory -Path $backupDirectory | Out-Null
}

Push-Location $backupRoot
try {
    docker compose exec -T db pg_dump `
        --username=nusa_intel `
        --dbname=nusa_intel `
        --format=custom `
        --file=$containerBackup
    Assert-ExitCode "Database backup" $LASTEXITCODE
    docker compose cp "db:$containerBackup" $resolvedBackup
    Assert-ExitCode "Backup copy" $LASTEXITCODE

    if ($RestoreSmoke) {
        docker compose exec -T db dropdb `
            --username=nusa_intel `
            --if-exists `
            $restoreDatabase
        Assert-ExitCode "Restore scratch cleanup" $LASTEXITCODE
        docker compose exec -T db createdb `
            --username=nusa_intel `
            $restoreDatabase
        Assert-ExitCode "Restore scratch creation" $LASTEXITCODE
        try {
            docker compose exec -T db pg_restore `
                --username=nusa_intel `
                --dbname=$restoreDatabase `
                --exit-on-error `
                $containerBackup
            Assert-ExitCode "Database restore" $LASTEXITCODE
            $domainTableCount = docker compose exec -T db psql `
                --username=nusa_intel `
                --dbname=$restoreDatabase `
                --tuples-only `
                --no-align `
                --command="SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('ops', 'bronze', 'silver', 'gold', 'regulations') AND table_type = 'BASE TABLE';"
            Assert-ExitCode "Restored domain table verification" $LASTEXITCODE
            if ([int]$domainTableCount -lt 22) {
                throw "Restore smoke produced only $domainTableCount of 22 expected domain tables."
            }

            $revision = docker compose exec -T db psql `
                --username=nusa_intel `
                --dbname=$restoreDatabase `
                --tuples-only `
                --no-align `
                --command="SELECT version_num FROM public.alembic_version;"
            Assert-ExitCode "Restored migration revision verification" $LASTEXITCODE
            if ($revision.Trim() -ne "20260816_0004") {
                throw "Restore smoke found unexpected Alembic revision '$($revision.Trim())'."
            }
            $latestViewCount = docker compose exec -T db psql `
                --username=nusa_intel `
                --dbname=$restoreDatabase `
                --tuples-only `
                --no-align `
                --command="SELECT count(*) FROM information_schema.views WHERE table_schema = 'gold' AND table_name = 'latest_regional_observations';"
            Assert-ExitCode "Restored analytics view verification" $LASTEXITCODE
            if ([int]$latestViewCount -ne 1) {
                throw "Restore smoke did not recreate gold.latest_regional_observations."
            }
            Write-Output "Restore smoke verified $domainTableCount domain tables, the latest-observation view, and revision $($revision.Trim())."
        } finally {
            docker compose exec -T db dropdb `
                --username=nusa_intel `
                --if-exists `
                $restoreDatabase
            Assert-ExitCode "Restore scratch removal" $LASTEXITCODE
        }
    }
} finally {
    Pop-Location
}

Write-Output "Backup written to $resolvedBackup"
