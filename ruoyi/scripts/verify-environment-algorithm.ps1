. (Join-Path $PSScriptRoot 'common.ps1')
$environmentRuntime = Get-LocalRuntime
$environmentOutput = Join-Path $RuoyiRoot '.runtime/environment-checks'
New-Item -ItemType Directory -Path $environmentOutput -Force | Out-Null
$environmentSource = Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin'
& (Join-Path $environmentRuntime.JavaHome 'bin/javac.exe') -encoding UTF-8 -d $environmentOutput `
    (Join-Path $environmentSource 'AirspaceEngine.java') (Join-Path $environmentSource 'EnvironmentRules.java') (Join-Path $environmentSource 'EnvironmentImage.java') `
    (Join-Path $RuoyiRoot 'backend/ruoyi-admin/src/test/java/com/ruoyi/skytwin/EnvironmentRulesChecks.java')
if ($LASTEXITCODE -ne 0) { throw 'Environment checks compilation failed.' }
& (Join-Path $environmentRuntime.JavaHome 'bin/java.exe') -cp $environmentOutput com.ruoyi.skytwin.EnvironmentRulesChecks
if ($LASTEXITCODE -ne 0) { throw 'Environment checks failed.' }
