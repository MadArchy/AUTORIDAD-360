"""Prompts para la generación de contenido."""

GENERATION_PROMPT = """{persona_block}

Trabajas SOLO con el TEXTO FUENTE y el RESUMEN. NO inventes datos, cifras, leyes ni citas que no estén en la fuente.
Máximo 2 emojis. Cero hype.

Devuelve JSON estricto (sin markdown fuera del JSON):
{{
  "article_id": {article_id},
  "source_url": "{source_url}",
  "format_type": "{format_type}",
  "language": "{language}",
  "title": "<título ejecutivo, no clickbait>",
  "body_text": "<contenido listo para publicar; cita la fuente al final>",
  "body_json": <objeto del formato o null>,
  "key_claims": ["<tesis 1>", "<implicación 2>", "<riesgo o acción 3>"]
}}

Reglas por formato:

- linkedin (CRÍTICO — no es un resumen de prensa):
  Objetivo: opinión ejecutiva útil para GC/CLO/CISO/directivos. NO parafrasear la noticia.
  Prohibido:
  * Copiar o reescribir casi literales párrafos de la fuente.
  * Dedicar más de 2 frases cortas a "qué pasó".
  * Empezar con "La adquisición…", "El artículo…", "Según la noticia…" y quedarte ahí.
  Estructura OBLIGATORIA (180–260 palabras):
  1) GANCHO (1–2 líneas): tensión o decisión que enfrenta un líder (no el titular reformulado).
  2) HECHO ANCLA (máx. 2 frases): solo lo indispensable de la fuente, con dato concreto si existe.
  3) "Mi perspectiva:" (mínimo 4–6 frases) con AL MENOS tres de estos:
     - riesgo legal/regulatorio o de gobierno corporativo
     - impacto operativo (procesos, vendors, datos, control interno)
     - lo que la fuente NO responde y qué pregunta harías tú
     - acción concreta esta semana para un comité / legal / compliance
  4) CTA o pregunta ejecutiva (1 frase).
  5) Cierre: Fuente: {source_url}
  key_claims debe listar la tesis y las implicaciones (no frases calcadas de la fuente).

- video_script: Guion 60–90s. Formato: [0:00 - GANCHO], [0:15 - HECHO], [0:40 - ANÁLISIS], [1:15 - CIERRE & CTA]. El análisis debe superar al resumen.

- carousel: EXACTAMENTE 5 slides progresivos (PROHIBIDO repetir el mismo párrafo). body_json:
  {{"format":"carousel","slides":[
    {{"slide":1,"title":"<gancho>","text":"<tensión ejecutiva, no titular>"}},
    {{"slide":2,"title":"<hecho>","text":"<dato concreto de la fuente>"}},
    {{"slide":3,"title":"<riesgo>","text":"<implicación legal/operativa>"}},
    {{"slide":4,"title":"<mi perspectiva>","text":"<postura accionable>"}},
    {{"slide":5,"title":"<acción>","text":"<CTA + fuente>"}}
  ]}}
  body_text = resumen lineal de los 5 slides.

- newsletter: Asunto + saludo + reflexión estratégica (no resumen) + takeaways accionables.
  body_json = {{"subject": "...", "takeaways": ["...", "...", "..."]}}

Idioma de salida (OBLIGATORIO): {language_instruction}

ÁNGULO NARRATIVO ÚNICO PARA ESTA PIEZA:
{narrative_angle}

RESUMEN VERIFICADO:
{summary}

KEY FACTS:
{key_facts}

TEXTO FUENTE (recortado — úsalo como evidencia, no como borrador a reescribir):
\"\"\"
{full_text}
\"\"\"
"""

NARRATIVE_ANGLES = (
    "Enfócate en riesgo de cumplimiento y responsabilidad de directivos.",
    "Enfócate en oportunidad competitiva y timing de mercado MX-US.",
    "Enfócate en lo que la noticia NO dice y qué debiera preguntar un GC/CLO.",
    "Enfócate en impacto operativo: procesos, vendors y control interno.",
    "Enfócate en lectura regulatoria práctica (qué cambia mañana en la mesa de decisión).",
)

LINKEDIN_REWRITE_PROMPT = """{persona_block}

El borrador de LinkedIn es demasiado cercano a la noticia (parafraseo).
Reescríbelo con análisis propio. Devuelve SOLO JSON estricto con:
article_id={article_id}, source_url="{source_url}", format_type="linkedin", language="{language}",
title, body_text, body_json=null, key_claims (3 ítems).

Reglas duras:
- Máximo 2 frases de hechos de la fuente.
- Bloque "Mi perspectiva:" con riesgo + impacto operativo + pregunta sin responder + acción concreta.
- No copies frases de la fuente. Idioma: {language_instruction}.
- Ángulo: {angle}
- Tema: {title}
- Cierra con Fuente: {source_url}

BORRADOR DÉBIL:
{raw_draft}

HECHOS ÚTILES (no parafrasear el artículo completo):
{key_facts}
"""


def get_rewrite_prompt(
    format_type: str,
    critique: str,
    suggestions: list[str],
    angle: str,
    title: str,
    article_id: int,
    source_url: str,
    raw_draft: str,
) -> str:
    return f"""
    El siguiente borrador de {format_type} necesita mayor profundidad argumentativa.
    Feedback del crítico: {critique}
    Sugerencias: {', '.join(suggestions)}
    Ángulo narrativo obligatorio: {angle}
    Tema obligatorio: {title}

    Reescribe el borrador. Devuelve SOLO JSON estricto con article_id={article_id},
    source_url="{source_url}", format_type="{format_type}".
    No parafrasees la noticia: aporta tesis, riesgo e implicación ejecutiva.

    BORRADOR ACTUAL:
    {raw_draft}
    """
