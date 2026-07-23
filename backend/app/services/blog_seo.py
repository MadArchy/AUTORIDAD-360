"""Campos SEO públicos del blog (autor, revisor, categorías)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.editorial import BlogPost, NewsArticle, NewsCategory


def categories_for_article(db: Session, article: NewsArticle | None) -> list[str]:
    if not article or not article.category_id:
        return []
    cat = db.query(NewsCategory).filter(NewsCategory.id == article.category_id).first()
    if not cat:
        return []
    name = (cat.name or cat.slug or "").strip()
    return [name] if name else []


def apply_blog_seo_defaults(
    db: Session,
    post: BlogPost,
    *,
    article: NewsArticle | None = None,
    reviewer: str | None = None,
) -> None:
    if article is None:
        article = db.query(NewsArticle).filter(NewsArticle.id == post.article_id).first()
    if not post.author_name:
        post.author_name = (settings.client_name or "Juan Vásquez").strip()
    if reviewer and not post.reviewer_name:
        post.reviewer_name = reviewer.strip()[:256]
    elif not post.reviewer_name and post.approved_by:
        post.reviewer_name = post.approved_by
    cats = categories_for_article(db, article)
    if cats and not post.categories_json:
        post.categories_json = cats
    if not post.seo_description:
        raw = (article.summary if article else None) or post.source_citation or post.title
        plain = " ".join(str(raw).replace("<", " ").split())
        post.seo_description = plain[:300]
