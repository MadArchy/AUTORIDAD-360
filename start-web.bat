@echo off
REM ============================================================
REM  Autoridad 360 — Modo Web (un solo puerto, tunel HTTPS)
REM ============================================================
setlocal
set ROOT=%~dp0

echo.
echo =========================================
echo   AUTORIDAD 360 — Modo WEB
echo =========================================
echo.

REM 1. Infraestructura Docker
echo [1/4] Levantando MySQL y Redis...
docker compose up -d mysql redis
if errorlevel 1 (
    echo ERROR: Docker no inicio. Abre Docker Desktop primero.
    pause & exit /b 1
)
echo       OK.
echo.

REM 2. Build del frontend
echo [2/4] Compilando frontend...
cd /d "%ROOT%frontend"
call npm run build
if errorlevel 1 (
    echo ERROR: Fallo el build del frontend.
    pause & exit /b 1
)
echo       OK - frontend\dist\ listo.
echo.

REM 3. Backend en ventana separada
echo [3/4] Iniciando backend en :8010...
start "autoridad-api" cmd /c "cd /d ""%ROOT%backend"" && set APP_ENV=development&& set OLLAMA_BASE_URL=http://127.0.0.1:11434&& set CORS_ORIGINS=*&& .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8010 & pause"
echo       Backend iniciando...
timeout /t 5 /nobreak >nul
echo.

REM 4. Tunel Cloudflare
echo [4/4] Abriendo tunel HTTPS publico...
echo.
echo  Busca la linea:
echo  https://XXXXXXXX.trycloudflare.com
echo  Esa es tu URL publica.
echo.
echo  Cierra esta ventana para detener el tunel.
echo.

where cloudflared >nul 2>&1
if errorlevel 1 (
    echo Instalando cloudflared...
    winget install Cloudflare.cloudflared --silent
)

cloudflared tunnel --url http://127.0.0.1:8010
pause
