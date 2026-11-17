param([ValidateSet('all','data','backend','frontend','dashboard','agent')][string]$Service = 'all')
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
$records = @(Get-ManagedRecords)
foreach ($name in @('agent', 'dashboard', 'frontend', 'backend', 'redis', 'mysql')) {
    if ($Service -ne 'all' -and $Service -ne $name -and -not ($Service -eq 'data' -and $name -in @('redis','mysql'))) { continue }
    $record = $records | Where-Object { $_.Name -eq $name } | Select-Object -First 1
    $process = Get-ManagedProcess $record
    if (-not $process) { Write-Host "$name is not running under this deployment."; continue }
    if ($name -eq 'mysql') {
        & (Join-Path $runtime.MySqlBin 'mysqladmin.exe') "--defaults-file=$(Join-Path $RuoyiRoot 'config/mysql-root.cnf')" shutdown
        if ($LASTEXITCODE -ne 0) { throw 'MySQL shutdown failed; it was not force-killed.' }
    } elseif ($name -eq 'redis') {
        $env:REDISCLI_AUTH = (Get-LocalSecrets).RedisPassword
        try {
            # Use the verified managed process record, even if configuration changed after startup.
            & (Join-Path $runtime.RedisBin 'redis-cli.exe') -h 127.0.0.1 -p $record.Port shutdown save
            if ($LASTEXITCODE -ne 0) { throw 'Redis shutdown failed; it was not force-killed.' }
        } finally { Remove-Item Env:REDISCLI_AUTH -ErrorAction SilentlyContinue }
    } elseif ($name -eq 'agent') {
        # The verified venv launcher may own a Python child and a stdio MCP child.
        # Stop only this owned tree; never search/kill arbitrary Python processes.
        & "$env:SystemRoot\System32\taskkill.exe" /PID $process.Id /T /F
        if ($LASTEXITCODE -ne 0) { throw 'Owned Agent process tree did not stop.' }
    } else {
        Stop-Process -Id $process.Id
    }
    if (-not $process.WaitForExit(10000)) {
        throw "$name did not exit after its shutdown request; it was not force-killed."
    }
    Write-Host "Stopped $name."
}
$remaining = @($records | Where-Object { Get-ManagedProcess $_ })
ConvertTo-Json -InputObject $remaining | Set-Content -LiteralPath $ProcessFile -Encoding UTF8
