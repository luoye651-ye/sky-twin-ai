param(
    [string]$MySqlBin = 'C:\Program Files\MySQL\MySQL Server 8.0\bin',
    [string]$RedisSource = 'D:\redis',
    [string]$NodeExecutable = '',
    [ValidateRange(1, 65535)][int]$RedisPort = 16380
)
. (Join-Path $PSScriptRoot 'common.ps1')

foreach ($directory in @('.runtime', '.runtime/redis', 'config', 'data/mysql', 'data/redis', 'data/uploads', 'logs')) {
    New-Item -ItemType Directory -Path (Join-Path $RuoyiRoot $directory) -Force | Out-Null
}
if (-not $NodeExecutable) { $NodeExecutable = (Get-Command node.exe).Source }
$jdk = Get-ChildItem (Join-Path $RuoyiRoot '.runtime') -Directory -Filter 'jdk-17*' | Select-Object -First 1
$maven = Get-ChildItem (Join-Path $RuoyiRoot '.runtime') -Directory -Filter 'apache-maven-3.9*' | Select-Object -First 1
if (-not $jdk -or -not $maven) { throw 'Portable JDK 17 and Maven 3.9 are required under .runtime.' }
foreach ($file in @('mysqld.exe', 'mysql.exe', 'mysqladmin.exe')) {
    if (-not (Test-Path -LiteralPath (Join-Path $MySqlBin $file))) { throw "Missing MySQL binary: $file" }
}
foreach ($file in @('redis-server.exe', 'redis-cli.exe', 'msys-2.0.dll', 'msys-crypto-3.dll', 'msys-gcc_s-seh-1.dll', 'msys-ssl-3.dll', 'msys-stdc++-6.dll')) {
    $source = Join-Path $RedisSource $file
    if (Test-Path -LiteralPath $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $RuoyiRoot '.runtime/redis') -Force
    }
}
if (-not (Test-Path (Join-Path $RuoyiRoot '.runtime/redis/redis-server.exe'))) {
    throw 'Redis executable was not found.'
}
$runtime = [ordered]@{
    JavaHome = $jdk.FullName
    MavenExecutable = Join-Path $maven.FullName 'bin/mvn.cmd'
    NodeExecutable = $NodeExecutable
    MySqlBin = $MySqlBin
    RedisBin = Join-Path $RuoyiRoot '.runtime/redis'
    RedisPort = $RedisPort
}
$runtime | ConvertTo-Json | Set-Content -LiteralPath $RuntimeFile -Encoding UTF8

function New-LocalSecret {
    $bytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return [BitConverter]::ToString($bytes).Replace('-', '').ToLowerInvariant()
}
if (-not (Test-Path -LiteralPath $SecretsFile)) {
    [ordered]@{
        MySqlRootPassword = New-LocalSecret
        DbPassword = New-LocalSecret
        RedisPassword = New-LocalSecret
        TokenSecret = New-LocalSecret
    } | ConvertTo-Json | Set-Content -LiteralPath $SecretsFile -Encoding UTF8
}
$secrets = Get-LocalSecrets
$rootForward = $RuoyiRoot.Replace('\', '/')
$mysqlBase = (Split-Path $MySqlBin -Parent).Replace('\', '/')
@"
[mysqld]
basedir="$mysqlBase"
datadir="$rootForward/data/mysql"
port=3307
bind-address=127.0.0.1
mysqlx=OFF
server-id=3307
character-set-server=utf8mb4
collation-server=utf8mb4_unicode_ci
max_connections=100
innodb_buffer_pool_size=128M
log-error="$rootForward/logs/mysql.error.log"
pid-file="$rootForward/logs/mysql.pid"
"@ | Set-Content (Join-Path $RuoyiRoot 'config/mysql.ini') -Encoding ASCII
@"
[client]
protocol=tcp
host=127.0.0.1
port=3307
user=root
password=$($secrets.MySqlRootPassword)
default-character-set=utf8mb4
"@ | Set-Content (Join-Path $RuoyiRoot 'config/mysql-root.cnf') -Encoding ASCII
@"
bind 127.0.0.1
protected-mode yes
port $RedisPort
requirepass $($secrets.RedisPassword)
dir "./data/redis"
dbfilename dump.rdb
appendonly yes
appenddirname "appendonlydir"
save 60 1
logfile ""
"@ | Set-Content (Join-Path $RuoyiRoot 'config/redis.conf') -Encoding ASCII
Write-Host 'Local runtime and private configuration are ready. Secrets were not printed.'
