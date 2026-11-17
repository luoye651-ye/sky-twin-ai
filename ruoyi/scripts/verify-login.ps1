param([string]$Username = 'admin', [string]$Password = 'admin123',
      [string]$BaseUrl = 'http://127.0.0.1:5174/dev-api')
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
$baseUrl = $BaseUrl.TrimEnd('/')
$unauthorized = Invoke-RestMethod "$baseUrl/system/user/list" -TimeoutSec 10
if ($unauthorized.code -ne 401) { throw 'Protected API did not reject the unauthenticated request.' }
$captcha = Invoke-RestMethod "$baseUrl/captchaImage" -TimeoutSec 10
$code = ''
if ($captcha.captchaEnabled) {
    # Local deployment smoke check: read only this test's captcha, keep captcha enabled.
    $env:REDISCLI_AUTH = (Get-LocalSecrets).RedisPassword
    try {
        $code = & (Join-Path $runtime.RedisBin 'redis-cli.exe') -h 127.0.0.1 -p (Get-LocalRedisPort $runtime) --raw get "captcha_codes:$($captcha.uuid)"
        if ($LASTEXITCODE -ne 0 -or -not $code) { throw 'The local test captcha could not be read.' }
        $code = "$code".Trim().Trim('"')
    } finally { Remove-Item Env:REDISCLI_AUTH -ErrorAction SilentlyContinue }
}
$body = @{ username=$Username; password=$Password; code=$code; uuid=$captcha.uuid } | ConvertTo-Json
$login = Invoke-RestMethod "$baseUrl/login" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 15
if ($login.code -ne 200 -or -not $login.token) { throw "Login failed (code $($login.code))." }
$headers = @{ Authorization = "Bearer $($login.token)" }
try {
    $info = Invoke-RestMethod "$baseUrl/getInfo" -Headers $headers -TimeoutSec 10
    if ($info.code -ne 200 -or $info.user.userName -ne $Username) { throw 'Authenticated user info failed.' }
    $routes = Invoke-RestMethod "$baseUrl/getRouters" -Headers $headers -TimeoutSec 10
    if ($routes.code -ne 200 -or @($routes.data).Count -lt 1) { throw 'Permission menu loading failed.' }
    $users = Invoke-RestMethod "$baseUrl/system/user/list?pageNum=1&pageSize=10" -Headers $headers -TimeoutSec 10
    if ($users.code -ne 200 -or $users.total -lt 1) { throw 'User management query failed.' }
    $roles = Invoke-RestMethod "$baseUrl/system/role/list?pageNum=1&pageSize=10" -Headers $headers -TimeoutSec 10
    if ($roles.code -ne 200 -or $roles.total -lt 1) { throw 'Role management query failed.' }
    Write-Host "PASS: login, user info, permission menus, user list ($($users.total)), role list ($($roles.total))."
} finally {
    $logout = Invoke-RestMethod "$baseUrl/logout" -Method Post -Headers $headers -TimeoutSec 10
    if ($logout.code -ne 200) { throw 'Logout failed.' }
}
$expired = Invoke-RestMethod "$baseUrl/getInfo" -Headers $headers -TimeoutSec 10
if ($expired.code -ne 401) { throw 'The logout token was still accepted.' }
Write-Host 'PASS: unauthenticated access rejected; token invalidated after logout.'
