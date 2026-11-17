$ErrorActionPreference = 'Stop'
$RuoyiRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$RuntimeFile = Join-Path $RuoyiRoot 'config/runtime.local.json'
$SecretsFile = Join-Path $RuoyiRoot 'config/local-secrets.json'
$ProcessFile = Join-Path $RuoyiRoot 'logs/processes.json'

function Get-LocalRuntime {
    if (-not (Test-Path -LiteralPath $RuntimeFile)) {
        throw 'Run scripts/configure-local.ps1 first.'
    }
    Get-Content -Raw -LiteralPath $RuntimeFile | ConvertFrom-Json
}

function Get-LocalSecrets {
    if (-not (Test-Path -LiteralPath $SecretsFile)) {
        throw 'Run scripts/configure-local.ps1 first.'
    }
    Get-Content -Raw -LiteralPath $SecretsFile | ConvertFrom-Json
}

# Keep all clients on the same project Redis port. Existing runtime files
# without this field use the new default outside Windows' reserved range.
function Get-LocalRedisPort($Runtime = (Get-LocalRuntime)) {
    $port = 16380
    if ($null -ne $Runtime.RedisPort) { $port = [int]$Runtime.RedisPort }
    if ($port -lt 1 -or $port -gt 65535) { throw 'RedisPort must be between 1 and 65535.' }
    return $port
}

function Test-LocalPort([int]$Port) {
    $client = New-Object Net.Sockets.TcpClient
    try {
        $connect = $client.ConnectAsync('127.0.0.1', $Port)
        if (-not $connect.Wait(500)) { return $false }
        return $client.Connected
    } catch { return $false }
    finally { $client.Dispose() }
}

function Get-ManagedRecords {
    if (Test-Path -LiteralPath $ProcessFile) {
        $parsed = Get-Content -Raw -LiteralPath $ProcessFile | ConvertFrom-Json
        foreach ($record in $parsed) {
            Write-Output $record
        }
    }
}

function Get-ManagedProcess($Record) {
    if (-not $Record) { return $null }
    $process = Get-Process -Id $Record.ProcessId -ErrorAction SilentlyContinue
    if (-not $process) { return $null }
    # Check executable and start time: never stop another process after PID reuse.
    if ($process.Path -ne $Record.Executable) { return $null }
    $recordedStart = [DateTime]$Record.StartedUtc
    if ($process.StartTime.ToUniversalTime().Ticks -ne $recordedStart.ToUniversalTime().Ticks) {
        return $null
    }
    return $process
}

function Start-ManagedProcess {
    param([string]$Name, [string]$Executable, [string[]]$Arguments,
          [string]$WorkingDirectory, [int]$Port)
    $records = @(Get-ManagedRecords)
    $record = $records | Where-Object { $_.Name -eq $Name } | Select-Object -First 1
    $running = Get-ManagedProcess $record
    if ($running) {
        Write-Host "$Name is already running (PID $($running.Id))."
        return
    }
    if (Test-LocalPort $Port) {
        throw "Port $Port is in use by an unmanaged process; nothing was stopped."
    }
    $process = Start-Process -FilePath $Executable -ArgumentList $Arguments `
        -WorkingDirectory $WorkingDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $RuoyiRoot "logs/$Name.stdout.log") `
        -RedirectStandardError (Join-Path $RuoyiRoot "logs/$Name.stderr.log")
    $newRecord = [pscustomobject]@{
        Name = $Name
        ProcessId = $process.Id
        Executable = [IO.Path]::GetFullPath($Executable)
        StartedUtc = $process.StartTime.ToUniversalTime().ToString('o')
        Port = $Port
    }
    $updated = @($records | Where-Object { $_.Name -ne $Name }) + @($newRecord)
    ConvertTo-Json -InputObject $updated | Set-Content -LiteralPath $ProcessFile -Encoding UTF8
    Write-Host "Started $Name (PID $($process.Id), port $Port)."
}

function Wait-LocalPort([int]$Port, [int]$Seconds = 60) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-LocalPort $Port) { return }
        Start-Sleep -Seconds 1
    }
    throw "Port $Port did not become ready. See ruoyi/logs."
}

function Set-BackendEnvironment {
    $secrets = Get-LocalSecrets
    $env:SKYTWIN_DB_PASSWORD = $secrets.DbPassword
    $env:SKYTWIN_REDIS_PASSWORD = $secrets.RedisPassword
    $env:SKYTWIN_REDIS_PORT = [string](Get-LocalRedisPort)
    $env:SKYTWIN_TOKEN_SECRET = $secrets.TokenSecret
    $env:SKYTWIN_UPLOAD_DIR = (Join-Path $RuoyiRoot 'data/uploads').Replace('\', '/')
    $env:SKYTWIN_LOG_DIR = (Join-Path $RuoyiRoot 'logs').Replace('\', '/')
}
