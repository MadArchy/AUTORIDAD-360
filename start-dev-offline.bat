@echo off
REM Puente offline: Postgres 5433 + Redis + API 8012 (cuando MySQL pull falla)
REM Requiere: docker compose -f docker-compose.offline.yml up -d
cd /d "%~dp0backend"
if not defined DATABASE_URL set DATABASE_URL=postgresql+psycopg2://autoridad:autoridadpass@127.0.0.1:5433/autoridad360
if not defined APP_ENV set APP_ENV=development
if not defined JWT_SECRET_KEY set JWT_SECRET_KEY=autoridad360-jwt-dev-secret-change-me-32
if not defined ENCRYPTION_KEY set ENCRYPTION_KEY=autoridad360-enc-dev-secret-change-me-32
if not defined API_KEY_ENCRYPTION_KEY set API_KEY_ENCRYPTION_KEY=autoridad360-enc-dev-secret-change-me-32
if not defined SESSION_SECRET_KEY set SESSION_SECRET_KEY=autoridad360-session-dev-secret-32ch
set REDIS_URL=redis://127.0.0.1:6379/0
set CELERY_BROKER_URL=redis://127.0.0.1:6379/0
set OLLAMA_BASE_URL=http://127.0.0.1:11434
set OLLAMA_MODEL=gemma4:e2b
set CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002
echo Migraciones Alembic...
.\venv\Scripts\python.exe -m alembic upgrade head
if errorlevel 1 (
  echo ERROR alembic — abortando
  exit /b 1
)
start "autoridad-api-8012" cmd /k ".\venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8012"
REM Workers separados: RSS no bloquea la cola editorial/LLM.
start "autoridad-celery-ingest" cmd /k ".\venv\Scripts\celery.exe -A app.tasks.celery_app worker --loglevel=info --pool=solo -Q ingest -n ingest@%%COMPUTERNAME%%"
start "autoridad-celery-editorial" cmd /k ".\venv\Scripts\celery.exe -A app.tasks.celery_app worker --loglevel=info --pool=solo -Q llm,generate,celery -n editorial@%%COMPUTERNAME%%"
cd /d "%~dp0frontend"
set VITE_API_URL=http://127.0.0.1:8012/api/v1
set VITE_PUBLIC_BLOG_URL=http://127.0.0.1:3002
start "autoridad-ui" cmd /k "npm run dev -- --host 127.0.0.1 --port 3001 --strictPort"
echo.
echo Admin http://127.0.0.1:3001
echo Blog  http://127.0.0.1:3002  (start-blog.bat)
echo API   http://127.0.0.1:8012  (Postgres offline)
echo Celery workers ingest/editorial requeridos para jobs async
echo Docs  http://127.0.0.1:8012/docs
