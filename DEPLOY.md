# Deploy checklist — Autoridad 360

## Antes de producción

1. Generar secretos distintos (≥32 chars):
   `powershell -File scripts\generate-secrets.ps1`
2. Copiar a `backend/.env` (nunca a git). Rotar si hubo zip/entrega con `.env`.
3. `APP_ENV=production`
4. `COOKIE_SECURE=true` (solo HTTPS)
5. CORS solo orígenes reales (admin + blog)
6. `PUBLISH_NATIVE_LIVE=false` hasta OAuth LinkedIn validado
7. Contraseñas DB distintas del piloto; sin `admin123` en prod
8. `alembic upgrade head` **antes** de arrancar la API
9. Reverse proxy HTTPS; `/docs` queda deshabilitado en production
10. Backup automatizado (`scripts\backup-postgres.ps1`) + restore probado mensualmente

## Arranque canónico (piloto local)

```bat
start-pilot.bat
```

Equivale a: compose offline → alembic → API/Celery/UI → blog.

## Verificación post-arranque

```powershell
Invoke-RestMethod http://127.0.0.1:8012/api/v1/health
Invoke-RestMethod http://127.0.0.1:8012/api/v1/health/ready
powershell -File scripts\watch-health.ps1
```

`ready` debe devolver 200 solo si DB + Redis OK.

## LinkedIn live

Ver `docs/LINKEDIN_LIVE.md` y `docs/FLUJO_EDITORIAL.md`.

## SEO / dominio público

1. Apuntar DNS del dominio al host del blog
2. Verificar dominio custom en admin → Organización (status `verified`)
3. Google Search Console → propiedad del dominio → enviar `https://dominio/sitemap.xml`
4. Confirmar `robots.txt` Allow + Sitemap

## No hacer en prod

- Confiar en `create_all` como migración
- `PUBLISH_NATIVE_LIVE=true` sin token real
- Publicar 6 redes a la vez sin assets/aprobación
- Botón “Generar SEO” masivo
