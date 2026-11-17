param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$aiRoot = Split-Path $PSScriptRoot -Parent
$spec = Get-Content -LiteralPath (Join-Path $aiRoot 'env-spec.json') -Raw | ConvertFrom-Json
$venvPython = Join-Path $aiRoot '.venv/Scripts/python.exe'
$minor = & $Python -c 'import sys; print(*sys.version_info[:2], sep=chr(46))'
if ($LASTEXITCODE -ne 0 -or $minor.Trim() -ne $spec.python_minor) { throw "Expected Python $($spec.python_minor), got $minor" }
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv (Join-Path $aiRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
}
foreach ($phase in $spec.pip_phases) {
    & $venvPython -m pip install --disable-pip-version-check --index-url $phase.index @($phase.packages)
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed; do not start training.' }
}
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency verification failed' }
& $venvPython -m pip install --disable-pip-version-check --index-url 'https://pypi.org/simple' -r (Join-Path $aiRoot 'requirements-lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Locked dependency installation failed' }
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Locked dependency verification failed' }
Write-Host "Environment installed: $venvPython (run river_yolo.py check next)."
