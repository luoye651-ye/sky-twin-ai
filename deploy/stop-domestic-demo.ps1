$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$path=Join-Path $root '.runtime/domestic-demo-process.json'
if(-not(Test-Path -LiteralPath $path)){Write-Host 'No owned domestic demo process.';exit 0}
$record=Get-Content -LiteralPath $path -Raw|ConvertFrom-Json
$running=Get-Process -Id $record.pid -ErrorAction SilentlyContinue
if($running -and $running.Path -eq $record.executable -and $running.StartTime.ToUniversalTime().ToString('o') -eq $record.startedUtc){
  & taskkill.exe /PID $running.Id /T /F | Out-Null
  if($LASTEXITCODE -ne 0){throw 'Could not stop owned domestic demo process'}
  Write-Host 'Stopped owned domestic website and cpolar child process.'
}
Write-Host 'Existing Java/Agent/MySQL/Redis and other tunnel services retained.'
