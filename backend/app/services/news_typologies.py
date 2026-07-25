"""Tipologías editoriales — Tipos_de_Noticias_IA_Juan_Vasquez.pdf

Prioridad 1–11. Cada tipología define qué monitorear, por qué sirve y queries.
Filtro de calidad: la noticia debe permitir responder qué ocurrió, por qué importa,
qué riesgo/oportunidad genera y qué debería revisar una empresa.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

NEWS_TYPOLOGIES: list[dict[str, Any]] = [
    {
        "id": 1,
        "slug": "politica-regulacion-ia",
        "pillar_slug": "corporativo-compliance",
        "name": "Política y regulación de IA",
        "monitor": (
            "Leyes, proyectos legislativos, políticas públicas, órdenes ejecutivas "
            "y decisiones gubernamentales de México y Estados Unidos."
        ),
        "why": "Explicar qué cambia para las empresas y qué deben preparar antes de que una obligación sea exigible.",
        "editorial_angle": "¿Qué debe revisar una empresa mexicana o estadounidense ante una nueva norma de IA?",
        "queries": [
            "regulación inteligencia artificial México 2026",
            "ley inteligencia artificial México Congreso",
            "US AI regulation executive order compliance 2026",
            "EU AI Act enforcement companies United States Mexico",
        ],
    },
    {
        "id": 2,
        "slug": "ia-mal-implementada",
        "pillar_slug": "legal-tech-ia",
        "name": "Empresas que implementaron mal la IA",
        "monitor": (
            "Pilotos cancelados, chatbots con errores, sobrecostos, baja adopción interna, "
            "fallas de supervisión o resultados que no justificaron la inversión."
        ),
        "why": "Transformar errores reales en lecciones sobre gobernanza, pruebas, control y revisión humana.",
        "editorial_angle": "Cinco fallas de gobernanza que llevaron a cancelar un proyecto de IA.",
        "queries": [
            "AI project cancelled enterprise failure",
            "chatbot failure company lawsuit OR recall",
            "piloto inteligencia artificial cancelado empresa",
            "AI pilot failed ROI governance",
        ],
    },
    {
        "id": 3,
        "slug": "casos-legales-ia",
        "pillar_slug": "corporativo-compliance",
        "name": "Casos legales por uso de IA",
        "monitor": (
            "Demandas, sanciones, investigaciones regulatorias, decisiones judiciales "
            "y conflictos por respuestas o decisiones automatizadas."
        ),
        "why": "Demostrar que la responsabilidad sigue siendo de la empresa aunque intervenga una herramienta de IA.",
        "editorial_angle": "La IA respondió mal: ¿quién asume la responsabilidad?",
        "queries": [
            "AI liability lawsuit company",
            "FTC AI investigation enforcement",
            "demanda inteligencia artificial responsabilidad empresa",
            "AI discrimination lawsuit employment OR lending",
        ],
    },
    {
        "id": 4,
        "slug": "ia-exito-empresarial",
        "pillar_slug": "legal-tech-ia",
        "name": "Empresas que implementaron IA con éxito",
        "monitor": (
            "Casos con mejoras verificables en productividad, servicio, costos, "
            "innovación, análisis o automatización."
        ),
        "why": "Mostrar prácticas que sí funcionan: objetivo claro, datos adecuados, controles y adopción del equipo.",
        "editorial_angle": "Qué hizo correctamente una empresa para escalar su solución de IA.",
        "queries": [
            "enterprise AI success case study productivity",
            "company scales AI governance controls adoption",
            "caso éxito inteligencia artificial empresa productividad",
        ],
    },
    {
        "id": 5,
        "slug": "empresas-rezagadas-ia",
        "pillar_slug": "legal-tech-ia",
        "name": "Empresas rezagadas en adopción",
        "monitor": (
            "Sectores o compañías que perdieron competitividad, productividad o capacidad "
            "de respuesta por reaccionar tarde a la transformación tecnológica."
        ),
        "why": "Crear contenido sobre el costo de esperar, sin afirmar que la IA fue la única causa del fracaso.",
        "editorial_angle": "El costo empresarial de retrasar la adopción de IA.",
        "queries": [
            "cost of delaying AI adoption enterprise",
            "laggard companies AI competitiveness",
            "retraso adopción inteligencia artificial empresas",
        ],
    },
    {
        "id": 6,
        "slug": "patentes-pi-ia",
        "pillar_slug": "propiedad-intelectual",
        "name": "Innovación, patentes y Propiedad Intelectual",
        "monitor": (
            "Patentes de IA, inventorship, derechos de autor, secretos empresariales, "
            "licencias, titularidad de resultados y nuevas invenciones."
        ),
        "why": "Conectar la experiencia de Juan en IA, PI y patentes con decisiones empresariales de innovación.",
        "editorial_angle": "¿Quién es el inventor cuando una empresa utiliza IA?",
        "queries": [
            "AI patent inventorship USPTO",
            "copyright AI generated work lawsuit",
            "patente inteligencia artificial inventor México",
            "trade secret AI training data dispute",
        ],
    },
    {
        "id": 7,
        "slug": "inversiones-ia",
        "pillar_slug": "emprendimiento",
        "name": "Inversiones empresariales en IA",
        "monitor": (
            "Nuevos centros de datos, adquisiciones, alianzas, fondos, expansión de startups, "
            "capacitación y presupuestos corporativos."
        ),
        "why": "Analizar oportunidades, riesgos de dependencia, talento, infraestructura y necesidad de gobernanza.",
        "editorial_angle": "Qué significa una gran inversión en IA para el mercado y sus empresas.",
        "queries": [
            "corporate AI investment data center acquisition",
            "inversión inteligencia artificial empresas México",
            "AI startup funding governance enterprise",
        ],
    },
    {
        "id": 8,
        "slug": "privacidad-ciberseguridad-ia",
        "pillar_slug": "corporativo-compliance",
        "name": "Privacidad y ciberseguridad",
        "monitor": (
            "Filtraciones, exposición de información confidencial, entrenamiento con datos corporativos, "
            "ataques, incidentes y riesgos de proveedores."
        ),
        "why": "Generar listas prácticas de controles, revisión contractual y protección de información.",
        "editorial_angle": "Cinco controles antes de entregar datos empresariales a una herramienta de IA.",
        "queries": [
            "data breach AI training data company",
            "vendor AI privacy risk enterprise",
            "filtración datos entrenamiento inteligencia artificial",
            "LFPDPPP inteligencia artificial empresas México",
        ],
    },
    {
        "id": 9,
        "slug": "empleo-transformacion-ia",
        "pillar_slug": "legal-tech-ia",
        "name": "Empleo y transformación laboral",
        "monitor": (
            "Automatización de tareas, reestructuraciones, nuevos cargos, capacitación, "
            "selección algorítmica y decisiones de recursos humanos."
        ),
        "why": "Explicar cómo adoptar IA sin improvisar cambios laborales ni crear riesgos de discriminación.",
        "editorial_angle": "Qué debe preparar Recursos Humanos antes de implementar IA.",
        "queries": [
            "AI workforce restructuring HR algorithmic hiring",
            "selección algorítmica discriminación IA empleo",
            "automatización puestos trabajo inteligencia artificial empresa",
        ],
    },
    {
        "id": 10,
        "slug": "ia-abogados-legal",
        "pillar_slug": "legal-tech-ia",
        "name": "IA para abogados y equipos jurídicos",
        "monitor": (
            "Herramientas legales, confidencialidad, privilegio, revisión humana, ética profesional, "
            "errores de citación y productividad jurídica."
        ),
        "why": "Posicionar a Juan frente a firmas, departamentos legales y líderes de cumplimiento.",
        "editorial_angle": "Qué debe revisar un equipo jurídico antes de utilizar una herramienta de IA.",
        "queries": [
            "legal tech AI hallucination citation lawyer",
            "abogados inteligencia artificial privilegio confidencialidad",
            "AI legal research malpractice risk",
            "law firm generative AI policy ethics",
        ],
    },
    {
        "id": 11,
        "slug": "mexico-estados-unidos-ia",
        "pillar_slug": "comercio-mx-us",
        "name": "Relación México–Estados Unidos",
        "monitor": (
            "Operaciones binacionales, transferencia de datos, contratos, proveedores, "
            "nearshoring tecnológico, PI y diferencias regulatorias."
        ),
        "why": "Diferenciar la marca con análisis comparativos para empresas que operan en ambos mercados.",
        "editorial_angle": "Cómo gobernar una herramienta de IA utilizada en México y Estados Unidos.",
        "queries": [
            "cross-border data transfer AI Mexico United States",
            "nearshoring inteligencia artificial gobernanza México",
            "US Mexico AI regulation comparison companies",
            "transferencia datos personales IA México Estados Unidos",
        ],
    },
]

# Queries planas priorizadas (P1 → P11)
SEARCH_QUERIES: list[str] = []
for typo in NEWS_TYPOLOGIES:
    SEARCH_QUERIES.extend(typo["queries"])

# Ruido editorial a rechazar aunque mencione "IA"
REJECT_TOPICS = (
    "incoterms",
    "shipping basics",
    "shipping documentation",
    "valoración startup",
    "valuation billion",
    "product launch hype",
    "crypto price",
    "celebrity",
    "deportes",
    "entretenimiento",
)

TYPOLOGY_EVAL_PROMPT = """Eres el curador editorial de Juan Vásquez (IA, gobernanza, PI, empresas, eje México–EE.UU.).

