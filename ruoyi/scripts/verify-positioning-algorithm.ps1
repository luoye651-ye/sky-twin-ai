. (Join-Path $PSScriptRoot 'common.ps1')
$positionRuntime = Get-LocalRuntime
$positionOutput = Join-Path $RuoyiRoot '.runtime/positioning-checks'
New-Item -ItemType Directory -Path $positionOutput -Force | Out-Null
& (Join-Path $positionRuntime.JavaHome 'bin/javac.exe') -encoding UTF-8 -d $positionOutput `
    (Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/PositionRules.java') `
    (Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/test/java/com/ruoyi/skytwin/PositionRulesChecks.java') `
    (Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/NmeaGga.java') `
    (Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/test/java/com/ruoyi/skytwin/NmeaGgaChecks.java')
if ($LASTEXITCODE -ne 0) { throw 'Positioning checks compilation failed.' }
& (Join-Path $positionRuntime.JavaHome 'bin/java.exe') -cp $positionOutput com.ruoyi.skytwin.PositionRulesChecks
if ($LASTEXITCODE -ne 0) { throw 'Positioning algorithm verification failed.' }
& (Join-Path $positionRuntime.JavaHome 'bin/java.exe') -cp $positionOutput com.ruoyi.skytwin.NmeaGgaChecks
if ($LASTEXITCODE -ne 0) { throw 'NMEA adapter verification failed.' }
