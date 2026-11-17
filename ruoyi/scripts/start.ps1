param([ValidateSet('all', 'data', 'backend', 'frontend', 'dashboard', 'agent')][string]$Service = 'all')
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
$redisPort = Get-LocalRedisPort $runtime

if ($Service -in @('all', 'data')) {
    if (-not (Test-Path (Join-Path $RuoyiRoot 'data/mysql/mysql'))) {
        throw 'MySQL is not initialized. Follow README.md before starting.'
    }
    $mysqlConfig = Join-Path $RuoyiRoot 'config/mysql.ini'
    Start-ManagedProcess -Name mysql -Executable (Join-Path $runtime.MySqlBin 'mysqld.exe') `
        -Arguments @("--defaults-file=`"$mysqlConfig`"", '--console') `
        -WorkingDirectory $RuoyiRoot -Port 3307
    Start-ManagedProcess -Name redis -Executable (Join-Path $runtime.RedisBin 'redis-server.exe') `
        -Arguments @('config/redis.conf', '--port', "$redisPort") -WorkingDirectory $RuoyiRoot -Port $redisPort
    Wait-LocalPort 3307
    Wait-LocalPort $redisPort
}

if ($Service -in @('all', 'backend')) {
    if (-not (Test-Path (Join-Path $RuoyiRoot 'data/.schema-ready'))) {
        throw 'Run scripts/initialize-db.ps1 before starting the Java backend.'
    }
    $jar = Join-Path $RuoyiRoot 'backend/ruoyi-admin/target/ruoyi-admin.jar'
    if (-not (Test-Path $jar)) { throw 'Run scripts/build.ps1 -Target backend first.' }
    Set-BackendEnvironment
    try {
        $configPath = (Join-Path $RuoyiRoot 'config').Replace('\', '/') + '/'
        $temporaryPath = (Join-Path $RuoyiRoot '.runtime/tmp').Replace('\', '/')
        New-Item -ItemType Directory -Path $temporaryPath -Force | Out-Null
        Start-ManagedProcess -Name backend -Executable (Join-Path $runtime.JavaHome 'bin/java.exe') `
            -Arguments @('-Xms128m', '-Xmx768m', '-Dfile.encoding=UTF-8', "-Djdk.net.unixdomain.tmpdir=$temporaryPath", "-Djava.io.tmpdir=$temporaryPath", '-jar', "`"$jar`"", `
                '--spring.profiles.active=druid,sky-twin', "--spring.config.additional-location=optional:file:$configPath") `
            -WorkingDirectory $RuoyiRoot -Port 8081
    } finally {
        Remove-Item Env:SKYTWIN_DB_PASSWORD,Env:SKYTWIN_REDIS_PASSWORD,Env:SKYTWIN_REDIS_PORT,Env:SKYTWIN_TOKEN_SECRET -ErrorAction SilentlyContinue
    }
    Wait-LocalPort 8081 90
}

if ($Service -in @('all', 'frontend')) {
    $vite = Join-Path $RuoyiRoot 'frontend/node_modules/vite/bin/vite.js'
    if (-not (Test-Path $vite)) { throw 'Install frontend dependencies first. See README.md.' }
    Start-ManagedProcess -Name frontend -Executable $runtime.NodeExecutable `
        -Arguments @("`"$vite`"", '--host', '127.0.0.1', '--port', '5174', '--strictPort') `
        -WorkingDirectory (Join-Path $RuoyiRoot 'frontend') -Port 5174
    Wait-LocalPort 5174
}
if ($Service -in @('all','dashboard')) {
    & (Join-Path $PSScriptRoot 'start-dashboard.ps1')
}
if ($Service -in @('all','agent')) {
    $agentRoot = [IO.Path]::GetFullPath((Join-Path $RuoyiRoot '../agent'))
    $agentPython = Join-Path $agentRoot '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $agentPython)) {
        if ($Service -eq 'agent') { throw 'Prepare agent/.venv and requirements first. See agent/README.md.' }
        Write-Warning 'Agent environment is not installed; skipped. See agent/README.md.'
    } else {
        Start-ManagedProcess -Name agent -Executable $agentPython `
            -Arguments @('-X', 'utf8', '-m', 'uvicorn', 'chat_service:app', '--host', '127.0.0.1', '--port', '8002', '--no-access-log', '--workers', '1') `
            -WorkingDirectory $agentRoot -Port 8002
        Wait-LocalPort 8002 30
    }
}
Write-Host 'RuoYi admin: http://127.0.0.1:5174 | Java API: http://127.0.0.1:8081'
