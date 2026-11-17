$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../ruoyi/scripts/common.ps1')
$records=@(Get-ManagedRecords)
foreach($name in @('demo-web','demo-agent')){
  $record=$records|Where-Object{$_.Name -eq $name}|Select-Object -First 1
  $owned=Get-ManagedProcess $record
  if(-not $owned){Write-Host "$name is not running under this deployment.";continue}
  if($name -eq 'demo-agent'){& "$env:SystemRoot\System32\taskkill.exe" /PID $owned.Id /T /F;if($LASTEXITCODE -ne 0){throw 'Owned demo Agent did not stop'}}else{Stop-Process -Id $owned.Id}
  if(-not $owned.WaitForExit(10000)){throw 'Owned demo process did not exit'}
}
$remaining=@($records|Where-Object{Get-ManagedProcess $_})
ConvertTo-Json -InputObject $remaining|Set-Content -LiteralPath $ProcessFile -Encoding UTF8
Write-Host 'Stopped only the owned independent sample processes; sample data retained.'
