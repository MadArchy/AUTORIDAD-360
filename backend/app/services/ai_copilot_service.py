"""Servicio Copiloto de IA — Interacción y refinamiento en tiempo real de noticias y artículos."""

from __future__ import annotations

from typing import Any
from sqlalchemy.orm import Session

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
