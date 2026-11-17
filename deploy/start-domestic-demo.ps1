$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
. (Join-Path $root 'ruoyi/scripts/common.ps1')
if(-not(Test-Path -LiteralPath (Join-Path $root '.runtime/cpolar-skytwin.yml'))){throw 'Run deploy/configure-domestic-demo.ps1 in your local PowerShell first; no token is needed in chat.'}
if(-not(Test-Path -LiteralPath (Join-Path $root 'frontend/dist/index.html'))){throw 'Build frontend with npm --prefix frontend run build first.'}
foreach($entry in @(@{port=3307;service='data'},@{port=16380;service='data'},@{port=8081;service='backend'},@{port=8002;service='agent'})){
  if(-not(Test-LocalPort $entry.port)){& (Join-Path $root 'ruoyi/scripts/start.ps1') -Service $entry.service}
}
$statePath=Join-Path $root '.runtime/domestic-demo-process.json'
if(Test-Path -LiteralPath $statePath){
  $record=Get-Content -LiteralPath $statePath -Raw|ConvertFrom-Json
  $running=Get-Process -Id $record.pid -ErrorAction SilentlyContinue
  if($running -and $running.Path -eq $record.executable -and $running.StartTime.ToUniversalTime().ToString('o') -eq $record.startedUtc){Write-Host 'Domestic demo already running.';exit 0}
}
if(Test-LocalPort 5182){throw 'Domestic demo port 5182 is already used; nothing was stopped.'}
$process=Start-Process -FilePath (Get-Command node).Source -ArgumentList @((Join-Path $PSScriptRoot 'run-domestic-demo.mjs')) -WorkingDirectory $root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $root '.runtime/domestic-demo.stdout.log') -RedirectStandardError (Join-Path $root '.runtime/domestic-demo.stderr.log')
@{pid=$process.Id;startedUtc=$process.StartTime.ToUniversalTime().ToString('o');executable=$process.Path}|ConvertTo-Json|Set-Content -LiteralPath $statePath -Encoding UTF8
Write-Host 'Domestic demo starting. Read .runtime/domestic-demo.stdout.log for the new HTTPS URL.'
Write-Host 'No Sites, localhost.run, or proxy connection is used by this connector.'
