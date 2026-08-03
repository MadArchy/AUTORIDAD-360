"""Tools editoriales como StructuredTool nativo de langchain-core.

Las funciones de dominio siguen en este módulo; LangGraph las invoca vía
StructuredTool.invoke (esquema Pydantic + descripción tipada).
"""

from __future__ import annotations

from typing import Any, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.content import ContentPackage, ContentPiece
from app.models.editorial import NewsArticle
from app.services.agentic_searcher import AgenticSearcherService
from app.services.content_generation import create_content_package
from app.services.content_review import run_reviews
from app.services.llm import classify_article, process_unclassified, verify_article


ToolFn = Callable[..., dict[str, Any]]


def tool_scout_web(
    db: Session,
    *,
    max_queries: int = 6,
    max_results_per_query: int = 2,
    queries: list[str] | None = None,
    max_priority: int = 6,
    max_age_hours: int = 36,
) -> dict[str, Any]:
    """Por defecto prioriza tipologías 1–6 (regulación, fallos, legales, éxito, rezago, PI)."""
    service = AgenticSearcherService(
        db,
        organization_id=db.info.get("organization_id"),
    )
    stats = service.run_search_cycle(
        max_results_per_query=max_results_per_query,
        extra_queries=queries,
        max_queries=max(1, max_queries),
        max_priority=max_priority,
        max_age_hours=max_age_hours,
    )
    return {"stats": stats}


def tool_classify_batch(db: Session, *, limit: int = 5) -> dict[str, Any]:
    return process_unclassified(
        db,
        limit=limit,
        organization_id=db.info.get("organization_id"),
    )


def tool_classify_one(db: Session, *, article_id: int) -> dict[str, Any]:
    query = db.query(NewsArticle).filter(NewsArticle.id == article_id)
    if db.info.get("organization_id") is not None:
        query = query.filter(
            NewsArticle.organization_id == db.info["organization_id"]
        )
    article = query.first()
    if not article:
        raise ValueError(f"Article {article_id} not found")
    result = classify_article(db, article)
    return {"article_id": article_id, "status": article.status, "result": result}


def tool_verify_one(db: Session, *, article_id: int) -> dict[str, Any]:
    query = db.query(NewsArticle).filter(NewsArticle.id == article_id)
    if db.info.get("organization_id") is not None:
        query = query.filter(
            NewsArticle.organization_id == db.info["organization_id"]
        )
    article = query.first()
    if not article:
        raise ValueError(f"Article {article_id} not found")
    result = verify_article(db, article)
    return {
        "article_id": article_id,
        "status": article.status,
        "publishable": result.get("publishable"),
        "result": result,
    }


def tool_write_package(
    db: Session,
    *,
    article_id: int,
    languages: list[str] | None = None,
    prefer_llm: bool = True,
) -> dict[str, Any]:
    query = db.query(NewsArticle).filter(NewsArticle.id == article_id)
    if db.info.get("organization_id") is not None:
        query = query.filter(
            NewsArticle.organization_id == db.info["organization_id"]
        )
    article = query.first()
    if not article:
        raise ValueError(f"Article {article_id} not found")
    package = create_content_package(
        db,
        article,
        languages=languages or ["es"],
        prefer_llm=prefer_llm,
        organization_id=db.info.get("organization_id"),
    )
    pieces = (
        db.query(ContentPiece)
        .filter(ContentPiece.package_id == package.id)
        .all()
    )
    return {
        "package_id": package.id,
        "status": package.status,
        "piece_ids": [p.id for p in pieces],
        "formats": [p.format_type for p in pieces],
    }


def tool_review_package(db: Session, *, package_id: int) -> dict[str, Any]:
    package_query = db.query(ContentPackage).filter(ContentPackage.id == package_id)
    if db.info.get("organization_id") is not None:
        package_query = package_query.filter(
            ContentPackage.organization_id == db.info["organization_id"]
        )
    package = package_query.first()
    if not package:
        raise ValueError(f"Package {package_id} not found")
    article = db.query(NewsArticle).filter(NewsArticle.id == package.article_id).first()
    if not article:
        raise ValueError("Package article missing")

    pieces = (
        db.query(ContentPiece)
        .filter(ContentPiece.package_id == package_id)
        .all()
    )
    outcomes: list[dict[str, Any]] = []
    for piece in pieces:
        run_reviews(db, piece, article)
        outcomes.append(
            {
                "piece_id": piece.id,
                "format": piece.format_type,
                "status": piece.status,
                "factual_passed": (piece.factual_review_json or {}).get("passed"),
                "brand_passed": (piece.brand_review_json or {}).get("passed"),
            }
        )
    db.commit()
    return {"package_id": package_id, "reviews": outcomes}


