$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
foreach($name in @('public-tunnel','public-gateway')){
  $state=Join-Path $root ".runtime/$name-process.json"
  if(-not(Test-Path -LiteralPath $state)){continue}
  $record=Get-Content -LiteralPath $state -Raw|ConvertFrom-Json
  $running=Get-Process -Id $record.pid -ErrorAction SilentlyContinue
  if($running -and $running.Path -eq $record.executable -and $running.StartTime.ToUniversalTime().ToString('o') -eq $record.startedUtc){
    & taskkill.exe /PID $running.Id /T /F | Out-Null
    if($LASTEXITCODE -ne 0){throw "Could not stop owned $name process"}
    Write-Host "Stopped owned $name process."
  }
}
Write-Host 'Existing Java, Agent, MySQL and Redis services retained.'
