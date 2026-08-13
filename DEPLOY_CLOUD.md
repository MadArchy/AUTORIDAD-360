# 🚀 Deploy Autoridad 360 a Internet

## Arquitectura final

```
Vercel (Frontend)  →  Railway (API + MySQL + Redis)  →  Ollama (tu PC, túnel Cloudflare)
```

---

## Paso 1 — Generar secretos de producción

Abre PowerShell y ejecuta:

```powershell
# Genera 4 secretos distintos de 64 caracteres
1..4 | ForEach-Object { -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | % {[char]$_}) }
```

Guarda los 4 valores — los usarás en Railway como:
- `JWT_SECRET_KEY`
- `API_KEY_ENCRYPTION_KEY`
- `SESSION_SECRET_KEY`
- `ENCRYPTION_KEY`

---

## Paso 2 — Subir código a GitHub

```powershell
cd "c:\Users\user\Desktop\autoridad 360"
git add backend/Dockerfile backend/entrypoint.sh backend/.env.railway.example
git add frontend/vite.config.js frontend/vercel.json frontend/.env.production
git add railway.json
git commit -m "feat: preparar deploy Railway + Vercel"
git push origin main
```

> [!CAUTION]
> Verifica que `.env` y `.env.production` (con valores reales) estén en `.gitignore` y **no** se suban a GitHub.

---

## Paso 3 — Deploy Backend en Railway

1. Ve a **[railway.app](https://railway.app)** → New Project → Deploy from GitHub repo
2. Selecciona el repositorio
3. Railway detectará el `railway.json` → usará el `backend/Dockerfile`
4. En el proyecto, haz clic en **"Add Plugin"**:
   - ✅ Add **MySQL** → Railway genera `DATABASE_URL` automáticamente
   - ✅ Add **Redis** → Railway genera `REDIS_URL` automáticamente
5. Ve a **Variables** del servicio backend y agrega (ver `.env.railway.example`)

---

## Paso 4 — Exponer Ollama con Cloudflare Tunnel (gratis)

Con Ollama corriendo en tu PC:

```powershell
# Instala cloudflared (una sola vez)
winget install Cloudflare.cloudflared

# Crea el túnel temporal (sin cuenta)
cloudflared tunnel --url http://localhost:11434
```

Cloudflare te dará una URL como `https://abc-def.trycloudflare.com`.
Ponla en `OLLAMA_BASE_URL` en Railway.

---

## Paso 5 — Deploy Frontend en Vercel

1. Ve a **[vercel.com](https://vercel.com)** → New Project → Import desde GitHub
2. **Root Directory**: `frontend`
3. **Environment Variables**:
   - `VITE_API_URL` = `https://TU-BACKEND.up.railway.app/api/v1`
4. Click **Deploy**

---

## Paso 6 — Actualizar CORS en Railway

Una vez tengas la URL de Vercel, en Railway → Variables:

```
CORS_ORIGINS=https://TU-PROYECTO.vercel.app
```

---

## Paso 7 — Verificación

```powershell
Invoke-RestMethod https://TU-BACKEND.up.railway.app/api/v1/health
Invoke-RestMethod https://TU-BACKEND.up.railway.app/api/v1/health/ready
```

Abre `https://TU-PROYECTO.vercel.app` → Login → verifica que los artículos carguen ✅

---

## Resumen de URLs finales

| Servicio | URL |
|---|---|
| 🖥️ **Admin** | `https://autoridad360-xxx.vercel.app` |
| ⚙️ **API** | `https://autoridad360-xxx.up.railway.app` |
| 🗄️ **MySQL** | Gestionado por Railway (interno) |
| 🔴 **Redis** | Gestionado por Railway (interno) |
| 🤖 **Ollama** | Tu PC con Cloudflare Tunnel |
