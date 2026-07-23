# Restaura un dump en DB temporal autoridad360_restore (nunca sobre el piloto).
# Uso: powershell -ExecutionPolicy Bypass -File .\scripts\restore-postgres.ps1 -DumpPath .\backups\archivo.dump
param(
  [Parameter(Mandatory = $true)][string]$DumpPath
)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $DumpPath)) { throw "Dump no encontrado: $DumpPath" }
$container = "autoridad360-postgres"
$remote = "/tmp/autoridad360_restore.dump"
Write-Host "Creando DB temporal autoridad360_restore ..."
docker exec $container psql -U autoridad -d postgres -c "DROP DATABASE IF EXISTS autoridad360_restore;"
docker exec $container psql -U autoridad -d postgres -c "CREATE DATABASE autoridad360_restore OWNER autoridad;"
docker cp $DumpPath "${container}:${remote}"
docker exec $container pg_restore -U autoridad -d autoridad360_restore --clean --if-exists $remote
docker exec $container rm -f $remote
Write-Host "OK restore en autoridad360_restore. Validar tablas y luego DROP DATABASE."
Write-Host "docker exec $container psql -U autoridad -d autoridad360_restore -c '\dt'"
