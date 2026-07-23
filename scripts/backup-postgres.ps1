# Backup Postgres offline (contenedor autoridad360-postgres).
# Uso: powershell -ExecutionPolicy Bypass -File .\scripts\backup-postgres.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$OutDir = Join-Path $Root "backups"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$local = Join-Path $OutDir "autoridad360-$stamp.dump"
$container = "autoridad360-postgres"
$remote = "/tmp/autoridad360-$stamp.dump"

Write-Host "Dumping $container ..."
docker exec $container pg_dump -U autoridad -d autoridad360 -Fc -f $remote
docker cp "${container}:${remote}" $local
docker exec $container rm -f $remote
$size = (Get-Item $local).Length
Write-Host "OK: $local ($([math]::Round($size/1KB,1)) KB)"
Write-Host "Registrar fecha, tamaño y responsable fuera del repo."
