param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$DjangoArgs
)

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$envFile = Join-Path $repoRoot ".tmp\\local-mariadb.env"

if (-not (Test-Path $envFile)) {
    throw "Missing local MariaDB env file at $envFile"
}

Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
        return
    }

    $name, $value = $line.Split("=", 2)
    Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
}

$env:PYTHONPATH = Join-Path $repoRoot ".deps"
$python = Join-Path $repoRoot ".venv\\Scripts\\python.exe"
$manage = Join-Path $repoRoot "backend\\manage.py"

& $python $manage @DjangoArgs
exit $LASTEXITCODE
