$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$directory=Join-Path $root '.runtime'
New-Item -ItemType Directory -Force -Path $directory | Out-Null
$path=Join-Path $directory 'cpolar-skytwin.yml'
if(Test-Path -LiteralPath $path){Write-Host 'Existing project-only cpolar settings retained. You can start the domestic demo.';exit 0}
Write-Host 'Open https://dashboard.cpolar.com/auth and copy your own Authtoken.'
Write-Host 'Paste only into the masked prompt below. Do not send it in chat.'
$protected=Read-Host 'cpolar Authtoken (hidden)' -AsSecureString
$pointer=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($protected)
try{
  $token=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer).Trim()
  if($token.Length -lt 16 -or $token.Length -gt 1024 -or $token -match '[\s\x00-\x1f\x7f]'){throw 'Invalid token format; no configuration was written.'}
  $quoted=ConvertTo-Json -InputObject $token -Compress
  $yaml=@"
authtoken: $quoted
region: cn
http_proxy: false
console_ui: false
web_addr: false
tunnels:
  skytwin:
    proto: http
    addr: 127.0.0.1:5182
    bind_tls: true
    redirect_https: true
    inspect: false
"@
  [IO.File]::WriteAllText($path,$yaml,(New-Object Text.UTF8Encoding($false)))
  Write-Host 'Saved project-only cpolar configuration. Only skytwin HTTP/HTTPS is configured; no SSH/RDP tunnel.'
}finally{
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
  $token=$null;$quoted=$null;$yaml=$null;$protected.Dispose()
}
