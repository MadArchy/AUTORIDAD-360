# Flujo editorial real (piloto)

## Cadena canónica

1. **Top 10** — noticias priorizadas (`/top10`)
2. **Contenido** — generar paquete multi-formato desde artículo
3. **Aprobación** — semáforo + approve piece / blog
4. **Canales** — `from-slot` o crear paquete → variantes + checklist
5. **Confirmar** — job `confirm` (asistido) o `execute` (nativo dry-run/live)
6. **Refresh** — sugerir piezas viejas → aprobar → **iniciar revisión** → editar/aprobar nueva versión → completar

## Refresh sin ambigüedad

| Estado | Significado | Acción UI |
|--------|-------------|-----------|
| `suggested` | Candidato | Aprobar / Descartar |
| `approved` | Listo para trabajar | **Iniciar revisión** (crea pieza `draft` v+1) |
| `in_progress` | Hay `new_piece_id` | Editar en Contenido → aprobar → **Marcar hecho** |
| `done` | Cerrado | — |
| `dismissed` | Rechazado | — |

API:

- `POST /saas/refresh/suggest`
- `POST /saas/refresh/{id}/decide` `{accept, actor}`
- `POST /saas/refresh/{id}/start` → crea draft y pasa a `in_progress`
- `POST /saas/refresh/{id}/complete` `{new_piece_id?}`

## UTM → lead → servicio

1. Crear enlace en **Marketing** (utm_campaign + service_offer)
2. Usar `tracked_url` en CTA del canal
3. Captura pública: `POST /api/v1/public/leads` con los mismos UTM
4. Ver pipeline en **Resultados**

## Guardrails

- No publicar 6 redes sin assets/aprobación
- Claims legales: `supported` exige ≥1 evidencia
- Nativo LinkedIn: ver `docs/LINKEDIN_LIVE.md`
