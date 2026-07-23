# Operación del piloto Autoridad 360

## Arranque local

**Camino único recomendado:**

```bat
start-pilot.bat
```

Equivale a: Docker Postgres/Redis → `alembic upgrade head` → API/Celery/UI → blog.

Manual:

1. Levantar Postgres y Redis:
   `docker compose -f docker-compose.offline.yml up -d`
2. Ejecutar migraciones:
   `cd backend && venv\Scripts\python.exe -m alembic upgrade head`
3. Iniciar API, workers Celery y admin:
   `start-dev-offline.bat`
4. Iniciar el blog público:
   `start-blog.bat`

La API usa `http://127.0.0.1:8012`, el admin `:3001` y el blog `:3002`.
Los jobs pesados requieren los workers `autoridad-celery-ingest` y
`autoridad-celery-editorial`. El primero no queda bloqueado por inferencias LLM.

## Verificación

- `GET /api/v1/health` informa DB, Redis, Celery y Ollama.
- `GET /api/v1/jobs` permite revisar cola, ejecución y errores.
- En producción, `/docs`, seeds y autenticación por headers están deshabilitados.

## Línea base de rendimiento (20 julio 2026)

Medición sobre `ai_usage_logs` del piloto antes de conectar toda la UI a jobs:

- Clasificación: 33.1 s promedio (103 llamadas).
- Verificación: 33.2 s promedio (93 llamadas).
- Generación de contenido: 82.4 s promedio (479 llamadas).
- Crítica del stack anterior: 55.2 s promedio (122 llamadas).

Un paquete de cuatro formatos podía superar siete minutos al sumar generación,
crítica y reescritura serial. La referencia para comparar mejoras es la duración
total del job y el número de llamadas LLM, no solo el tiempo de respuesta HTTP.

Medición posterior:

- Recolección RSS completa con caché caliente: 12.1 s para 13 categorías y 90
  entradas deduplicadas, sin errores.
- La API encola generación, análisis y reportes sin bloquear la interfaz.
- Un paquete estándar agrupa los cuatro formatos en una inferencia LLM. Si el
  modelo no devuelve algún formato válido, solo ese formato usa la ruta individual.
- La crítica argumentativa adicional queda desactivada por defecto y puede
  habilitarse con `CONTENT_CRITIC_ENABLED=true` cuando la calidad lo requiera.
- Suite final: 98 pruebas backend; build Vite y configuración Docker válidos.

## Backup Postgres

Script:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\backup-postgres.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\restore-postgres.ps1 -DumpPath .\backups\autoridad360-YYYYMMDD.dump
```

Manual (equivalente):

```powershell
docker exec autoridad360-postgres pg_dump -U autoridad -d autoridad360 -Fc -f /tmp/autoridad360.dump
docker cp autoridad360-postgres:/tmp/autoridad360.dump .\backups\autoridad360.dump
```

Guardar el dump fuera del equipo del piloto y registrar fecha, tamaño y responsable.
No incluir `.env`, API keys ni dumps dentro de Git.

## Prueba de restauración

Restaurar primero en una base temporal, nunca sobre el piloto:

```powershell
docker exec autoridad360-postgres createdb -U autoridad autoridad360_restore
docker cp .\backups\autoridad360.dump autoridad360-postgres:/tmp/autoridad360.dump
docker exec autoridad360-postgres pg_restore -U autoridad -d autoridad360_restore --clean --if-exists /tmp/autoridad360.dump
```

Validar tablas principales, login y conteos de artículos, piezas y posts. El backup
no se considera válido hasta completar esta prueba.

## Paso a producción

Ver checklist completo: [`DEPLOY.md`](DEPLOY.md)

- Rotar JWT, cifrado, sesión (`scripts\generate-secrets.ps1`)
- `APP_ENV=production` y orígenes CORS explícitos
- `alembic upgrade head` antes de arrancar la API
- HTTPS + `COOKIE_SECURE=true` + backups automatizados
- Health watch: `scripts\watch-health.ps1`
- Flujo editorial: `docs\FLUJO_EDITORIAL.md` · LinkedIn: `docs\LINKEDIN_LIVE.md`
