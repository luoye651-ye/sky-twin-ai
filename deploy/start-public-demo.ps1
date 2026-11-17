$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. (Join-Path $root 'ruoyi/scripts/common.ps1')
foreach($entry in @(@{port=3307;service='data'},@{port=16380;service='data'},@{port=8081;service='backend'},@{port=8002;service='agent'})){
  if(-not(Test-LocalPort $entry.port)){
    & (Join-Path $root 'ruoyi/scripts/start.ps1') -Service $entry.service
  }
}
& (Join-Path $PSScriptRoot 'start-public-gateway.ps1')
$statePath=Join-Path $root '.runtime/public-tunnel-process.json'
if(Test-Path -LiteralPath $statePath){
  $record=Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
  $running=Get-Process -Id $record.pid -ErrorAction SilentlyContinue
  if($running -and $running.StartTime.ToUniversalTime().ToString('o') -eq $record.startedUtc){Write-Host 'Public tunnel connector already running.';exit 0}
}
$process=Start-Process -FilePath (Get-Command node).Source -ArgumentList @((Join-Path $PSScriptRoot 'run-public-tunnel.mjs')) -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root '.runtime/public-tunnel.stdout.log') -RedirectStandardError (Join-Path $root '.runtime/public-tunnel.stderr.log')
@{pid=$process.Id;startedUtc=$process.StartTime.ToUniversalTime().ToString('o');executable=$process.Path}|ConvertTo-Json|Set-Content -LiteralPath $statePath -Encoding UTF8
Write-Host 'Public demo connector started. Wait for Registered in .runtime/public-tunnel.stdout.log.'
Write-Host 'Site: https://skytwin-ai-demo.spicyangel15.chatgpt.site'
