"""Servicio Copiloto de IA — Interacción y refinamiento en tiempo real de noticias y artículos."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import ContentPiece
from app.models.editorial import NewsArticle, BlogPost
from app.services.llm import _call_model
from app.services.audit import log_audit


def refine_article_content(
    db: Session,
    article_id: int,
    instruction: str,
    target_field: str = "full_text",
    provider_mode: str = "auto",
) -> dict[str, Any]:
    """
    Refina o interactúa con el contenido de una noticia/artículo mediante un prompt de usuario.
    Permite cambiar tono, corregir estilo, generar resúmenes, adaptar disclaimers, etc.
    """
    article = db.query(NewsArticle).filter_by(id=article_id).first()
    if not article:
        raise ValueError(f"Artículo con ID {article_id} no encontrado")

    current_text = getattr(article, target_field, "") or article.full_text or article.summary or ""

    prompt = f"""
    Eres el Copiloto Editorial Senior de Autoridad 360.
    Tu objetivo es iterar, perfeccionar o adaptar el contenido de la siguiente noticia según la instrucción del usuario.

    TÍTULO: {article.title}
    FUENTE: {article.source_name} ({article.url})
    CAMPO OBJETIVO ({target_field}):
    ---
    {current_text}
    ---

    INSTRUCCIÓN DEL USUARIO:
    "{instruction}"

    Reglas obligatorias:
    1. Si el usuario pide reescribir o adaptar, devuelve la versión actualizada del texto lista para publicarse.
    2. Mantén la precisión de los hechos y la veracidad.
    3. Responde de forma clara y directa en idioma español a menos que el usuario especifique otro idioma.
    """

    new_content, model_used = _call_model(
        db, "agent_critique", prompt, provider_mode=provider_mode
    )

    log_audit(
        db,
        entity_type="news_article",
        entity_id=article.id,
        action="copilot_refine",
        actor="user_copilot",
        output_summary=f"Refinado campo {target_field} con instrucción: {instruction[:60]}",
    )

    return {
        "article_id": article.id,
        "target_field": target_field,
        "original_content": current_text,
        "refined_content": new_content,
        "model_used": model_used,
        "instruction": instruction,
    }


def refine_blog_post_content(
    db: Session,
    post_id: int,
    instruction: str,
    target_field: str = "body_markdown",
    provider_mode: str = "auto",
) -> dict[str, Any]:
    """
    Refina o interactúa con el borrador de un post de blog.
    """
    post = db.query(BlogPost).filter_by(id=post_id).first()
    if not post:
        raise ValueError(f"Post de blog con ID {post_id} no encontrado")

    current_text = getattr(post, target_field, "") or post.body_markdown or post.summary or ""

    prompt = f"""
    Eres el Copiloto Editorial Senior de Autoridad 360.
    Ajusta el siguiente post de blog respetando el contexto y aplicando la instrucción del usuario.

    TÍTULO ACTUAL: {post.title}
    CONTENIDO ACTUAL ({target_field}):
    ---
    {current_text}
    ---

    INSTRUCCIÓN DEL USUARIO:
    "{instruction}"

    Reglas:
    - Retorna la nueva versión mejorada del contenido en formato markdown limpio.
    - Preserva la estructura SEO y tono profesional.
    """

    new_content, model_used = _call_model(
        db, "blog_article", prompt, provider_mode=provider_mode
    )

    log_audit(
        db,
        entity_type="blog_post",
        entity_id=post.id,
        action="copilot_refine_blog",
        actor="user_copilot",
        output_summary=f"Refinado post {post.id} ({target_field}) con: {instruction[:60]}",
    )

    return {
        "post_id": post.id,
        "target_field": target_field,
        "original_content": current_text,
        "refined_content": new_content,
        "model_used": model_used,
        "instruction": instruction,
    }


def refine_content_piece(
    db: Session,
    piece_id: int,
    instruction: str,
    *,
    organization_id: int | None = None,
    draft_text: str | None = None,
    provider_mode: str = "auto",
) -> dict[str, Any]:
    """
    Refina una pieza de formato (LinkedIn, carrusel, etc.).
    Si se pasa draft_text, itera sobre el borrador del editor (sin persistir).
    """
    q = db.query(ContentPiece).filter(ContentPiece.id == piece_id)
    if organization_id is not None:
        q = q.filter(ContentPiece.organization_id == organization_id)
    piece = q.first()
    if not piece:
        raise ValueError(f"Pieza con ID {piece_id} no encontrada")

    if draft_text is not None and str(draft_text).strip():
        current_text = str(draft_text)
    elif piece.format_type == "carousel" and piece.body_json:
        current_text = json.dumps(piece.body_json, ensure_ascii=False, indent=2)
    else:
        current_text = piece.body_text or ""

    format_hint = {
        "linkedin": "post profesional para LinkedIn",
        "video_script": "guion de video / teleprompter",
        "carousel": "carrusel (JSON de slides con title/content)",
        "newsletter": "edición de newsletter",
    }.get(piece.format_type, piece.format_type)

    prompt = f"""
    Eres el Copiloto Editorial Senior de Autoridad 360.
    Mejora la siguiente pieza de formato ({format_hint}) según la instrucción del usuario.

    TÍTULO DE LA PIEZA: {piece.title}
    FORMATO: {piece.format_type}
    CONTENIDO ACTUAL:
    ---
    {current_text}
    ---

    INSTRUCCIÓN DEL USUARIO:
    "{instruction}"

    Reglas:
    1. Devuelve SOLO el contenido actualizado listo para pegar (sin preámbulos).
    2. Si el formato es carrusel y el input es JSON, responde con JSON válido de slides.
    3. Mantén hechos y tono profesional autoritativo; sin hype vacío.
    4. Idioma: el mismo del contenido original salvo que la instrucción pida otro.
    """

    new_content, model_used = _call_model(
        db, "agent_critique", prompt, provider_mode=provider_mode
    )

    log_audit(
        db,
        entity_type="content_piece",
        entity_id=piece.id,
        action="copilot_refine_piece",
        actor="user_copilot",
        output_summary=f"Refinado {piece.format_type}: {instruction[:60]}",
    )

    return {
        "piece_id": piece.id,
        "format_type": piece.format_type,
        "original_content": current_text,
        "refined_content": new_content,
        "model_used": model_used,
        "instruction": instruction,
    }
