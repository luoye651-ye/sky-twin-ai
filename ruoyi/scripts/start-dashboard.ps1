. (Join-Path $PSScriptRoot 'common.ps1')
$runtime = Get-LocalRuntime
$projectRoot = Split-Path $RuoyiRoot -Parent
$dashboard = Join-Path $projectRoot 'frontend'
Start-ManagedProcess -Name dashboard -Executable $runtime.NodeExecutable `
    -Arguments @("`"$(Join-Path $dashboard 'node_modules/vite/bin/vite.js')`"", '--host', '127.0.0.1', '--port', '5173', '--strictPort') `
    -WorkingDirectory $dashboard -Port 5173
Wait-LocalPort 5173
Write-Host 'SkyTwin command center: http://127.0.0.1:5173'
