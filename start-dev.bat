@echo off
REM Docker canónico: API 8000 + MySQL 3307 (docker compose up)
REM Piloto local: puede usar 8012 si ya hay uvicorn ahí
cd /d "%~dp0backend"
if not defined DATABASE_URL set DATABASE_URL=mysql+pymysql://autoridad:autoridadpass@127.0.0.1:3307/autoridad360
if not defined APP_ENV set APP_ENV=development
if not defined JWT_SECRET_KEY set JWT_SECRET_KEY=dev-jwt-secret-rotate-before-prod-32c
if not defined ENCRYPTION_KEY set ENCRYPTION_KEY=dev-api-encrypt-rotate-before-prod-32
set OLLAMA_BASE_URL=http://127.0.0.1:11434
set OLLAMA_MODEL=gemma4:e2b
set CORS_ORIGINS=http://localhost:3000,http://localhost:3001,http://localhost:3002,http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3002
start "autoridad-api" cmd /k ".\venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000"
cd /d "%~dp0frontend"
set VITE_API_URL=http://127.0.0.1:8000/api/v1
set VITE_PUBLIC_BLOG_URL=http://127.0.0.1:3002
start "autoridad-ui" cmd /k "npm run dev -- --host 127.0.0.1 --port 3001 --strictPort"
echo.
echo Admin http://127.0.0.1:3001
echo Blog  http://127.0.0.1:3002  (start-blog.bat)
echo API   http://127.0.0.1:8000
echo Docs  http://127.0.0.1:8000/docs
