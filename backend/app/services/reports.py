from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.config import settings
from app.models import BlogPost, NewsArticle, WeeklyReport
from app.services.scoring import get_top10


def _week_bounds(reference: datetime | None = None) -> tuple[datetime, datetime]:
    ref = reference or datetime.utcnow()
    start = ref - timedelta(days=ref.weekday())
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start, end


def generate_weekly_report(
    db: Session,
    organization_id: int | None = None,
) -> WeeklyReport:
    week_start, week_end = _week_bounds()
    top10 = get_top10(db, days=7, organization_id=organization_id)

    items = []
    for rank, scored in enumerate(top10, start=1):
        article = scored.article
        items.append(
            {
                "rank": rank,
                "article_id": article.id,
                "title": article.title,
                "source_url": article.source_url,
                "source_name": article.source_name,
                "total_score": scored.total_score,
                "summary": article.summary,
                "category": article.category.name if article.category else None,
            }
        )

    report_json = {
        "client": settings.client_name,
        "week_start": week_start.date().isoformat(),
        "week_end": week_end.date().isoformat(),
        "generated_at": datetime.utcnow().isoformat(),
        "top10": items,
        "weights": {
            "relevance": 0.25,
            "impact": 0.20,
            "reliability": 0.15,
            "freshness": 0.15,
            "content_potential": 0.10,
            "mx_us_relevance": 0.10,
            "conversion": 0.05,
        },
    }

    lines = [
        f"# Reporte Semanal — {settings.client_name}",
        f"Semana: {week_start.date()} a {week_end.date()}",
        "",
        "## Top 10 noticias verificadas",
        "",
    ]
    for item in items:
        lines.extend(
            [
                f"### {item['rank']}. {item['title']}",
                f"- **Puntaje:** {item['total_score']}",
                f"- **Fuente:** [{item['source_name']}]({item['source_url']})",
                f"- **Categoría:** {item['category']}",
                f"- **Resumen:** {item['summary']}",
                "",
            ]
        )

    markdown = "\n".join(lines)

    existing = (
        db.query(WeeklyReport)
        .filter(
            WeeklyReport.organization_id == organization_id,
            WeeklyReport.week_start == week_start,
            WeeklyReport.week_end == week_end,
        )
        .first()
    )
    if existing:
        existing.report_json = report_json
        existing.markdown_content = markdown
        db.commit()
        db.refresh(existing)
        return existing

    report = WeeklyReport(
        organization_id=organization_id,
        week_start=week_start,
        week_end=week_end,
        report_json=report_json,
        markdown_content=markdown,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def create_blog_draft_from_article(
    db: Session,
    article: NewsArticle,
    *,
    regenerate: bool = False,
    organization_id: int | None = None,
) -> "BlogPost":
    """Crea (o regenera) un borrador de blog con análisis editorial vía LLM."""
    import html
    import re

    if article.status not in (
        "collected",
        "classified",
        "verified",
        "approved",
        "published",
    ):
        raise ValueError(
            f"No se puede crear borrador de blog desde status '{article.status}'"
        )

    org_id = organization_id or article.organization_id

    slug_base = re.sub(r"[^a-z0-9]+", "-", article.title.lower()).strip("-")[:80]
    slug = f"{slug_base}-{article.id}"
    citation = f"Fuente original: {article.source_name} — {article.source_url}"

    existing = db.query(BlogPost).filter(BlogPost.article_id == article.id).first()
    # Si ya existe publicado/aprobado y no pedimos regenerar, devolver el mismo
    if existing and not regenerate and existing.status in ("approved", "published"):
        if org_id and existing.organization_id is None:
            existing.organization_id = org_id
            db.commit()
            db.refresh(existing)
        return existing

    title, paragraphs, mode = _generate_blog_body(db, article)

    paras_html = "\n  ".join(
        f"<p>{html.escape(p)}</p>" for p in paragraphs if p and str(p).strip()
    )
    content_html = f"""
<article data-generation="{html.escape(mode)}">
  <h2>{html.escape(title)}</h2>
  {paras_html}
  <blockquote cite="{html.escape(article.source_url)}">
    <p>{html.escape((article.summary or article.title or '')[:400])}</p>
  </blockquote>
  <p><strong>{html.escape(citation)}</strong></p>
  <p><a href="{html.escape(article.source_url)}" target="_blank" rel="noopener noreferrer">Leer noticia original</a></p>
</article>
""".strip()
    from app.services.html_sanitize import sanitize_editorial_html

    content_html = sanitize_editorial_html(content_html)

    if existing:
        existing.title = title[:512] if title else article.title
        existing.content_html = content_html
        existing.source_url = article.source_url
        existing.source_citation = citation
        if org_id and existing.organization_id is None:
            existing.organization_id = org_id
        if existing.status == "pending" or regenerate:
            existing.status = "pending"
        from app.services.blog_seo import apply_blog_seo_defaults

        apply_blog_seo_defaults(db, existing, article=article)
        db.commit()
        db.refresh(existing)
        return existing

    post = BlogPost(
        organization_id=org_id,
        article_id=article.id,
        title=title[:512] if title else article.title,
        slug=slug,
        content_html=content_html,
        source_url=article.source_url,
        source_citation=citation,
        status="pending",
    )
    from app.services.blog_seo import apply_blog_seo_defaults

    apply_blog_seo_defaults(db, post, article=article)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def _generate_blog_body(db: Session, article: NewsArticle) -> tuple[str, list[str], str]:
    """Devuelve (title, paragraphs, generation_mode)."""
    from app.services.llm import _call_model, _extract_json

    summary = article.summary or article.title or ""
    facts = []
    if article.classification_json:
        facts = article.classification_json.get("key_facts") or []

    angles = (
        "riesgo de cumplimiento para el consejo",
        "oportunidad competitiva MX-US",
        "lo que el GC debería preguntar mañana",
        "impacto en vendors y control interno",
    )
    angle = angles[article.id % len(angles)]

    prompt = f"""Eres Juan Vásquez, consultor en IA, regulación y Derecho Tech (México / EE.UU.).
Escribe un ARTÍCULO DE BLOG editorial (no un resumen copy-paste).
Ángulo obligatorio: {angle}.
Tono: directivo, analítico, humano. Sin hype. Máximo 1 emoji.

Devuelve SOLO JSON:
{{
  "title": "<título editorial distinto al titular de la noticia>",
  "paragraphs": [
    "<gancho 2-3 frases>",
    "<contexto con hechos de la fuente>",
    "<análisis: riesgos/implicaciones>",
    "<perspectiva Juan: qué deben hacer líderes>",
    "<cierre con pregunta o CTA>"
  ],
  "article_id": {article.id},
  "source_url": "{article.source_url}"
}}

TITULAR ORIGINAL: {article.title}
RESUMEN: {summary}
KEY FACTS: {facts}
TEXTO FUENTE (recortado):
\"\"\"
{(article.full_text or '')[:8000]}
\"\"\"
"""
    try:
        raw, _model = _call_model(db, "blog_article", prompt)
        data = _extract_json(raw)
        title = str(data.get("title") or article.title).strip()
        paragraphs = data.get("paragraphs") or []
        if isinstance(paragraphs, str):
            paragraphs = [paragraphs]
        paragraphs = [str(p).strip() for p in paragraphs if str(p).strip()]
        if data.get("article_id") not in (None, article.id):
            raise ValueError("article_id mismatch")
        if len(paragraphs) < 3:
            raise ValueError("too few paragraphs")
        return title, paragraphs[:7], "gateway"
    except Exception:
        # Fallback: aún así estructura editorial, no solo el summary crudo
        title = f"Lo que implica para líderes: {article.title[:90]}"
        paragraphs = [
            f"La señal de esta semana no es el titular, sino la decisión que fuerza: {summary[:280]}",
            f"Hechos base: {'; '.join(str(f) for f in (facts[:3] or [summary]))}.",
            (
                "Mi lectura: conviene separar ruido mediático de riesgo real — "
                "compliance, vendors y gobernanza — antes de escalar el tema al consejo."
            ),
            (
                "Pregunta útil: ¿quién en tu organización traduce esta noticia a control "
                "operativo en las próximas 72 horas?"
            ),
        ]
        return title, paragraphs, "deterministic"
