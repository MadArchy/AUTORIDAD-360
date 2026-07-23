# Roadmap Combinado — Plataforma de Inteligencia Editorial y Posicionamiento Profesional

Caso piloto: Juan Vásquez
Herramientas de construcción: Cursor + Antigravity
Principio rector: automatización máxima, alucinación cero, aprobación humana en todo lo sensible.

---

## 0. Cómo se combina todo

No se construye el proyecto grande de un solo golpe. Se construye **en el orden en que cada pieza necesita a la anterior**, pero sin dejar ningún módulo fuera del mapa. El MVP de noticias (agentes → top 10 → blog → reporte) no es un proyecto aparte: es la **Fase 1** de este roadmap, y todo lo demás se conecta sobre esa base.

```
Fase 1 → Núcleo de noticias reales + reporte + blog        (base de datos, agentes, verificación)
Fase 2 → Perfiles profesionales + porcentajes editoriales   (usa la Fase 1)
Fase 3 → Generación de contenido multi-formato              (usa la Fase 1 y 2)
Fase 4 → Calendario, tareas y aprobaciones                  (usa la Fase 3)
Fase 5 → Gateway de modelos (local + API keys pagas)        (mejora todas las fases anteriores)
Fase 6 → Multiempresa / multicliente                        (generaliza todo lo anterior)
Fase 7 → Métricas, leads y ajuste automático de porcentajes (cierra el ciclo de aprendizaje)
```

Cada fase entrega algo funcional y verificable. No se avanza a la siguiente sin haber probado la anterior con datos reales de Juan.

---

## 1. Principios que aplican a TODAS las fases (no negociables)

1. **El modelo nunca genera contenido desde su memoria.** Solo trabaja sobre texto ya guardado en la base de datos, con `source_url` verificable.
2. **Todo output de IA es JSON estructurado con `article_id` o `source_id` trazable.** Si falta, el backend lo rechaza por regla de código, no por confianza en el modelo.
3. **Un segundo paso verifica cada afirmación contra el texto original** antes de marcarla como publicable.
4. **Nada se publica automáticamente.** Toda pieza pasa por aprobación humana visible (noticia original al lado del contenido generado).
5. **Las decisiones importantes (Top 10, distribución por porcentajes) las calcula código determinístico**, no un prompt de "elige lo mejor". El modelo aporta puntajes; el backend calcula el resultado.
6. **Registro de auditoría en cada paso**: qué modelo se usó, qué fuente, qué prompt, quién aprobó.

---

## 2. Roles de Cursor y Antigravity

| Situación | Herramienta | Por qué |
|---|---|---|
| Crear un módulo nuevo desde cero (scaffolding, tablas, endpoints) | **Antigravity** | Maneja bien tareas grandes de "aquí está la tarea completa", trabaja con varios agentes en paralelo (frontend/backend/tests a la vez), y tiene navegador integrado para verificar visualmente el blog y los dashboards. |
| Lógica sensible: verificación anti-alucinación, cálculo de porcentajes, cifrado de API keys, reglas de aprobación | **Cursor** | Ediciones quirúrgicas, más control línea por línea en la parte donde un error tiene consecuencias (dinero, datos, contenido legal). |
| Refinar/depurar lo que Antigravity generó | **Cursor** | Antigravity construye rápido y amplio; Cursor ajusta con precisión. |
| Pruebas end-to-end con navegador (flujo de aprobación, blog) | **Antigravity** | Su función de navegador embebido sirve para verificación visual automática. |

Patrón de trabajo por módulo: **Antigravity construye el esqueleto → Cursor revisa y ajusta la parte crítica → Antigravity corre las pruebas visuales.**

---

## 3. Fase 1 — Núcleo de noticias reales, Top 10 y blog (3–4 semanas)

*(Este es el plan que ya definimos; aquí queda como la base de todo lo demás)*

**Semana 1 — Recolección (Antigravity)**
- FastAPI + MySQL 8.4.
- Conectores RSS reales para las 11 categorías del documento de noticias.
- Tabla `news_articles`: título, URL, fuente, fecha, texto completo, hash de duplicado.
- Job Celery que recolecta sin tocar IA todavía.

**Semana 2 — Clasificación y verificación (Cursor)**
- Prompt de clasificación sobre texto ya guardado (JSON estricto + `article_id`).
- Agente verificador que compara el resumen contra el texto fuente.
- Conexión inicial a Ollama local.

**Semana 3 — Top 10 y reporte (Antigravity)**
- Fórmula de puntuación determinística (los pesos que ya definimos: relevancia 25%, impacto 20%, confiabilidad 15%, vigencia 15%, potencial de contenido 10%, relevancia MX-US 10%, conversión 5%).
- Generador de reporte semanal con link a cada fuente.

**Semana 4 — Blog (Antigravity + Cursor)**
- Next.js con panel de aprobación previo a publicación.
- Cada nota muestra cita y link a la fuente original.

✅ **Criterio de cierre de fase**: una semana completa de operación real con las fuentes de Juan, sin ninguna afirmación no verificable en el reporte final.

---

## 4. Fase 2 — Perfil estratégico y porcentajes editoriales (2 semanas)

**Herramienta principal: Antigravity** (nuevas tablas y pantallas), **Cursor** para las reglas de cuota.

