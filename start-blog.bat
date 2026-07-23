@echo off
REM Preferir puente estatico si npm/TLS falla
cd /d "%~dp0"
if exist "frontend-blog\node_modules\next\package.json" (
  cd frontend-blog
  if not defined NEXT_PUBLIC_API_URL set NEXT_PUBLIC_API_URL=http://127.0.0.1:8012/api/v1
  start "autoridad-blog-3002" cmd /k "npm run dev"
  echo Blog Next.js  http://127.0.0.1:3002
) else (
  echo Next.js no instalado — usando blog estatico (sin npm^)
  call "%~dp0start-blog-static.bat"
)
