. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
$record = @(Get-ManagedRecords) | Where-Object { $_.Name -eq 'mysql' } | Select-Object -First 1
if (-not (Get-ManagedProcess $record)) { throw 'Start the dedicated MySQL with start.ps1 -Service data first.' }
$migration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v1.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $migration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Migration failed. See logs/sky-migration.stderr.log.' }
$logisticsMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v2_logistics.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $logisticsMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-logistics-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-logistics-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Logistics migration failed. See logs/sky-logistics-migration.stderr.log.' }
$dispatchMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v3_dispatch.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $dispatchMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-dispatch-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-dispatch-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Dispatch migration failed. See logs/sky-dispatch-migration.stderr.log.' }
$airspaceMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v4_airspace.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $airspaceMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-airspace-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-airspace-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Airspace migration failed. See logs/sky-airspace-migration.stderr.log.' }
$positionMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v5_positioning.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $positionMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-positioning-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-positioning-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Positioning migration failed. See logs/sky-positioning-migration.stderr.log.' }
$routeMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v6_routes.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $routeMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-route-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-route-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Route migration failed. See logs/sky-route-migration.stderr.log.' }
$trafficMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v7_traffic.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $trafficMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-traffic-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-traffic-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Traffic migration failed. See logs/sky-traffic-migration.stderr.log.' }
$environmentMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v8_environment.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $environmentMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-environment-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-environment-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Environment migration failed. See logs/sky-environment-migration.stderr.log.' }
Write-Host 'SkyTwin tables including environmental evidence migrated (existing rows preserved).'
$patrolMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v9_patrol_eval.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $patrolMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-patrol-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-patrol-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Patrol evaluation migration failed. See logs/sky-patrol-migration.stderr.log.' }
Write-Host 'Offline patrol evaluation tables migrated (no task/event changes).'

$visionMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v10_vision.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $visionMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-vision-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-vision-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Vision migration failed. See logs/sky-vision-migration.stderr.log.' }

$opsMigration = Join-Path $RuoyiRoot 'backend/sql/sky_twin_v11_operations.sql'
$process = Start-Process -FilePath (Join-Path $runtime.MySqlBin 'mysql.exe') `
    -ArgumentList @("--defaults-file=`"$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')`"", '--default-character-set=utf8mb4', '--database=sky_twin_ruoyi') `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardInput $opsMigration `
    -RedirectStandardOutput (Join-Path $RuoyiRoot 'logs/sky-operations-migration.stdout.log') `
    -RedirectStandardError (Join-Path $RuoyiRoot 'logs/sky-operations-migration.stderr.log')
if ($process.ExitCode -ne 0) { throw 'Operations migration failed.' }
