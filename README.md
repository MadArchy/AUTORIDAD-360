# Autoridad 360 — Fases 1–7 (ciclo completo)

Plataforma de inteligencia editorial para posicionamiento profesional.  
**Piloto:** Juan Vásquez

## Fases

1. Noticias reales → verificación → Top 10 → blog  
2. Perfil + corrección de cuota  
3. Contenido multi-formato  
4. Calendario, tareas, semáforo  
5. Gateway multi-modelo + keys cifradas  
6. Multiempresa / roles  
7. **Métricas, leads y ajuste de porcentajes por leads calificados**

## Arranque

```bash
docker compose up -d --build
cd frontend && npm install && npm run dev
```

Métricas: http://localhost:3000/metricas · Docs: http://localhost:8000/docs

### Fase 7 — flujo

```bash
# Dashboard
curl http://localhost:8000/api/v1/metrics/dashboard

# Registrar lead calificado ligado a un pilar
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{"contact_name":"Prospecto Demo","pillar_id":1,"status":"qualified","is_qualified":true}'

# Generar recomendación (requiere >= 3 leads calificados)
curl -X POST http://localhost:8000/api/v1/recommendations/percentages/generate

# Aceptar / rechazar
curl -X POST http://localhost:8000/api/v1/recommendations/percentages/1/decide \
  -H "Content-Type: application/json" \
  -d '{"actor":"Juan Vasquez","accept":true}'
```

Migración:

```bash
docker exec -i autoridad360-mysql mysql -uautoridad -pautoridadpass autoridad360 < backend/db/migrate_fase7.sql
```

## Regla de aprendizaje

Los **likes no mueven porcentajes**. Solo leads `qualified` / `converted` generan recomendaciones, y un humano debe aceptarlas.

## Roadmap

Ciclo del documento maestro cubierto (Fases 1–7). Siguientes mejoras naturales: JWT real, LiteLLM en prod, y semana de operación con datos reales de Juan.
