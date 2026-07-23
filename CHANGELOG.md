# Changelog

## 0.8.0 — 2026-07-22

### Producción / ops
- `start-pilot.bat`: compose + alembic + API/Celery/UI + blog
- Scripts: `generate-secrets`, `backup-postgres`, `restore-postgres`, `watch-health`
- `DEPLOY.md`, `docs/FLUJO_EDITORIAL.md`, `docs/LINKEDIN_LIVE.md`
- `GET /health/ready` (503 si DB/Redis caídos)

### Producto
- Branding público por hostname (`GET /public/branding`) aplicado al blog estático
- Captura pública de leads con UTM (`POST /public/leads`) + formulario en blog
- Refresh: `POST /saas/refresh/{id}/start` crea draft v+1
- Atribución: `GET /marketing/attribution`
- Extracción de claims adjunta evidencia candidata desde `source_url`
- Seed prompts por canal: `POST /seo-legal/prompts/seed-channels`

### Ingeniería
- GitHub Actions CI (ruff selectivo + pytest unit)
- VERSION / CHANGELOG
