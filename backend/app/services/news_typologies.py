"""Tipologías editoriales — Tipos_de_Noticias_IA_Juan_Vasquez.pdf

Prioridad 1–11. Cada tipología define qué monitorear y queries de búsqueda.
Filtro de calidad: la noticia debe permitir responder qué ocurrió, por qué importa,
qué riesgo/oportunidad genera y qué debería revisar una empresa.
"""

from __future__ import annotations

from typing import Any

NEWS_TYPOLOGIES: list[dict[str, Any]] = [
    {
        "id": 1,
        "slug": "politica-regulacion-ia",
        "name": "Política y regulación de IA",
        "monitor": "Leyes, proyectos legislativos, políticas públicas, órdenes ejecutivas y decisiones gubernamentales MX/US",
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
        "name": "Empresas que implementaron mal la IA",
        "monitor": "Pilotos cancelados, chatbots con errores, sobrecostos, baja adopción, fallas de supervisión",
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
        "name": "Casos legales por uso de IA",
        "monitor": "Demandas, sanciones, investigaciones, decisiones judiciales por decisiones automatizadas",
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
        "name": "Empresas que implementaron IA con éxito",
        "monitor": "Casos con mejoras verificables en productividad, costos, servicio o automatización",
        "queries": [
            "enterprise AI success case study productivity",
            "company scales AI governance controls adoption",
            "caso éxito inteligencia artificial empresa productividad",
        ],
    },
    {
        "id": 5,
        "slug": "empresas-rezagadas-ia",
        "name": "Empresas rezagadas en adopción",
        "monitor": "Sectores/compañías que pierden competitividad por reaccionar tarde a la transformación",
        "queries": [
            "cost of delaying AI adoption enterprise",
            "laggard companies AI competitiveness",
            "retraso adopción inteligencia artificial empresas",
        ],
    },
    {
        "id": 6,
        "slug": "patentes-pi-ia",
        "name": "Innovación, patentes y Propiedad Intelectual",
        "monitor": "Patentes de IA, inventorship, copyright, secretos, licencias, titularidad de outputs",
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
        "name": "Inversiones empresariales en IA",
        "monitor": "Data centers, M&A, alianzas, fondos, startups, presupuestos, capacitación",
        "queries": [
            "corporate AI investment data center acquisition",
            "inversión inteligencia artificial empresas México",
            "AI startup funding governance enterprise",
        ],
    },
    {
        "id": 8,
        "slug": "privacidad-ciberseguridad-ia",
        "name": "Privacidad y ciberseguridad",
        "monitor": "Filtraciones, datos corporativos en entrenamiento, ataques, riesgos de proveedores",
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
        "name": "Empleo y transformación laboral",
        "monitor": "Automatización, reestructuras, nuevos cargos, selección algorítmica, RH",
        "queries": [
            "AI workforce restructuring HR algorithmic hiring",
            "selección algorítmica discriminación IA empleo",
            "automatización puestos trabajo inteligencia artificial empresa",
        ],
    },
    {
        "id": 10,
        "slug": "ia-abogados-legal",
        "name": "IA para abogados y equipos jurídicos",
        "monitor": "Legal tech, confidencialidad, privilegio, ética, errores de citación, productividad jurídica",
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
        "name": "Relación México–Estados Unidos",
        "monitor": "Datos cross-border, contratos, proveedores, nearshoring tech, PI, diferencias regulatorias",
        "queries": [
            "cross-border data transfer AI Mexico United States",
            "nearshoring inteligencia artificial gobernanza México",
            "US Mexico AI regulation comparison companies",
            "transferencia datos personales IA México Estados Unidos",
        ],
    },
]

# Queries planas priorizadas (P1–P3 primero, luego el resto)
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
1 política-regulacion-ia — leyes/políticas/órdenes ejecutivas MX o US sobre IA
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


def typology_by_id(type_id: int | None) -> dict[str, Any] | None:
    if not type_id:
        return None
    for t in NEWS_TYPOLOGIES:
        if t["id"] == int(type_id):
            return t
    return None


def queries_for_priorities(max_priority: int = 11) -> list[str]:
    """Queries de tipologías con id <= max_priority."""
    out: list[str] = []
    for t in NEWS_TYPOLOGIES:
        if t["id"] <= max_priority:
            out.extend(t["queries"])
    return out


def describe_typologies() -> list[dict[str, Any]]:
    return [
        {
            "id": t["id"],
            "slug": t["slug"],
            "name": t["name"],
            "monitor": t["monitor"],
            "query_count": len(t["queries"]),
        }
        for t in NEWS_TYPOLOGIES
    ]
