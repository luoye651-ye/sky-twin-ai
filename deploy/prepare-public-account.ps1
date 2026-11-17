param([string]$AdminUsername='admin', [string]$AdminPassword='admin123')
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../ruoyi/scripts/common.ps1')
$runtime=Get-LocalRuntime
$baseUrl='http://127.0.0.1:8081'
$settingsPath=Join-Path $PSScriptRoot '../.runtime/public-demo-credentials.json'
$repair=$false
if(Test-Path -LiteralPath $settingsPath){
  $existing=Get-Content -LiteralPath $settingsPath -Raw|ConvertFrom-Json
  if($existing.username -ne 'sky_demo' -or $existing.role -ne 'sky_dispatcher'){throw 'Unexpected credential file identity; nothing changed.'}
  if($existing.password.Length -ge 5 -and $existing.password.Length -le 20){Write-Host 'Existing public demonstration credentials retained.';exit 0}
  $repair=$true
}
$captcha=Invoke-RestMethod "$baseUrl/captchaImage" -TimeoutSec 15
$code=''
if($captcha.captchaEnabled){
  $env:REDISCLI_AUTH=(Get-LocalSecrets).RedisPassword
  try{ $code=(& (Join-Path $runtime.RedisBin 'redis-cli.exe') -h 127.0.0.1 -p (Get-LocalRedisPort) --raw get "captcha_codes:$($captcha.uuid)").Trim().Trim('"') }
  finally{Remove-Item Env:REDISCLI_AUTH -ErrorAction SilentlyContinue}
}
$login=Invoke-RestMethod "$baseUrl/login" -Method Post -ContentType 'application/json' -Body (@{username=$AdminUsername;password=$AdminPassword;code=$code;uuid=$captcha.uuid}|ConvertTo-Json) -TimeoutSec 15
if($login.code -ne 200 -or -not $login.token){throw 'Local administrator authentication failed; no account changed.'}
$headers=@{Authorization="Bearer $($login.token)"}
try{
  $users=Invoke-RestMethod "$baseUrl/system/user/list?userName=sky_demo" -Headers $headers
  $matches=@($users.rows | Where-Object { $_.userName -eq 'sky_demo' })
  if($matches.Count -and -not $repair){throw 'sky_demo already exists without this deployment credential file; nothing overwritten.'}
  if($repair -and $matches.Count -ne 1){throw 'Owned demonstration account was not found; nothing changed.'}
  $roles=Invoke-RestMethod "$baseUrl/system/role/list?roleKey=sky_dispatcher" -Headers $headers
  $role=@($roles.rows | Where-Object { $_.roleKey -eq 'sky_dispatcher' -and $_.status -eq '0' })
  if($role.Count -ne 1){throw 'Expected active sky_dispatcher role was not found; no account created.'}
  # RuoYi login precheck accepts 5..20 characters. 12 random bytes produce
  # 16 Base64 characters (96 bits), avoiding the previous 32-character error.
  $bytes=New-Object byte[] 12
  $rng=[Security.Cryptography.RandomNumberGenerator]::Create()
  try{$rng.GetBytes($bytes)}finally{$rng.Dispose()}
  $password=[Convert]::ToBase64String($bytes)
  if($password.Length -lt 5 -or $password.Length -gt 20){throw 'Generated password violates the server login policy.'}
  if($repair){
    $detail=Invoke-RestMethod "$baseUrl/system/user/$($matches[0].userId)" -Headers $headers
    if(@($detail.roleIds).Count -ne 1 -or [long]$detail.roleIds[0] -ne [long]$role[0].roleId){throw 'Demo account role changed; nothing overwritten.'}
    $body=@{userId=$matches[0].userId;password=$password}|ConvertTo-Json
    $created=Invoke-RestMethod "$baseUrl/system/user/resetPwd" -Method Put -ContentType 'application/json' -Headers $headers -Body $body
  }else{
    $body=@{userName='sky_demo';nickName='SkyTwin Public Demo';password=$password;sex='2';status='0';roleIds=@([long]$role[0].roleId);postIds=@();remark='Dedicated competition demonstration account; no system administrator role.'}|ConvertTo-Json
    $created=Invoke-RestMethod "$baseUrl/system/user" -Method Post -ContentType 'application/json' -Headers $headers -Body $body
  }
  if($created.code -ne 200){throw 'Demo account creation was rejected; credentials not written.'}
  @{username='sky_demo';password=$password;role='sky_dispatcher';createdUtc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath $settingsPath -Encoding UTF8
  Write-Host 'Prepared sky_demo account with sky_dispatcher role and server-compatible password. Password stored locally, not printed.'
}finally{Invoke-RestMethod "$baseUrl/logout" -Method Post -Headers $headers | Out-Null}
