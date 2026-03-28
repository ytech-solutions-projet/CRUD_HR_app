param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$DjangoArgs
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repoRoot ".tmp\\local-postgres.env"

if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
            return
        }

        $name, $value = $line.Split("=", 2)
        Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
    }
} elseif (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql://hr_app_user:LocalPostgres12345!@127.0.0.1:5432/ytech_hr"
}

python (Join-Path $repoRoot "backend\\manage.py") @DjangoArgs
exit $LASTEXITCODE