def tool_trend_ad_notes(
    db: Session,
    *,
    slug: str = "juan-vasquez",
    max_queries: int = 12,
) -> dict[str, Any]:
    from app.services.trend_ad_advisor import generate_ad_trend_notes

    org_id = db.info.get("organization_id")
    notes = generate_ad_trend_notes(
        db,
        organization_id=org_id,
        slug=slug,
        max_queries=max(4, min(int(max_queries or 12), 20)),
        persist=True,
    )
    return {
        "notes": notes,
        "trends_count": len(notes.get("trends") or []),
        "hits_count": (notes.get("meta") or {}).get("hits_count"),
    }


def _load_article_for_brief(db: Session, article_id: int | None) -> NewsArticle | None:
    if not article_id:
        return None
    query = db.query(NewsArticle).filter(NewsArticle.id == article_id)
    if db.info.get("organization_id") is not None:
        query = query.filter(NewsArticle.organization_id == db.info["organization_id"])
    return query.first()


def _draft_practice_brief(
    db: Session,
    *,
    practice: str,
    article_id: int | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    """Brief especializado con voz Juan (AI governance o IP/patents)."""
    from app.services import fase5_ai
    from app.services.juan_persona import LEGAL_DISCLAIMER, get_juan_persona_block

    article = _load_article_for_brief(db, article_id)
    if article_id and not article:
        raise ValueError(f"Article {article_id} not found")

    persona = get_juan_persona_block(
        db,
        organization_id=db.info.get("organization_id"),
        practice=practice,
    )
    source_block = ""
    if article:
        snippet = (article.full_text or article.summary or "")[:2500]
        source_block = (
            f"\nFUENTE ANCLA\nTítulo: {article.title}\n"
            f"Medio: {article.source_name}\nURL: {article.source_url}\n"
            f"Texto:\n{snippet}\n"
        )
    topic_line = topic or (article.title if article else "Tendencia de alto impacto en la práctica")

    if practice == "ai_governance":
        angle = (
            "Ángulo AI Readiness & Governance: Education (gente), Technology (postura real de tools/datos) "
            "y Governance (frameworks que operan). Evita vender 'solo una policy'."
        )
    elif practice == "ip_patents":
        angle = (
            "Ángulo IP/Patents: prosecution, FTO, inventorship, AI+IP, portafolio alineado a producto. "
            "Sé preciso; no inventes números de patente ni outcomes."
        )
    else:
        angle = "Ángulo editorial de autoridad para líderes que cargan el riesgo."

    prompt = f"""{persona}

{angle}

TEMA / FOCO: {topic_line}
{source_block}

Redacta un BRIEF ejecutivo en markdown (400–700 palabras) con:
1. Hecho ancla (si hay fuente)
2. Lectura de riesgo / oportunidad para GC, board o CISO
3. "Mi perspectiva"
4. 3 acciones concretas esta semana
5. Disclaimer al final

Responde SOLO markdown. Disclaimer obligatorio:
{LEGAL_DISCLAIMER}
"""
    text, meta = fase5_ai.complete(db, task_type="generate_content", prompt=prompt)
    return {
        "practice": practice,
        "article_id": article.id if article else None,
        "topic": topic_line,
        "brief_markdown": (text or "").strip(),
        "model_used": (meta or {}).get("model_used"),
        "disclaimer": LEGAL_DISCLAIMER,
    }


def tool_draft_juan_editorial(
    db: Session,
    *,
    article_id: int,
    languages: list[str] | None = None,
    prefer_llm: bool = True,
) -> dict[str, Any]:
    """Paquete multi-formato con voz Juan (wrapper de write_package)."""
    result = tool_write_package(
        db,
        article_id=article_id,
        languages=languages,
        prefer_llm=prefer_llm,
    )
    result["practice"] = "editorial"
    result["persona"] = "juan_vasquez"
    return result


def tool_draft_ai_governance_brief(
    db: Session,
    *,
    article_id: int | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    return _draft_practice_brief(
        db, practice="ai_governance", article_id=article_id, topic=topic
    )


def tool_draft_ip_patent_brief(
    db: Session,
    *,
    article_id: int | None = None,
    topic: str | None = None,
) -> dict[str, Any]:
    return _draft_practice_brief(
        db, practice="ip_patents", article_id=article_id, topic=topic
    )


# --- Esquemas Pydantic (args de StructuredTool) ---


class ScoutWebInput(BaseModel):
    max_queries: int = Field(default=6, ge=1, le=20)
    max_results_per_query: int = Field(default=2, ge=1, le=10)
    queries: list[str] | None = None
    max_priority: int = Field(default=6, ge=1, le=11)


class ClassifyBatchInput(BaseModel):
    limit: int = Field(default=5, ge=1, le=30)


class ArticleIdInput(BaseModel):
    article_id: int = Field(..., ge=1)


class WritePackageInput(BaseModel):
    article_id: int = Field(..., ge=1)
    languages: list[str] | None = Field(default=None)
    prefer_llm: bool = True


class ReviewPackageInput(BaseModel):
    package_id: int = Field(..., ge=1)


class TrendAdNotesInput(BaseModel):
    slug: str = Field(default="juan-vasquez")
    max_queries: int = Field(default=12, ge=4, le=20)


class PracticeBriefInput(BaseModel):
    article_id: int | None = Field(default=None, ge=1)
    topic: str | None = None


TOOL_META: dict[str, dict[str, Any]] = {
    "scout_web": {
        "description": "Busca las 11 tipologías del briefing Juan Vásquez (regulación, fallos, legales, PI, MX-US…)",
        "args_schema": ScoutWebInput,
        "fn": tool_scout_web,
    },
    "classify_batch": {
        "description": "Clasifica y verifica un lote de artículos en estado collected",
        "args_schema": ClassifyBatchInput,
        "fn": tool_classify_batch,
    },
    "classify_one": {
        "description": "Clasifica un artículo por id",
        "args_schema": ArticleIdInput,
        "fn": tool_classify_one,
    },
    "verify_one": {
        "description": "Verifica factual grounding de un artículo por id",
        "args_schema": ArticleIdInput,
        "fn": tool_verify_one,
    },
    "write_package": {
        "description": "Genera paquete multi-formato a partir de un artículo verificado",
        "args_schema": WritePackageInput,
        "fn": tool_write_package,
    },
    "review_package": {
        "description": "Aplica revisores factual y de marca a todas las piezas de un paquete",
        "args_schema": ReviewPackageInput,
        "fn": tool_review_package,
    },
    "trend_ad_notes": {
        "description": (
            "Investiga tendencias en LinkedIn/YouTube/X/TikTok/Instagram "
            "según temas del perfil y genera notas de CTA orgánico por red"
        ),
        "args_schema": TrendAdNotesInput,
        "fn": tool_trend_ad_notes,
    },
    "draft_juan_editorial": {
        "description": (
            "Redactor Juan: genera paquete multi-formato con voz de autoridad "
            "(IP, AI readiness, gobernanza) desde un artículo verificado"
        ),
        "args_schema": WritePackageInput,
        "fn": tool_draft_juan_editorial,
    },
    "draft_ai_governance_brief": {
        "description": (
            "Brief AI Readiness & Governance (Education / Technology / Governance) "
            "en voz Juan; opcionalmente anclado a un article_id"
        ),
        "args_schema": PracticeBriefInput,
        "fn": tool_draft_ai_governance_brief,
    },
    "draft_ip_patent_brief": {
        "description": (
            "Brief IP/Patents (prosecution, FTO, inventorship, AI+IP) en voz Juan; "
            "opcionalmente anclado a un article_id"
        ),
        "args_schema": PracticeBriefInput,
        "fn": tool_draft_ip_patent_brief,
    },
}


# Compat: catálogo usado por describe()/prompts
TOOL_CATALOG: dict[str, dict[str, Any]] = {
    name: {"description": meta["description"], "fn": meta["fn"]}
    for name, meta in TOOL_META.items()
}


def build_structured_tools(db: Session) -> dict[str, StructuredTool]:
    """Construye StructuredTools ligados a la sesión DB de la corrida."""
    tools: dict[str, StructuredTool] = {}
    for name, meta in TOOL_META.items():
        domain_fn = meta["fn"]

        def _make_func(fn: ToolFn = domain_fn):
            def _bound(**kwargs: Any) -> dict[str, Any]:
                return fn(db, **kwargs)

            return _bound

        tools[name] = StructuredTool.from_function(
            func=_make_func(),
            name=name,
            description=meta["description"],
            args_schema=meta["args_schema"],
        )
    return tools


def invoke_tool(name: str, db: Session, **kwargs: Any) -> dict[str, Any]:
    """Invoca la tool vía StructuredTool nativo (validación de args incluida)."""
    if name not in TOOL_META:
        raise ValueError(f"Unknown tool: {name}")
    tool = build_structured_tools(db)[name]
    result = tool.invoke(kwargs)
    if not isinstance(result, dict):
        return {"result": result}
    return result