Clasifica la noticia en UNA tipología (1–11) o descártala.

TIPOLOGÍAS (prioridad alta → baja):
1 politica-regulacion-ia — leyes/políticas/órdenes ejecutivas MX o US sobre IA
2 ia-mal-implementada — pilotos cancelados, fallos, sobrecostos, mala gobernanza
3 casos-legales-ia — demandas, sanciones, investigaciones, fallos por uso de IA
4 ia-exito-empresarial — casos con resultados verificables de IA en empresa
5 empresas-rezagadas-ia — costo de llegar tarde a la adopción
6 patentes-pi-ia — patentes, inventorship, copyright, secretos, licencias de IA
7 inversiones-ia — data centers, M&A, fondos, presupuestos corporativos en IA
8 privacidad-ciberseguridad-ia — filtraciones, datos en entrenamiento, riesgo proveedor
9 empleo-transformacion-ia — automatización laboral, RH, selección algorítmica
10 ia-abogados-legal — legal tech, privilegio, ética, errores de citación
11 mexico-estados-unidos-ia — operación binacional, datos cross-border, nearshoring tech

La noticia DEBE permitir responder: qué ocurrió, por qué importa, qué riesgo/oportunidad y qué debería revisar una empresa.

RECHAZA (score < 40) si es: marketing de producto, hype/startup valuation sin gobernanza,
guías genéricas de comercio/shipping/Incoterms, farándula, o tech sin decisión empresarial/legal.

