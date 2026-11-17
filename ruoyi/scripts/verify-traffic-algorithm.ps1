. (Join-Path $PSScriptRoot 'common.ps1')
$trafficRuntime = Get-LocalRuntime
$trafficOutput = Join-Path $RuoyiRoot '.runtime/traffic-checks'
New-Item -ItemType Directory -Path $trafficOutput -Force | Out-Null
$trafficSource = Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin'
& (Join-Path $trafficRuntime.JavaHome 'bin/javac.exe') -encoding UTF-8 -d $trafficOutput `
    (Join-Path $trafficSource 'AirspaceEngine.java') (Join-Path $trafficSource 'TrafficEngine.java') `
    (Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/test/java/com/ruoyi/skytwin/TrafficEngineChecks.java')
if ($LASTEXITCODE -ne 0) { throw 'Traffic checks compilation failed.' }
& (Join-Path $trafficRuntime.JavaHome 'bin/java.exe') -cp $trafficOutput com.ruoyi.skytwin.TrafficEngineChecks
if ($LASTEXITCODE -ne 0) { throw 'Traffic checks failed.' }
