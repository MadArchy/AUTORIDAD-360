@echo off
REM Camino unico del piloto offline: compose + alembic + API/Celery/UI + blog
set ROOT=%~dp0
cd /d "%ROOT%"

echo [1/4] Docker Postgres+Redis...
docker compose -f docker-compose.offline.yml up -d --wait
if errorlevel 1 (
  echo ERROR: docker compose fallo
  exit /b 1
)

echo [2/4] Alembic upgrade head...
cd /d "%ROOT%backend"
if not defined DATABASE_URL set DATABASE_URL=postgresql+psycopg2://autoridad:autoridadpass@127.0.0.1:5433/autoridad360
if not defined APP_ENV set APP_ENV=development
.\venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 (
  echo ERROR: migraciones fallaron
  exit /b 1
)

echo [3/4] API + Celery + Admin...
cd /d "%ROOT%"
call start-dev-offline.bat

echo [4/4] Blog estatico :3002...
if exist "%ROOT%start-blog-static.bat" (
  start "autoridad-blog-3002" cmd /c "%ROOT%start-blog-static.bat"
) else if exist "%ROOT%start-blog.bat" (
  start "autoridad-blog-3002" cmd /c "%ROOT%start-blog.bat"
)

echo.
echo Piloto listo:
echo   Admin  http://127.0.0.1:3001
echo   Blog   http://127.0.0.1:3002
echo   API    http://127.0.0.1:8012/api/v1/health
echo   Docs   http://127.0.0.1:8012/docs
echo.
echo Health watch: powershell -File scripts\watch-health.ps1
exit /b 0