Devuelve SOLO JSON:
{{
  "relevance_score": <0-100>,
  "news_type_id": <1-11 o null si irrelevante>,
  "news_type_slug": "<slug o null>",
  "reason": "<una frase>",
  "editorial_fit": <true|false>,
  "four_questions_ok": <true|false>
}}

TEXTO:
\"\"\"
{text}
\"\"\"
"""


def build_eval_prompt(typologies: list[dict[str, Any]] | None = None) -> str:
    """Prompt de evaluación alineado a los temas activos (perfil o PDF)."""
    pool = typologies or NEWS_TYPOLOGIES
    lines = []
    for t in pool:
        mid = t.get("monitor") or t.get("name") or ""
        lines.append(f"{t['id']} {t['slug']} — {mid}")
    catalog = "\n".join(lines) if lines else "1 general — noticias de IA empresarial"
    max_id = max((int(t.get("id") or 1) for t in pool), default=11)
    return f"""Eres el curador editorial de Juan Vásquez (IA, gobernanza, PI, empresas, eje México–EE.UU.).

Clasifica la noticia en UNA tipología (1–{max_id}) o descártala.

TIPOLOGÍAS (prioridad alta → baja):
{catalog}

La noticia DEBE permitir responder: qué ocurrió, por qué importa, qué riesgo/oportunidad y qué debería revisar una empresa.

