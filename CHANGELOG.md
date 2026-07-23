# Changelog

## 0.9.0 — 2026-07-23

### Editorial / UX
- Generación **por formato** (LinkedIn, video, etc. bajo demanda)
- Selector **IA local vs API cloud** al generar
- Ollama más rápido (`think: false`), cola Celery `llm` corregida
- Prompt LinkedIn con más argumentación y anti-parafraseo
- Menú: IA unificada (modelos + agentes); SEO/Legal oculto; Hoy en 2 pasos

### Agentes
- Orquestación migrada a **LangGraph** (`StateGraph`) manteniendo gateway Ollama
- Pipeline `article` con rama de reintento de writer si la crítica LLM marca `ok: false`
- Tools editoriales como **`langchain_core` StructuredTool** (esquema Pydantic + `invoke`)
- **ChromaDB** activo para deduplicación/indexación vectorial del Scout (embeddings Ollama `nomic-embed-text`)
- API `/api/v1/agents` sin cambio de contrato; `pipelines.engine = langgraph`
- Health expone `dependencies.chroma`

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
