. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
$secrets = Get-LocalSecrets
if (-not (Test-LocalPort 3307)) { throw 'Start the dedicated MySQL instance: scripts/start.ps1 -Service data' }
$mysqlRecord = @(Get-ManagedRecords) | Where-Object { $_.Name -eq 'mysql' } | Select-Object -First 1
if (-not (Get-ManagedProcess $mysqlRecord)) {
    throw 'Port 3307 is not the MySQL instance managed by this deployment.'
}
$rootConfig = Join-Path $RuoyiRoot 'config/mysql-root.cnf'
$mysql = Join-Path $runtime.MySqlBin 'mysql.exe'
$initialized = Join-Path $RuoyiRoot 'data/.schema-ready'
if (Test-Path $initialized) {
    Write-Host 'Schema already initialized. Existing data was preserved.'
    exit 0
}

# Set only this new instance's root password. Never inspect or change port 3306.
$authCheck = Start-Process -FilePath $mysql `
    -ArgumentList @("--defaults-file=`"$rootConfig`"", '--execute="SELECT 1;"') `
    -WindowStyle Hidden -Wait -PassThru `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/mysql-auth.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/mysql-auth.stderr.log')
if ($authCheck.ExitCode -ne 0) {
    $bootstrapFile = Join-Path $RuoyiRoot 'config/mysql-bootstrap.sql'
    "ALTER USER 'root'@'localhost' IDENTIFIED BY '$($secrets.MySqlRootPassword)';" |
        Set-Content -LiteralPath $bootstrapFile -Encoding ASCII
    try {
        $process = Start-Process -FilePath $mysql -ArgumentList @('--no-defaults', '--protocol=TCP', '--host=127.0.0.1', '--port=3307', '--user=root') `
            -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $bootstrapFile `
            -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/mysql-bootstrap.stdout.log') `
            -RedirectStandardError (Join-Path $RuoyiRoot 'logs/mysql-bootstrap.stderr.log')
        if ($process.ExitCode -ne 0) { throw 'Cannot initialize MySQL root account. See logs/mysql-bootstrap.stderr.log.' }
    } finally {
        Remove-Item -LiteralPath $bootstrapFile -Force
    }
}
$existing = & $mysql "--defaults-file=$rootConfig" --batch --skip-column-names `
    "--execute=SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sky_twin_ruoyi';"
if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect the dedicated schema.' }
if ([int]$existing -gt 0) {
    throw 'The database already has tables but no initialization marker. Refusing to overwrite data.'
}
$seed = Get-ChildItem (Join-Path $RuoyiRoot 'backend/sql') -Filter 'ry_*.sql' | Sort-Object Name -Descending | Select-Object -First 1
$quartz = Join-Path $RuoyiRoot 'backend/sql/quartz.sql'
$importFile = Join-Path $RuoyiRoot 'config/mysql-import.sql'
@"
CREATE DATABASE IF NOT EXISTS sky_twin_ruoyi CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'sky_twin_ruoyi'@'127.0.0.1' IDENTIFIED BY '$($secrets.DbPassword)';
GRANT ALL PRIVILEGES ON sky_twin_ruoyi.* TO 'sky_twin_ruoyi'@'127.0.0.1';
USE sky_twin_ruoyi;
SOURCE $($seed.FullName.Replace('\', '/'));
SOURCE $($quartz.Replace('\', '/'));
UPDATE sys_dept SET dept_name='SkyTwin Operations' WHERE dept_id=100;
UPDATE sys_user SET nick_name='SkyTwin Admin' WHERE user_id=1;
"@ | Set-Content -LiteralPath $importFile -Encoding UTF8
try {
    $process = Start-Process -FilePath $mysql -ArgumentList @("--defaults-file=`"$rootConfig`"", '--default-character-set=utf8mb4') `
        -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $importFile `
        -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/mysql-import.stdout.log') `
        -RedirectStandardError (Join-Path $RuoyiRoot 'logs/mysql-import.stderr.log')
    if ($process.ExitCode -ne 0) { throw 'Schema import failed. See logs/mysql-import.stderr.log.' }
    $count = & $mysql "--defaults-file=$rootConfig" --batch --skip-column-names `
        "--execute=SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='sky_twin_ruoyi';"
    if ($LASTEXITCODE -ne 0 -or [int]$count -lt 30) { throw 'Schema import verification failed.' }
    (Get-Date).ToString('o') | Set-Content $initialized
    Write-Host "Initialized dedicated database sky_twin_ruoyi ($count tables)."
} finally {
    Remove-Item -LiteralPath $importFile -Force
}
