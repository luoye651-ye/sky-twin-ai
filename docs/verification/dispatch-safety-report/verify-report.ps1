param([string]$JdkHome = '', [string]$OutputDirectory = '')
$ErrorActionPreference = 'Stop'
$reportRoot = $PSScriptRoot
$projectRoot = [IO.Path]::GetFullPath((Join-Path $reportRoot '../../..'))
if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $projectRoot 'tmp/dispatch-safety-report-replay'
}
$reportOutput = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $reportOutput -Force | Out-Null
$classesOutput = Join-Path $projectRoot 'tmp/dispatch-safety-report-classes'
New-Item -ItemType Directory -Path $classesOutput -Force | Out-Null
if ($JdkHome) {
    $compiler = Join-Path $JdkHome 'bin/javac.exe'
    $javaRunner = Join-Path $JdkHome 'bin/java.exe'
} elseif (Test-Path -LiteralPath (Join-Path $projectRoot 'ruoyi/config/runtime.local.json')) {
    # Read the JDK location only; do not read secrets or connect to business services.
    $localRuntime = Get-Content -Raw -LiteralPath (Join-Path $projectRoot 'ruoyi/config/runtime.local.json') | ConvertFrom-Json
    $compiler = Join-Path $localRuntime.JavaHome 'bin/javac.exe'
    $javaRunner = Join-Path $localRuntime.JavaHome 'bin/java.exe'
} else {
    $compiler = (Get-Command javac -ErrorAction Stop).Source
    $javaRunner = (Get-Command java -ErrorAction Stop).Source
}
$optimizer = Join-Path $projectRoot 'ruoyi/backend/ruoyi-admin/src/main/java/com/ruoyi/skytwin/DispatchOptimizer.java'
$checks = Join-Path $projectRoot 'ruoyi/backend/ruoyi-admin/src/test/java/com/ruoyi/skytwin/DispatchOptimizerChecks.java'
$benchmark = Join-Path $reportRoot 'SummaryBenchmark.java'
$compileOutput = @(& $compiler -encoding UTF-8 -d $classesOutput $optimizer $checks $benchmark 2>&1)
$compileExit = $LASTEXITCODE
$compileOutput | Out-File -FilePath (Join-Path $reportOutput 'compile.log') -Encoding utf8
if ($compileExit -ne 0) { throw 'Compilation failed; use JDK 17 or newer and inspect compile.log.' }
$checksOutput = @(& $javaRunner -cp $classesOutput com.ruoyi.skytwin.DispatchOptimizerChecks 2>&1)
$checksExit = $LASTEXITCODE
$checksOutput | Out-File -FilePath (Join-Path $reportOutput 'algorithm-checks.log') -Encoding utf8
if ($checksExit -ne 0) { throw 'Optimizer checks failed.' }
$benchmarkOutput = @(& $javaRunner -cp $classesOutput SummaryBenchmark $reportOutput 2>&1)
$benchmarkExit = $LASTEXITCODE
$benchmarkOutput | Out-File -FilePath (Join-Path $reportOutput 'benchmark.log') -Encoding utf8
if ($benchmarkExit -ne 0) { throw 'Benchmark failed; do not use the submitted metrics without investigating.' }
$sourceHashes = @($optimizer, $checks, $benchmark, $PSCommandPath) | ForEach-Object {
    [ordered]@{ file = $_.Substring($projectRoot.Length + 1).Replace('\','/'); sha256 = (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash.ToLower() }
}
$runtimeText = @(& $compiler -version 2>&1)
[ordered]@{
    capturedAt = (Get-Date).ToString('o')
    protocol = 'summary-offline-v1'
    javaCompiler = ($runtimeText -join ' ')
    execution = 'offline; no business API, database, model API, or flight operation'
    checks = ($checksOutput -join ' ')
    sources = $sourceHashes
} | ConvertTo-Json -Depth 6 | Out-File -FilePath (Join-Path $reportOutput 'run-manifest.json') -Encoding utf8
$checksOutput | Write-Output
$benchmarkOutput | Write-Output
Write-Output "Evidence directory: $reportOutput"
