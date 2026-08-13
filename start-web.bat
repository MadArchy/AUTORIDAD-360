@echo off
REM ============================================================
REM  Autoridad 360 — App Web completa (sin cuentas externas)
REM  Sirve frontend + API desde un solo puerto via tunel HTTPS
REM ============================================================
setlocal

cd /d "%~dp0"

echo.
echo =========================================
echo   AUTORIDAD 360 — Iniciando modo WEB
echo =========================================
echo.

REM --- 1. Infraestructura Docker (MySQL + Redis) ---
echo [1/4] Levantando MySQL y Redis (Docker)...
docker compose up -d mysql redis
if errorlevel 1 (
    echo ERROR: Docker no pudo iniciar MySQL/Redis.
    echo Asegurate de que Docker Desktop este corriendo.
    pause
    exit /b 1
)
echo       MySQL y Redis OK.
echo.

REM --- 2. Build del frontend ---
echo [2/4] Compilando frontend React...
cd /d "%~dp0frontend"
call npm run build
if errorlevel 1 (
    echo ERROR: Fallo el build del frontend.
    pause
    exit /b 1
)
echo       Build OK (frontend\dist\ listo).
echo.

REM --- 3. Backend FastAPI (sirve API + frontend) ---
echo [3/4] Iniciando backend (API + Frontend estatico)...
cd /d "%~dp0backend"
set APP_ENV=development
set OLLAMA_BASE_URL=http://127.0.0.1:11434
set OLLAMA_MODEL=gemma4:e2b
set CORS_ORIGINS=*
start "autoridad-api" cmd /k "cd /d "%~dp0backend" && .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8010"
echo       Backend iniciando en puerto 8010...
echo.

REM --- 4. Cloudflare Quick Tunnel (sin cuenta) ---
echo [4/4] Iniciando tunel Cloudflare (HTTPS publico)...
echo.
echo IMPORTANTE: La URL publica aparecera abajo en unos segundos.
echo             Busca una linea como:
echo             https://XXXXXXXX.trycloudflare.com
echo.
echo Deja esta ventana abierta. Cierra para detener el tunel.
echo.

REM Verificar si cloudflared esta instalado
where cloudflared >nul 2>&1
if errorlevel 1 (
    echo cloudflared no encontrado. Instalando...
    winget install Cloudflare.cloudflared --silent
    if errorlevel 1 (
        echo.
        echo ERROR: No se pudo instalar cloudflared automaticamente.
        echo Instala manualmente desde: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
        echo Luego ejecuta: cloudflared tunnel --url http://127.0.0.1:8010
        pause
        exit /b 1
    )
)

REM Esperar a que el backend arranque
timeout /t 4 /nobreak >nul

cloudflared tunnel --url http://127.0.0.1:8010

pause
