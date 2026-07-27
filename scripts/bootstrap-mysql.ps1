$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$env:DATABASE_URL = "mysql+pymysql://autoridad:autoridadpass@127.0.0.1:3307/autoridad360"
$env:APP_ENV = "development"

Push-Location $Backend
try {
  & .\venv\Scripts\python.exe -c "import app.models; from app.models import Base, engine; Base.metadata.create_all(bind=engine)"
  & .\venv\Scripts\python.exe -m alembic stamp head
  Write-Host "MySQL bootstrap completo y Alembic marcado en head."
}
finally {
  Pop-Location
}
