. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
$output = Join-Path $RuoyiRoot '.runtime/airspace-checks'
New-Item -ItemType Directory -Path $output -Force | Out-Null
$source = Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/AirspaceEngine.java'
$checks = Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/test/java/com/ruoyi/skytwin/AirspaceEngineChecks.java'
& (Join-Path $runtime.JavaHome 'bin/javac.exe') -encoding UTF-8 -d $output $source $checks
if ($LASTEXITCODE -ne 0) { throw 'Airspace checks compilation failed.' }
& (Join-Path $runtime.JavaHome 'bin/java.exe') -cp $output com.ruoyi.skytwin.AirspaceEngineChecks
if ($LASTEXITCODE -ne 0) { throw 'Airspace algorithm verification failed.' }
