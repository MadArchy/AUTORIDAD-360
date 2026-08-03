import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models import NewsArticle, BlogPost, BlogStatus, MultiNewsSynthesis

logger = logging.getLogger(__name__)

_DIGEST_MARKERS = re.compile(
    r"(noticia\s*\d+|fuente\s*\d+|la primera noticia|la segunda noticia|"
    r"la tercera noticia|según la primera|según la segunda|"
    r"resumen de cada|digest por medio)",
    re.IGNORECASE,
)


def _sanitize_fused_html(html: str) -> str:
    """Normaliza clases y suaviza restos de digest por noticia si el modelo se desvía."""
    text = (html or "").strip()
    if not text:
        return text
    # Preferir contenedor de ensayo
    if 'class="jv-essay"' not in text and "class='jv-essay'" not in text:
        text = f'<article class="jv-essay">{text}</article>'
    # Quitar caja "Resumen Ejecutivo / C-Level" genérica si aparece
    def _to_lede(match: re.Match) -> str:
        inner = re.sub(r"</?p[^>]*>", "", match.group(1), flags=re.IGNORECASE).strip()
        return f'<p class="jv-lede">{inner}</p>'

    text = re.sub(
        r"<div[^>]*>\s*<h3[^>]*>\s*Resumen Ejecutivo[^<]*</h3>(.*?)</div>",
        _to_lede,
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = text.replace("Resumen Ejecutivo (C-Level Briefing)", "")
    text = text.replace("C-Level Briefing", "")
    if _DIGEST_MARKERS.search(text):
        logger.warning("Síntesis con marcadores de digest por noticia; se conserva con aviso de criterio")
    return text


def call_llm(
    prompt: str,
    system_prompt: str = "",
    db: Session | None = None,
    provider_mode: str = "auto",
) -> str:
    """Invoca el Gateway (local / API / auto). Cloud no cae a Ollama en silencio."""
    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    mode = (provider_mode or "auto").strip().lower()
    if db:
        try:
            from app.services.fase5_ai import complete

            text, _meta = complete(
                db,
                task_type="content_generation",
                prompt=full_prompt,
                provider_mode=mode,
            )
            if text and text.strip():
                return text
        except Exception as exc:
            if mode in {"cloud", "api", "paid", "paid_only", "web"}:
                raise
            logger.warning(f"Error invocando Gateway de IA: {exc}, probando fallback...")

    if mode in {"cloud", "api", "paid", "paid_only", "web"}:
        raise RuntimeError(
            "No hay proveedor API disponible. Configura tu API key en Inteligencia Artificial."
        )

    from app.services.llm import _call_ollama

    return _call_ollama(full_prompt)


def auto_select_best_cluster(
    db: Session,
    pillar_id: Optional[int] = None,
    organization_id: Optional[int] = None,
    limit: int = 4
) -> List[int]:
    """
    Selección automática (Auto-Curaduría) de las 3 a 4 mejores noticias
    ordenadas por puntuación de impacto (total_score) y frescura.
    Compatible con MySQL (sin NULLS LAST).
    """
    from sqlalchemy import case

    def _ranked(base):
        # MySQL no soporta NULLS LAST; forzamos NULLs al final con CASE.
        score_rank = case((NewsArticle.total_score.is_(None), 1), else_=0)
        date_rank = case((NewsArticle.published_at.is_(None), 1), else_=0)
        return base.order_by(
            score_rank.asc(),
            NewsArticle.total_score.desc(),
            date_rank.asc(),
            NewsArticle.published_at.desc(),
            NewsArticle.id.desc(),
        ).limit(limit).all()

    query = db.query(NewsArticle)
    if organization_id is not None:
        query = query.filter(NewsArticle.organization_id == organization_id)
    if pillar_id is not None:
        query = query.filter(NewsArticle.category_id == pillar_id)

    articles = _ranked(query)

    if not articles or len(articles) < 2:
        # Si no hay suficientes por filtro estricto, buscar sin filtro de pilar
        fallback = db.query(NewsArticle)
        if organization_id is not None:
            fallback = fallback.filter(NewsArticle.organization_id == organization_id)
        articles = _ranked(fallback)

    if len(articles) < 2:
        raise ValueError("Se requieren al menos 2 noticias en la base de datos para ejecutar la síntesis automática.")

    return [art.id for art in articles]


def suggest_central_focus(
    db: Session,
    article_ids: List[int],
    provider_mode: str = "auto",
) -> Dict[str, Any]:
    """
    Analiza un grupo de noticias seleccionadas (2 a 5) y genera una sugerencia
    automática de 'Foco Único' u 'Objetivo Editorial Central'.
    """
    articles = db.query(NewsArticle).filter(NewsArticle.id.in_(article_ids)).all()
    if not articles:
        raise ValueError("No se encontraron noticias con los IDs proporcionados.")

    articles_context = []
    for idx, art in enumerate(articles, 1):
        summary_text = art.summary or (art.full_text[:300] if art.full_text else "")
        articles_context.append(f"Noticia {idx}: {art.title}\nFuente: {art.source_name}\nResumen: {summary_text}\n")

    combined_text = "\n---\n".join(articles_context)

    from app.services.juan_persona import get_juan_persona_block

    org_id = getattr(articles[0], "organization_id", None)
    system_prompt = (
        get_juan_persona_block(db, organization_id=org_id, practice="editorial")
        + "\n\nTu tarea: proponer UNA sola tesis editorial (no un resumen de titulares) "
        "que permita fusionar estas señales en un único argumento con tu criterio."
    )

    user_prompt = f"""Señales de entrada ({len(articles)} fuentes):

{combined_text}

Devuelve JSON con "suggested_focus": 1–2 oraciones = la TESIS que unifica el fenómeno
(riesgo/oportunidad para GC, board o CISO). Prohibido listar noticias una por una.
Ejemplo: {{"suggested_focus": "Cuando la inversión en infraestructura de IA se acelera sin una postura clara de gobernanza, el riesgo no es tecnológico: es de responsabilidad ejecutiva."}}
"""

    try:
        raw_response = call_llm(
            user_prompt,
            system_prompt=system_prompt,
            db=db,
            provider_mode=provider_mode,
        )
        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return {"suggested_focus": data.get("suggested_focus", raw_response.strip())}
        return {"suggested_focus": raw_response.strip().strip('"')}
    except Exception as e:
        logger.error(f"Error sugiriendo foco único: {e}")
        if (provider_mode or "").lower() in {"cloud", "api", "paid", "paid_only", "web"}:
            raise
        main_titles = " y ".join([a.title[:40] for a in articles[:2]])
        return {
            "suggested_focus": f"Análisis consolidado sobre la evolución de {main_titles} y sus implicaciones estratégicas."
        }


def generate_centralized_synthesis(
    db: Session,
    article_ids: List[int],
    central_focus: str,
    author_name: str = "Juan Vásquez",
    organization_id: Optional[int] = None,
    pillar_id: Optional[int] = None,
    provider_mode: str = "auto",
) -> Dict[str, Any]:
    """
    Sintetiza de 2 a 5 noticias en un único artículo de blog de nivel C-Suite / Ejecutivo,
    con caja de Resumen Ejecutivo y sección de 'Fuentes Consultadas'.
    """
    articles = db.query(NewsArticle).filter(NewsArticle.id.in_(article_ids)).all()
    if not articles:
        raise ValueError("No se encontraron noticias válidas para sintetizar.")

    sources_detail = []
    fuentes_html_list = []
    source_citations = []

    for idx, art in enumerate(articles, 1):
        snippet = art.full_text[:1200] if art.full_text else (art.summary or "")
        sources_detail.append(
            f"--- FUENTE {idx} ---\n"
            f"Título: {art.title}\n"
            f"Medio: {art.source_name}\n"
            f"URL: {art.source_url}\n"
            f"Contenido: {snippet}\n"
        )
        source_citations.append({
            "title": art.title,
            "source_name": art.source_name,
            "url": art.source_url
        })
        fuentes_html_list.append(
            f'<li><a href="{art.source_url}" target="_blank" rel="noopener noreferrer">'
            f'<strong>{art.source_name}</strong> — {art.title}</a></li>'
        )

    context_str = "\n".join(sources_detail)
    fuentes_section_html = (
        '<aside class="jv-sources">'
        "<h2>Fuentes acreditadas</h2>"
        "<p class=\"jv-sources__note\">Evidencia usada para anclar el argumento. "
        "No son resúmenes separados: el ensayo las fusiona.</p>"
        "<ol>\n" + "\n".join(fuentes_html_list) + "\n</ol>"
        "</aside>"
    )

    from app.services.juan_persona import LEGAL_DISCLAIMER, get_juan_persona_block

    system_prompt = (
        get_juan_persona_block(
            db, organization_id=organization_id, practice="editorial"
        )
        + "\n\nMISIÓN: redactar UN SOLO ensayo profesional en HTML — un pensamiento "
        "fusionado con tu criterio (voz de "
        f"{author_name}). "
        "Las fuentes son evidencia, no capítulos. Prohibido resumir noticia por noticia."
    )

    user_prompt = f"""TESIS / FOCO ÚNICO (debe gobernar todo el texto):
"{central_focus}"

EVIDENCIA (úsalas como hechos ancla entretejidos; NO hagas un digest de cada una):
{context_str}

REGLAS DURAS DE FORMA Y FONDO:
- Un solo arco argumental: tesis → tensión → implicación → "Mi perspectiva" → acciones.
- PROHIBIDO: "Noticia 1/2", "la primera fuente", "según la segunda noticia", listas de resúmenes por medio, o secciones tipo "qué dice cada outlet".
- Máximo 2–3 hechos concretos del conjunto de fuentes (con medio entre paréntesis si aporta credibilidad). El resto es criterio y lectura ejecutiva.
- Tono soberano, analítico, práctico; cero hype; sin emojis.
- No inventes leyes, casos, patentes ni citas.
- Idioma: español profesional.
- Longitud: 700–1100 palabras aprox.

ESTRUCTURA HTML OBLIGATORIA (usa estas clases; sin estilos inline pesados):
<article class="jv-essay">
  <p class="jv-lede">Apertura con la tesis (2–4 frases). No digas "resumen ejecutivo".</p>
  <h2>La tensión que importa</h2>
  <p>…desarrollo fusionado…</p>
  <h2>Riesgo y oportunidad para quien carga la decisión</h2>
  <p>…lectura para GC / board / CISO…</p>
  <h2>Mi perspectiva</h2>
  <div class="jv-perspective">
    <p>Tu criterio profesional (mín. 5–7 frases): qué está mal en el framing habitual, qué pregunta harías tú, qué no responden las fuentes.</p>
  </div>
  <h2>Qué haría esta semana</h2>
  <ul><li>3–5 acciones concretas</li></ul>
  <p class="jv-disclaimer">{LEGAL_DISCLAIMER}</p>
</article>

NO incluyas la lista de fuentes en el JSON (el sistema la adjunta).

Responde ÚNICAMENTE JSON:
{{
  "title": "Título de ensayo (tesis, no clickbait ni 'análisis consolidado de N noticias')",
  "seo_description": "140–160 caracteres",
  "content_html": "<article class=\\"jv-essay\\">...</article>"
}}
"""

    try:
        raw_response = call_llm(
            user_prompt,
            system_prompt=system_prompt,
            db=db,
            provider_mode=provider_mode,
        )
        json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
        if not json_match:
            raise ValueError("Respuesta del modelo no incluye JSON válido.")

        parsed = json.loads(json_match.group(0))
        article_title = parsed.get("title", f"Criterio editorial: {central_focus[:60]}")
        seo_desc = parsed.get(
            "seo_description", f"Ensayo con criterio Juan Vásquez: {central_focus[:100]}"
        )
        body_html = parsed.get("content_html", "<p>Error al formatear contenido HTML.</p>")
        body_html = _sanitize_fused_html(body_html)
    except Exception as e:
        logger.error(f"Error generando síntesis multifuente con LLM: {e}")
        if (provider_mode or "").lower() in {"cloud", "api", "paid", "paid_only", "web"}:
            raise
        article_title = f"Criterio editorial: {central_focus[:70]}"
        seo_desc = f"Ensayo fusionado con foco en: {central_focus[:100]}"
        body_html = (
            '<article class="jv-essay">'
            f'<p class="jv-lede">{central_focus}</p>'
            "<h2>Mi perspectiva</h2>"
            '<div class="jv-perspective"><p>La evidencia disponible apunta a una '
            "tensión de gobernanza y responsabilidad ejecutiva que no se resuelve "
            "con un resumen de titulares. Requiere postura, no parafraseo.</p></div>"
            f'<p class="jv-disclaimer">{LEGAL_DISCLAIMER}</p>'
            "</article>"
        )

    if LEGAL_DISCLAIMER.lower() not in (body_html or "").lower():
        body_html = (
            f"{body_html}\n"
            f'<p class="jv-disclaimer"><em>{LEGAL_DISCLAIMER}</em></p>'
        )
    final_content_html = f"{body_html}\n{fuentes_section_html}"

    base_slug = re.sub(r"[^\w\s-]", "", article_title.lower())
    base_slug = re.sub(r"[-\s]+", "-", base_slug).strip("-")[:80]
    unique_slug = f"sintesis-{base_slug}-{int(datetime.utcnow().timestamp())}"

    cat_slug = "general"
    if hasattr(articles[0], "category") and articles[0].category:
        cat_slug = getattr(articles[0].category, "slug", "general")

    blog_post = BlogPost(
        organization_id=organization_id or articles[0].organization_id,
        article_id=articles[0].id,
        title=article_title,
        slug=unique_slug,
        content_html=final_content_html,
        source_url=articles[0].source_url,
        source_citation=json.dumps(source_citations, ensure_ascii=False),
        status=BlogStatus.PENDING.value,
        author_name=author_name,
        categories_json=[cat_slug],
        seo_description=seo_desc[:320]
    )

    db.add(blog_post)
    db.flush()

    synthesis_record = MultiNewsSynthesis(
        organization_id=organization_id or articles[0].organization_id,
        pillar_id=pillar_id,
        central_focus=central_focus,
        source_article_ids=article_ids,
        blog_post_id=blog_post.id,
        synthesis_metadata_json={
            "source_count": len(articles),
            "sources": source_citations,
            "generated_at": datetime.utcnow().isoformat()
        }
    )

    db.add(synthesis_record)
    db.commit()
    db.refresh(blog_post)
    db.refresh(synthesis_record)

    return {
        "synthesis_id": synthesis_record.id,
        "blog_post_id": blog_post.id,
        "title": blog_post.title,
        "slug": blog_post.slug,
        "central_focus": central_focus,
        "content_html": blog_post.content_html,
        "sources_count": len(articles),
        "selected_article_ids": article_ids,
        "status": blog_post.status,
        "provider_mode": provider_mode,
    }


def run_autopilot_synthesis(
    db: Session,
    pillar_id: Optional[int] = None,
    author_name: str = "Juan Vásquez",
    organization_id: Optional[int] = None,
    provider_mode: str = "auto",
) -> Dict[str, Any]:
    """
    Ejecuta el Autopiloto Editorial de 1-Clic:
    1. Selecciona automáticamente las mejores 3 a 4 noticias por impacto.
    2. Determina el Foco Único con IA.
    3. Sintetiza y genera el artículo consolidado en formato C-Suite.
    """
    article_ids = auto_select_best_cluster(db, pillar_id=pillar_id, organization_id=organization_id, limit=4)
    suggested = suggest_central_focus(db, article_ids, provider_mode=provider_mode)
    central_focus = suggested.get("suggested_focus", "Análisis estratégico consolidado de tendencias de alto impacto.")

    res = generate_centralized_synthesis(
        db=db,
        article_ids=article_ids,
        central_focus=central_focus,
        author_name=author_name,
        organization_id=organization_id,
        pillar_id=pillar_id,
        provider_mode=provider_mode,
    )

    return {
        **res,
        "auto_pilot": True,
        "suggested_focus": central_focus
    }