RECHAZA (score < 40) si es: marketing de producto, hype/startup valuation sin gobernanza,
guías genéricas de comercio/shipping/Incoterms, farándula, o tech sin decisión empresarial/legal.

Devuelve SOLO JSON:
{{{{
  "relevance_score": <0-100>,
  "news_type_id": <1-{max_id} o null si irrelevante>,
  "news_type_slug": "<slug o null>",
  "reason": "<una frase>",
  "editorial_fit": <true|false>,
  "four_questions_ok": <true|false>
}}}}

TEXTO:
\"\"\"
{{text}}
\"\"\"
"""


def default_search_themes() -> list[dict[str, Any]]:
    """Copia editable de las tipologías del PDF (para sembrar en perfil)."""
    return deepcopy(NEWS_TYPOLOGIES)


def normalize_theme(raw: dict[str, Any], fallback_id: int = 1) -> dict[str, Any] | None:
    """Normaliza un tema editable del perfil."""
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip()
    if not name:
        return None
    slug = str(raw.get("slug") or "").strip().lower().replace(" ", "-")
    if not slug:
        slug = f"tema-{fallback_id}"
    queries_raw = raw.get("queries") or []
    if isinstance(queries_raw, str):
        queries = [q.strip() for q in queries_raw.replace(";", "\n").splitlines() if q.strip()]
    elif isinstance(queries_raw, list):
        queries = [str(q).strip() for q in queries_raw if str(q).strip()]
    else:
        queries = []
    try:
        theme_id = int(raw.get("id") or fallback_id)
    except (TypeError, ValueError):
        theme_id = fallback_id
    return {
        "id": theme_id,
        "slug": slug[:64],
        "name": name[:180],
        "monitor": str(raw.get("monitor") or "")[:800],
        "why": str(raw.get("why") or "")[:600],
        "editorial_angle": str(raw.get("editorial_angle") or "")[:400],
        "queries": queries[:12],
        "pillar_slug": (str(raw.get("pillar_slug") or "").strip().lower()[:64] or None),
        "is_active": bool(raw.get("is_active", True)),
    }


def normalize_themes(raw_list: list | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw_list or [], start=1):
        theme = normalize_theme(item, fallback_id=i)
        if theme:
            out.append(theme)
    # Reasignar ids secuenciales si hay huecos
    for i, theme in enumerate(out, start=1):
        theme["id"] = i
    return out


def typologies_from_profile(profile: Any | None) -> list[dict[str, Any]]:
    """Temas activos del perfil; si vacío, tipologías del PDF."""
    stored = getattr(profile, "search_themes_json", None) if profile is not None else None
    themes = normalize_themes(stored if isinstance(stored, list) else None)
    active = [t for t in themes if t.get("is_active", True)]
    if active:
        return active
    return default_search_themes()


def typology_by_id(type_id: int | None, typologies: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    if not type_id:
        return None
    pool = typologies or NEWS_TYPOLOGIES
    for t in pool:
        if t["id"] == int(type_id):
            return t
    return None


def queries_for_priorities(
    max_priority: int = 11,
    typologies: list[dict[str, Any]] | None = None,
) -> list[str]:
    """Queries de tipologías con id <= max_priority."""
    pool = typologies or NEWS_TYPOLOGIES
    out: list[str] = []
    for t in pool:
        if int(t.get("id") or 99) <= max_priority and t.get("is_active", True):
            out.extend(t.get("queries") or [])
    return out


def describe_typologies(typologies: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    pool = typologies or NEWS_TYPOLOGIES
    return [
        {
            "id": t["id"],
            "slug": t["slug"],
            "name": t["name"],
            "monitor": t.get("monitor"),
            "why": t.get("why"),
            "editorial_angle": t.get("editorial_angle"),
            "pillar_slug": t.get("pillar_slug"),
            "query_count": len(t.get("queries") or []),
            "is_active": t.get("is_active", True),
        }
        for t in pool
    ]
