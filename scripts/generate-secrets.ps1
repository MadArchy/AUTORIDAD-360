param(
  [ValidateSet("pilot", "production")]
  [string]$AppEnv = "pilot"
)

# Genera secretos distintos (>=32 chars) para produccion / piloto.
# Uso: powershell -ExecutionPolicy Bypass -File .\scripts\generate-secrets.ps1 -AppEnv pilot
function New-Secret([int]$n = 36) {
  $b = New-Object byte[] $n
  [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($b)
  return ([Convert]::ToBase64String($b).TrimEnd('=') -replace '\+','x' -replace '/','y')
}
Write-Output "APP_ENV=$AppEnv"
Write-Output "JWT_SECRET_KEY=$(New-Secret)"
Write-Output "API_KEY_ENCRYPTION_KEY=$(New-Secret)"
Write-Output "SESSION_SECRET_KEY=$(New-Secret)"
Write-Output "ENCRYPTION_KEY=$(New-Secret)"
Write-Output "DEV_SEED_PASSWORD=$(New-Secret 24)"
Write-Output ""
Write-Output "# Copia estas lineas a backend/.env (nunca a git). Reinicia API y fuerza re-login."