- Tablas `professional_profiles`, `content_pillars`, `editorial_percentages`, `market_percentages` (ya definidas en el modelo de datos).
- Pantalla de configuración del perfil de Juan: servicios, públicos, pilares, porcentajes por pilar y por mercado (MX/US).
- Lógica de "corrección de cuota" (si un pilar va por debajo de su meta mensual, sube su prioridad en el cálculo del Top 10 de la Fase 1).

✅ **Cierre**: el Top 10 de noticias ahora se ajusta automáticamente según qué tan cerca está cada pilar de su meta.

---

## 5. Fase 3 — Generación de contenido multi-formato (3 semanas)

**Herramienta: Antigravity** para los formatos nuevos, **Cursor** para el revisor de marca y el control factual.

- A partir de una noticia del Top 10 ya verificada, generar: publicación de LinkedIn, guion de video, carrusel, newsletter.
- Agente "reutilizador": una pieza aprobada se convierte en 3–5 derivados automáticamente.
- Agente revisor de marca (tono, voz, coherencia con publicaciones anteriores de Juan) y revisor factual (mismo mecanismo de verificación de la Fase 1, aplicado ahora al contenido generado, no solo al resumen).
- Traducción ES/EN para los dos mercados.

✅ **Cierre**: de una noticia aprobada sale un paquete completo de contenido en varios formatos, cada pieza con su fuente trazable.

---

## 6. Fase 4 — Calendario, tareas y aprobaciones (3 semanas)

**Herramienta: Antigravity** (módulo operativo nuevo)

- Calendario editorial con la cadencia real de Juan (3 LinkedIn/semana, 2 videos/mes, etc.)
- Tareas: asignación, adjuntar guion, notificar, recibir video grabado, marcar completado, enviar a edición.
- Semáforo de riesgo (verde/amarillo/rojo) definido en el documento maestro, aplicado aquí como estado de aprobación.
- Historial de versiones y decisiones (quién aprobó, cuándo, por qué se rechazó algo).

✅ **Cierre**: el flujo completo "tendencia → contenido → tarea → aprobación → publicación" corre sin salir de la plataforma.

---

## 7. Fase 5 — Gateway de modelos: local + API keys pagas (2–3 semanas)

**Herramienta: Cursor** (seguridad y enrutamiento son de alto riesgo si se hacen mal)

- LiteLLM como gateway desde el día uno.
- Conectores: Ollama (ya en uso desde Fase 1), y ahora OpenAI, Anthropic, Gemini vía API key.
- Pantalla "Configuración → Proveedores de IA": alta de proveedor, prueba de conexión, presupuesto mensual, límite diario.
- Cifrado de API keys en MySQL (nunca texto plano, nunca visibles completas después de guardadas).
- Enrutador: tareas simples → local; tareas complejas o sensibles → modelo comercial, con exigencia de aprobación humana igual.

✅ **Cierre**: puedes pegar una API key de Anthropic u OpenAI desde la interfaz, probarla, y ver en el dashboard qué porcentaje de tareas se resuelve local vs. pago.

---

## 8. Fase 6 — Multiempresa / multicliente (3 semanas)

**Herramienta: Antigravity** (generalización de lo ya construido)

- `organization_id` en todas las tablas operativas (aislamiento lógico, ya contemplado en el modelo de datos).
- Roles: superadmin, admin de agencia, estratega, redactor, profesional/cliente, editor, revisor legal, community manager, analista.
- Cada agencia ve solo sus clientes; cada cliente ve solo su información.
- Onboarding de un segundo y tercer profesional (piloto: dos abogados adicionales + un consultor de IA, como ya se definió).

✅ **Cierre**: el sistema maneja a Juan y a 2–3 clientes más sin mezclar datos ni calendarios.

---

## 9. Fase 7 — Métricas, leads y aprendizaje (2–3 semanas)

**Herramienta: Antigravity** para dashboards, **Cursor** para el motor de ajuste automático.

- Indicadores operativos, editoriales y comerciales (los ya definidos: tiempo de aprobación, interacciones por pilar, consultas generadas, etc.)
- Captura de leads y conversión (embudo comercial del plan de Juan).
- Ajuste automático de porcentajes según qué pilares generan más contactos calificados, no solo más "me gusta".

✅ **Cierre**: el sistema recomienda solo cambios de porcentaje respaldados por datos de las fases anteriores.

---

## 10. Cronograma total estimado

| Fase | Duración | Acumulado |
|---|---|---|
| 1. Noticias reales + Top 10 + blog | 3–4 semanas | 4 semanas |
| 2. Perfil y porcentajes | 2 semanas | 6 semanas |
| 3. Generación multi-formato | 3 semanas | 9 semanas |
| 4. Calendario y aprobaciones | 3 semanas | 12 semanas |
| 5. Gateway multi-modelo + API keys | 2–3 semanas | 15 semanas |
| 6. Multiempresa | 3 semanas | 18 semanas |
| 7. Métricas y aprendizaje | 2–3 semanas | 21 semanas |

**Total: ~20–21 semanas (5 meses) para el sistema completo**, con la ventaja de que desde la semana 4 ya hay algo publicándose de verdad con Juan, no un prototipo cerrado.

---

## 11. Regla de avance

No se pasa a la fase siguiente si la anterior no ha corrido **al menos una semana con datos reales de Juan sin intervención manual de emergencia**. Si una fase falla esa prueba, se corrige antes de seguir — no se acumulan módulos sobre una base que no probó ser confiable.
