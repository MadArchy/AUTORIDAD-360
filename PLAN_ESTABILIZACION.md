# Plan de estabilización — Autoridad 360

Basado en el veredicto técnico (abril–jul 2026). **No agregar más features** hasta cerrar Etapa 1.

## Veredicto (aceptado)

| Área | % | Lectura |
|------|---|---------|
| Concepto | 85 | Visión correcta |
| Cobertura funcional | 80 | Flujo editorial casi completo |
| Automatización IA | 70 | Ollama/agentes OK; endurecer |
| Organización código | 55 | App.jsx monolito; stacks paralelos |
| MySQL real | 30 | Hoy: Postgres/SQLite mezclados |
| Seguridad prod | 40 | Headers piloto, secretos compartidos |
| Piloto | 70 | Operable en local |
| Producción comercial | 40 | Bloqueada por infra/seguridad |

**Flujo validado:** Noticias → clasificar → score → seleccionar → generar → revisar → aprobar → calendario → métricas.

---

## Etapa 1 — Estabilización obligatoria (CASI CERRADA — bloqueo MySQL)

1. **Una sola BD: MySQL 8.4** — compose listo; **pull TLS falla** → puente Postgres
2. **Secretos** — separados en config + `.env.example`
3. **Auth** — JWT en UI; headers solo development/pilot
4. **Rutas seed** — `/orgs/seed`, `/profile/seed`, `/ops/cadence/seed` + lifespan gated en production
5. **Puertos** — `start-dev.bat` (8000/MySQL) · `start-dev-offline.bat` (8012/Postgres)

## Etapa 2 — Refactorización (EN CURSO)

- [x] Extraer todos los tabs de `App.jsx` → `frontend/src/tabs/*` (~1485 líneas shell)
- [x] `utils/normalizers.js`
- [x] Embeddings: no vector cero
- [x] React/Vite = admin (:3001); Next.js = blog público (`frontend-blog` :3002)
- [x] Tabla `ai_models` + `GET /ai/models` + seed desde catálogo
- [x] Celery: estados persistidos (`background_jobs`) + `Idempotency-Key` + `GET /jobs/{id}`

## Etapa 3 — Calidad y producción (EN CURSO · Postgres OK)

- [x] Smoke tests API (`backend/tests/test_etapa3_smoke.py`) contra BD actual — **9 passed**
- [x] Blog/admin: mutators JWT + roles staff; `GET /blog/published` y `GET /blog/{slug}` públicos
- [x] Jobs y content (pending/approve/reject/reuse/translate) requieren JWT + staff
- [x] Drafts de blog heredan `organization_id`; respuesta incluye resumen de verificación
- [ ] Suite completa contra MySQL real *(bloqueado pull Docker TLS)*
- [ ] Multiempresa completo (aislamiento articles/content/jobs por org) + backups/monitoreo
- [ ] Despliegue piloto

### Cómo desbloquear TLS (npm / Docker / nvm)

En esta máquina falla TLS de forma sistémica (`ERR_SSL_CIPHER_OPERATION_FAILED`, `tls: bad record MAC`):

1. Actualizar/reparar certificados raíz Windows y desactivar antivirus/proxy que inspeccione HTTPS
2. Probar otra red (hotspot móvil) o VPN
3. Reinstalar Node **20 LTS** cuando nvm pueda descargar: `nvm install 20.19.0`
4. Registry npm en HTTPS: `npm config set registry https://registry.npmjs.org/`
5. Docker: `docker pull mysql:8.4` cuando TLS esté sano

**Mientras tanto (piloto):**
- Blog: `start-blog-static.bat` → HTML en `:3002` (sin npm)
- Next.js en `frontend-blog/src` queda listo para `npm install` cuando TLS funcione
- BD: seguir con Postgres offline; MySQL cuando el pull funcione

---

## Criterios de salida Etapa 1

- [ ] `docker compose up` levanta MySQL + Redis + API *(bloqueado TLS)*
- [x] Un solo `DATABASE_URL` MySQL en docs/example (`.env.example`)
- [x] Tres secretos distintos en config
- [x] Producción no acepta `X-User-Email`
- [x] Seed org no es público (+ profile/cadence/lifespan gated)
- [x] `.gitignore` cubre `.env`, `venv`, `node_modules`, DBs locales
- [x] Login JWT en UI (`LoginScreen` + Bearer en `api.js`)
- [x] Alembic base (`backend/alembic`) listo para MySQL
- [x] Health muestra dialecto DB en header UI
- [x] `psycopg2-binary` en `requirements.txt` (puente offline)
- [x] `start-dev-offline.bat` documenta piloto Postgres/8012

### Bloqueo conocido (MySQL)

`docker pull mysql:8.4` / `mariadb:11` fallan con **TLS bad record MAC** en esta máquina.
Mientras tanto el piloto usa **Postgres** vía `docker-compose.offline.yml` (`5433`).
No cortar el piloto: reintentar pull MySQL cuando la red/Docker TLS se estabilice.

### Separación frontends (Etapa 2)

| App | Carpeta | Puerto | Rol |
|-----|---------|--------|-----|
| Admin | `frontend/` (Vite) | 3001 | Flujo editorial, JWT, agentes |
| Blog público | `frontend-blog/` (Next.js) | 3002 | Solo posts `published` |
| API | `backend/` | 8000 / 8012 | `GET /blog/published`, `GET /blog/{slug}` |

Arranque blog: `start-blog.bat` (API ya levantada).
