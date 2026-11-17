. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
$records = @(Get-ManagedRecords)
foreach ($name in @('mysql', 'redis', 'backend', 'frontend')) {
    if (-not ($records | Where-Object { $_.Name -eq $name })) {
        throw "Managed service $name is missing. Run start.ps1 first."
    }
}
foreach ($record in $records) {
    if (-not (Get-ManagedProcess $record)) { throw "Managed process $($record.Name) is not running." }
    [pscustomobject]@{
        Service = $record.Name
        ProcessId = $record.ProcessId
        OwnedProcessRunning = [bool](Get-ManagedProcess $record)
        Port = $record.Port
        PortReady = Test-LocalPort $record.Port
    }
}
$captcha = Invoke-RestMethod 'http://127.0.0.1:8081/captchaImage' -TimeoutSec 10
if ($captcha.code -ne 200) { throw 'Java captcha endpoint failed.' }
$proxy = Invoke-RestMethod 'http://127.0.0.1:5174/dev-api/captchaImage' -TimeoutSec 10
if ($proxy.code -ne 200) { throw 'Frontend API proxy failed.' }
$page = Invoke-WebRequest 'http://127.0.0.1:5174/login' -UseBasicParsing -TimeoutSec 10
if ($page.StatusCode -ne 200) { throw 'Frontend page failed.' }
$env:REDISCLI_AUTH = (Get-LocalSecrets).RedisPassword
try {
    $pong = & (Join-Path $runtime.RedisBin 'redis-cli.exe') -h 127.0.0.1 -p (Get-LocalRedisPort $runtime) ping
    if ($LASTEXITCODE -ne 0 -or $pong -ne 'PONG') { throw 'Dedicated Redis check failed.' }
} finally { Remove-Item Env:REDISCLI_AUTH -ErrorAction SilentlyContinue }
Write-Host 'PASS: frontend, Java API, API proxy and dedicated Redis.'
