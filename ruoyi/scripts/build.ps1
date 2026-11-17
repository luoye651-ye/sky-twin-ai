param([ValidateSet('all', 'backend', 'frontend')][string]$Target = 'all')
. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
if ($Target -in @('all', 'backend')) {
    $previousJava = $env:JAVA_HOME
    $previousMaven = $env:MAVEN_OPTS
    try {
        $env:JAVA_HOME = $runtime.JavaHome
        $env:MAVEN_OPTS = '-Xmx1024m -Dfile.encoding=UTF-8'
        Push-Location (Join-Path $RuoyiRoot 'backend')
        & $runtime.MavenExecutable -B -ntp -s (Join-Path $RuoyiRoot 'config/maven-settings.xml') `
            "-Dmaven.repo.local=$RuoyiRoot/.runtime/maven-repository" -DskipTests package
        if ($LASTEXITCODE -ne 0) { throw 'Backend build failed.' }
    } finally {
        Pop-Location
        $env:JAVA_HOME = $previousJava
        $env:MAVEN_OPTS = $previousMaven
    }
}
if ($Target -in @('all', 'frontend')) {
    Push-Location (Join-Path $RuoyiRoot 'frontend')
    try {
        & $runtime.NodeExecutable (Join-Path $RuoyiRoot 'frontend/node_modules/vite/bin/vite.js') build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    } finally { Pop-Location }
}
