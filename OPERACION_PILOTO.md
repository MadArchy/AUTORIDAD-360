# Operación del piloto Autoridad 360

## Arranque local

### Stack canónico MySQL (recomendado)

```bat
docker compose up -d --build
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000
```

- API: `http://127.0.0.1:8000`
- Admin: `http://127.0.0.1:3000` (`VITE_API_URL=http://127.0.0.1:8000/api/v1`)
- MySQL host: `localhost:3307`
- Redis: solo red interna Docker (no se expone al host)

Comprueba `http://127.0.0.1:8000/api/v1/health/ready` antes de abrir el admin.
Si la base se inicializa por primera vez:

```bat
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap-mysql.ps1
```

Los puertos del stack Docker quedan limitados a `127.0.0.1`. Para un piloto
expuesto, configura el proxy/TLS y nunca publiques MySQL o Redis directamente.

### Secretos para piloto o producción

1. Copia `backend/.env.example` a `backend/.env`.
2. Genera valores distintos y pégalos en `backend/.env`:

```bat
powershell -ExecutionPolicy Bypass -File .\scripts\generate-secrets.ps1 -AppEnv pilot
```

`APP_ENV=pilot` o `production` rechaza secretos de ejemplo y
`DEV_SEED_PASSWORD=admin123` al arrancar. `development` solo es aceptable si
el stack permanece en localhost.

### Protección de leads públicos

`POST /api/v1/public/leads` permite por defecto 8 solicitudes por IP cada 60
segundos y devuelve `429` al excederlo. Redis es obligatorio por defecto:
si no responde, devuelve `503` para evitar dejar el formulario sin protección.
Define `TRUSTED_PROXY_IPS` únicamente con las IPs de proxies que puedan enviar
`X-Forwarded-For`.

Motores de noticias opcionales (mejor cobertura que solo DDG): en `backend/.env`
añade `TAVILY_API_KEY` y/o `SERPAPI_API_KEY` y/o `BING_SEARCH_API_KEY`.
El health reporta `dependencies.news_search`.

Imágenes sociales: requiere proveedor OpenAI activo con clave que descifre
(`key_ok: true` en Inteligencia Artificial). Si no, Hoy avisará y no fingirá
creatividades de calidad.

La migración del piloto desde PostgreSQL se hace únicamente después de crear
un dump con `backup-postgres.ps1`, mediante
`cd backend` y
`venv\Scripts\python.exe ..\scripts\migrate-postgres-to-mysql.py`.

### Puente PostgreSQL (solo recuperación)

**No es el camino diario.** Solo si MySQL no está disponible:

```bat
start-pilot.bat
```

o `docker compose -f docker-compose.offline.yml up -d` + `start-dev-offline.bat`.

En ese modo excepcional la API puede estar en `:8012` y el admin en `:3001`.
Los jobs pesados requieren los workers ingest y editorial.

## Agentes automáticos (prioridad + tablero)

En **AI Hub → Agentes** verás el tablero en vivo (prioridad, estado ACTIVO/IDLE/OK,
función actual). Orden del ciclo automático:

1. `scout` → 2. `classifier` → 3–5. `verifier`/`writer`/`reviewer` (si hay artículo) →
6. `trend_ad_advisor` → 7–9. agentes Juan (`juan_editorial`, `juan_ai_governance`,
`juan_ip_patents`).

- **Manual ahora:** botón **Correr ciclo automático** → `POST /api/v1/agents/auto/run`
- **Estado:** `GET /api/v1/agents/status` (también embebido en `GET /api/v1/agents`)
- **Beat:** cada hora al minuto 40 (`run_agent_priority_cycle` en cola `llm`).
  Tras cambiar el schedule: `docker restart autoridad360-celery-beat autoridad360-celery-editorial`.

## Agentes Juan J. Vásquez

Una sola persona/voz (`backend/app/services/juan_persona.py`) y tres agentes en
**AI Hub → Agentes**:

| Agente | Uso |
|--------|-----|
| `juan_editorial` | Paquete multi-formato con voz Juan (requiere `article_id`) |
| `juan_ai_governance` | Brief AI Readiness (Education / Technology / Governance) |
| `juan_ip_patents` | Brief PI/patentes (prosecution, FTO, inventorship, AI+IP) |

Pipeline `juan_practice`: corre los tres en serie sobre un `article_id` verificado
(editorial → AI governance → IP). En la UI: modo pipeline **juan_practice** +
`article_id` → **Correr pipeline**. También `POST /api/v1/agents/pipeline/run`
con `{"mode":"juan_practice","article_id":…}`.

Disclaimer fijo: thought leadership editorial; no constituye asesoría legal.

## Verificación

- `GET /api/v1/health` informa DB, Redis, Celery, Ollama y motores de noticias.
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
