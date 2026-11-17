. (Join-Path $PSScriptRoot 'common.ps1')
$routeRuntime = Get-LocalRuntime
$routeOutput = Join-Path $RuoyiRoot '.runtime/route-checks'
New-Item -ItemType Directory -Path $routeOutput -Force | Out-Null
$routeSource = Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin'
& (Join-Path $routeRuntime.JavaHome 'bin/javac.exe') -encoding UTF-8 -d $routeOutput `
    (Join-Path $routeSource 'AirspaceEngine.java') (Join-Path $routeSource 'RouteEngine.java') `
    (Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/test/java/com/ruoyi/skytwin/RouteEngineChecks.java')
if ($LASTEXITCODE -ne 0) { throw 'Route checks compilation failed.' }
& (Join-Path $routeRuntime.JavaHome 'bin/java.exe') -cp $routeOutput com.ruoyi.skytwin.RouteEngineChecks
if ($LASTEXITCODE -ne 0) { throw 'Route checks failed.' }
