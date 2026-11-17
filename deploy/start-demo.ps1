param([switch]$SkipBuild)
$ErrorActionPreference='Stop'
. (Join-Path $PSScriptRoot '../ruoyi/scripts/common.ps1')
$runtime=Get-LocalRuntime
$projectRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$agentRoot=Join-Path $projectRoot 'agent'
$python=Join-Path $agentRoot '.venv/Scripts/python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'Prepare agent/.venv with requirements.lock.txt first. See deploy/README.md.'}
$demoRoot=Join-Path $agentRoot '.runtime/demo'
New-Item -ItemType Directory -Path $demoRoot -Force | Out-Null
$settings=Join-Path $demoRoot 'credentials.json'
if(-not(Test-Path -LiteralPath $settings)){
  $randomBytes=New-Object byte[] 24
  $random=[Security.Cryptography.RandomNumberGenerator]::Create()
  try{$random.GetBytes($randomBytes)}finally{$random.Dispose()}
  @{username='demo';password=[Convert]::ToBase64String($randomBytes)}|ConvertTo-Json|Set-Content -LiteralPath $settings -Encoding UTF8
}
if(-not $SkipBuild){
  Push-Location (Join-Path $projectRoot 'frontend')
  try{& npm run build;if($LASTEXITCODE -ne 0){throw 'Dashboard build failed'}}finally{Pop-Location}
}
Push-Location $agentRoot
try{
  if(-not(Test-Path -LiteralPath '.cache/models/bge-small-zh-v1.5/model_optimized.onnx')){& $python -X utf8 rag_cli.py prepare;if($LASTEXITCODE -ne 0){throw 'Local embedding model preparation failed'}}
  & $python -X utf8 rag_cli.py build
  if($LASTEXITCODE -ne 0){throw 'Local knowledge index build failed'}
}finally{Pop-Location}
$env:SKYTWIN_DEMO_SETTINGS=$settings
$env:SKYTWIN_ARTIFACT_DB=Join-Path $demoRoot 'artifacts.sqlite'
try{
  Start-ManagedProcess -Name 'demo-agent' -Executable $python -Arguments @('-X','utf8','-m','uvicorn','demo_service:app_factory','--factory','--host','127.0.0.1','--port','8003','--no-access-log','--workers','1') -WorkingDirectory $agentRoot -Port 8003
}finally{Remove-Item Env:SKYTWIN_DEMO_SETTINGS,Env:SKYTWIN_ARTIFACT_DB -ErrorAction SilentlyContinue}
Wait-LocalPort 8003 30
Start-ManagedProcess -Name 'demo-web' -Executable $runtime.NodeExecutable -Arguments @("`"$(Join-Path $PSScriptRoot 'demo-server.mjs')`"") -WorkingDirectory $projectRoot -Port 5180
Wait-LocalPort 5180 20
$health=Invoke-RestMethod 'http://127.0.0.1:8003/health'
if(-not $health.demo_only){throw 'Independent sample identity check failed'}
Write-Host 'Independent sample ready: http://127.0.0.1:5180/ai-workbench'
Write-Host "Read the local demo username/password in $settings (not printed)."
Write-Host 'No Java/MySQL/Redis instance is started or modified; no external LLM requests are allowed.'
