# Plan por fases — Autoridad 360

Documento de referencia. Entregar/repasar al usuario al culminar cada fase.

Actualizado: 2026-07-21

## Principio

Estabilizar (Fase 0) antes de ampliar automatización visible. Marca pública: Juan Vásquez. Autoridad 360 = fábrica operativa.

## Visión

Sistema que responde: qué ocurre / qué buscan → qué producir → fuentes y riesgo → quién aprueba → dónde publicar (blog + redes) → qué convirtió → qué actualizar.

## Canales objetivo (post Fase 0)

Blog, LinkedIn, Facebook, Instagram, TikTok, YouTube, X, newsletter.

Cada pieza aprobada → paquete multi-canal (artículo, carrusel, reel/short, post+imagen, newsletter, video script) + media assets + publish_jobs.

Orden redes: LinkedIn → Instagram/Facebook → YouTube → TikTok (asistido primero si API limita).

---

## Fase 0 — progreso

Inicio de implementación (2026-07-21):

- [x] Plan guardado en este archivo (recordar al culminar fases)
- [x] Sanitización HTML editorial
- [x] Protección SSRF allowlist en base_url de proveedores
- [x] Gate de presupuesto/límite diario AI (salta proveedor y prueba local)
- [x] Metrics/dashboard y brand review filtrados por organization_id
- [x] UNIQUE blog (organization_id, slug) + migración 0005
- [x] Eliminados servicios legacy y `app/core/config.py`
- [x] Login piloto solo en DEV (incluye org slug)
- [x] Rotación real de secretos documentada (`scripts/generate-secrets.ps1` + `DEPLOY.md`)
- [ ] Alembic baseline explícito tabla-a-tabla (deuda; create_all + revisiones incrementales siguen vigentes; piloto usa `start-pilot.bat` → alembic)
- [x] Sesiones HttpOnly refresh (`a360_refresh`) + access token corto en sessionStorage

## Fase 1 — Publicación multi-canal

- [x] Modelos + migración `20260721_0006` (auth_sessions, channel_accounts, media_assets, packages/variants/jobs)
- [x] Servicio asistido (blog/linkedin/facebook/instagram/tiktok/youtube/x/newsletter)
- [x] API `/api/v1/publish/*` + tab admin **Canales**
- [x] Calendario unificado (`GET /publish/schedule`) + `from-slot` + programar jobs (`calendar_slot_id`, migración `0007`)
- [x] Adjuntar media assets al crear paquete (UI + API)
- [x] Adaptadores nativos: LinkedIn (dry-run/live), Meta/IG/YouTube/TikTok (dry-run stub); connect cifrado + `POST /publish/jobs/{id}/execute`
- [ ] Live Graph Meta / YouTube upload / TikTok posting (tras OAuth de producción)

Criterio MVP asistido: pieza/blog → paquete → variantes + checklist → confirmar job publicado.
Nativo: cuenta `connected` + execute (por defecto dry-run; `PUBLISH_NATIVE_LIVE=true` para LinkedIn real).

## Fase 2 — SEO técnico sitio público

- [x] Marca pública Juan Vásquez en blog estático (`:3002`)
- [x] `robots.txt` + `sitemap.xml` dinámico (`server.py`)
- [x] Canonical, OG, Twitter, JSON-LD (WebSite + Article) en index/post
- [x] Quitados enlaces/textos de admin/API del HTML público
- [x] Autor / revisor / categorías / seo_description en BlogPost + API (`0008`, `PATCH /blog/{id}/seo`)
- [ ] Search Console / dominio de producción *(ops — ver DEPLOY.md)*
- [ ] Migrar serving a Next con `generateMetadata` cuando npm/TLS permita *(bloqueado TLS)*
- [x] Branding white-label en blog público por hostname (`/public/branding`)
- [x] Captura UTM → lead desde blog (`/public/leads`)

## Fase 3 — Inteligencia SEO + Legal Authority Content Engine

- [x] Modelos + migración `20260721_0009` (clusters, briefs, prompts, claims, evidences)
- [x] Schemas Pydantic (jurisdicción, intents, claim status)
- [x] API `/api/v1/seo-legal/*` (clusters, briefs, prompts, claims, evidences)
- [x] Regla: claim `supported` exige ≥1 evidencia (no overlap léxico)
- [x] Extracción de claims desde piezas (`POST /seo-legal/claims/from-piece/{id}` vía `content_review`)
- [x] UI admin **SEO / Legal** (clusters, briefs, claims, evidencias)
- [x] Prompts versionados ligados a generación (`resolve_generation_prompt` → `_llm_draft`)

## Fase 4 — Marketing y atribución

- [x] Modelos + migración `20260721_0010` (service_offers, campaign_links, newsletter_subscribers; UTM/CTA en leads/variants/engagements)
- [x] API `/api/v1/marketing/*` (ofertas, UTM preview/links, newsletter list, CTA variant)
- [x] Leads/engagements extendidos (UTM, job/variant/service, channel insights)
- [x] UI admin **Marketing** + CTA en Canales + UTM en formulario de leads
- [ ] Insights nativos redes (Graph/LinkedIn API) *(tras OAuth prod)*
- [ ] Envío newsletter / ESP *(fuera de MVP)*
- [ ] Sync CRM externo *(opcional)*

## Fase 5 — Aprendizaje y SaaS

- [x] Porcentajes con aprobación humana (ya en metrics: generate → decide → apply)
- [x] BYOK gateway existente + gate por plan (`byok_allowed`)
- [x] Modelos + migración `20260721_0011` (plan_code/branding, custom_domains, content_refresh_items)
- [x] API `/api/v1/saas/*` (planes, branding, dominios, refresh suggest/decide/complete)
- [x] UI **Organización** (plan + white-label) + tab **Refresh**
- [x] Límite de asientos al añadir miembros
- [x] Refresh: `start` crea draft v+1 (flujo documentado)
- [x] Branding por hostname en blog público
- [ ] Billing / Stripe *(fuera de MVP)*
- [ ] Verificación DNS automática de dominios *(ops)*
- [x] Aplicar branding al blog público por hostname

## Mejoras transversales (post Fase 5)

- [x] Arranque único `start-pilot.bat` + scripts backup/restore/health/secrets
- [x] CI GitHub Actions + VERSION/CHANGELOG
- [x] Docs flujo editorial + LinkedIn live
- [x] Atribución marketing (`/marketing/attribution`)
- [x] Evidencia candidata al extraer claims + seed prompts por canal
- [ ] Stripe / ESP / CRM *(cuando haya uso real)*
- [ ] Git remoto + release tags *(cuando el equipo publique)*

## Qué no hacer antes de cerrar Fase 0

- Botón “Generar SEO” masivo
- Publicar en 6 redes sin assets/aprobación
- Confiar solo en overlap léxico como “verificado jurídico”
- APIs Meta/TikTok/YouTube sin publish_jobs + permisos por org

## Al culminar fases

Recordar al usuario este documento y el plan detallado de redes (formatos, ratios, modo asistido vs API).
