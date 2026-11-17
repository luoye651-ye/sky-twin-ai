$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$statePath=Join-Path $root '.runtime/public-gateway-process.json'
if(Test-Path -LiteralPath $statePath){
  $record=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
  $running=Get-Process -Id $record.pid -ErrorAction SilentlyContinue
  if($running -and $running.StartTime.ToUniversalTime().ToString('o') -eq $record.startedUtc){Write-Host 'Public API gateway already running.';exit 0}
}
$env:SKYTWIN_PUBLIC_ORIGINS='https://skytwin-ai-demo.spicyangel15.chatgpt.site'
$env:SKYTWIN_TUNNEL_SECRET=(Get-Content (Join-Path $root '.runtime/public-tunnel-settings.json') -Raw | ConvertFrom-Json).secret
try{
  $process=Start-Process -FilePath (Get-Command node).Source -ArgumentList @((Join-Path $PSScriptRoot 'public-gateway.mjs')) -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root '.runtime/public-gateway.stdout.log') -RedirectStandardError (Join-Path $root '.runtime/public-gateway.stderr.log')
  @{pid=$process.Id;startedUtc=$process.StartTime.ToUniversalTime().ToString('o');executable=$process.Path}|ConvertTo-Json|Set-Content -LiteralPath $statePath -Encoding UTF8
}finally{Remove-Item Env:SKYTWIN_PUBLIC_ORIGINS,Env:SKYTWIN_TUNNEL_SECRET -ErrorAction SilentlyContinue}
Write-Host 'Started API-only gateway on 127.0.0.1:5181.'
