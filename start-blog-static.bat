@echo off
REM Blog publico SIN npm (puente estatico) — evita TLS/npm rotos
cd /d "%~dp0frontend-blog\static"
set PY=%~dp0backend\venv\Scripts\python.exe
if not exist "%PY%" set PY=py
start "autoridad-blog-static-3002" cmd /k "%PY% server.py"
echo.
echo Blog estatico  http://127.0.0.1:3002
echo Admin Vite     http://127.0.0.1:3001
echo.
echo Cuando TLS/npm funcionen: cd frontend-blog ^&^& npm install ^&^& npm run dev
