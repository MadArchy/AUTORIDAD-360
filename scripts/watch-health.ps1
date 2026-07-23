# Poll health y alerta en consola si DB/Redis caen.
# Uso: powershell -ExecutionPolicy Bypass -File .\scripts\watch-health.ps1 [-ApiUrl http://127.0.0.1:8012]
param(
  [string]$ApiUrl = "http://127.0.0.1:8012",
  [int]$IntervalSec = 30
)
$ErrorActionPreference = "Continue"
Write-Host "Watching $ApiUrl/api/v1/health every ${IntervalSec}s (Ctrl+C to stop)"
while ($true) {
  $ts = Get-Date -Format "HH:mm:ss"
  try {
    $h = Invoke-RestMethod "$ApiUrl/api/v1/health" -TimeoutSec 5
    $db = $h.dependencies.database.ok
    $redis = $h.dependencies.redis.ok
    $celery = $h.dependencies.celery.ok
    $line = "[$ts] status=$($h.status) db=$db redis=$redis celery=$celery workers=$($h.dependencies.celery.workers)"
    if ($h.status -ne "ok" -or -not $db -or -not $redis) {
      Write-Host "ALERT $line" -ForegroundColor Red
    } elseif (-not $celery) {
      Write-Host "WARN  $line (Celery down)" -ForegroundColor Yellow
    } else {
      Write-Host "OK    $line" -ForegroundColor Green
    }
  } catch {
    Write-Host "ALERT [$ts] API unreachable: $($_.Exception.Message)" -ForegroundColor Red
  }
  Start-Sleep -Seconds $IntervalSec
}
