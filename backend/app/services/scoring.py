"""Scoring determinístico — el backend calcula, no el modelo.

Fase 2: el total se ajusta con corrección de cuota por pilares deficitarios.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import NewsArticle
from app.services.editorial_filters import editorial_score_multiplier, is_editorial_noise
from app.services.quota import (
    apply_quota_boost,
    compute_quota_snapshot,
    get_active_profile,
    pillar_boost_map,
)

WEIGHTS = {
    "relevance": 0.25,
    "impact": 0.20,
    "reliability": 0.15,
    "freshness": 0.15,
    "content_potential": 0.10,
    "mx_us_relevance": 0.10,
    "conversion": 0.05,
}


@dataclass
class ScoredArticle:
    article: NewsArticle
    total_score: float
    base_score: float = 0.0
    quota_boost: float = 1.0
    matched_pillar: str | None = None


def _freshness_bonus(published_at: datetime | None) -> float:
    if not published_at:
        return 50.0
    age = datetime.utcnow() - published_at
    if age <= timedelta(days=1):
        return 100.0
    if age <= timedelta(days=3):
        return 85.0
    if age <= timedelta(days=7):
        return 70.0
    if age <= timedelta(days=14):
        return 50.0
    return 30.0


def compute_base_score(article: NewsArticle) -> float:
    freshness = float(article.score_freshness or _freshness_bonus(article.published_at))
    components = {
        "relevance": float(article.score_relevance or 0),
        "impact": float(article.score_impact or 0),
        "reliability": float(article.score_reliability or 0),
        "freshness": freshness,
        "content_potential": float(article.score_content_potential or 0),
        "mx_us_relevance": float(article.score_mx_us_relevance or 0),
        "conversion": float(article.score_conversion or 0),
    }
    total = sum(components[k] * WEIGHTS[k] for k in WEIGHTS)
    mult = editorial_score_multiplier(
        article.title,
        article.summary,
        article.excerpt,
        (article.full_text or "")[:800],
    )
    total = total * mult
    article.score_freshness = freshness
    return round(min(100.0, max(0.0, total)), 2)


def compute_total_score(article: NewsArticle) -> float:
    """Compat: guarda score base sin cuota (la cuota se aplica en get_top10)."""
    article.total_score = compute_base_score(article)
    return article.total_score


def score_verified_articles(db: Session, organization_id: int | None = None) -> int:
    query = db.query(NewsArticle).filter(NewsArticle.status == "verified")
    if organization_id is not None:
        query = query.filter(NewsArticle.organization_id == organization_id)
    articles = query.all()
    for article in articles:
        compute_total_score(article)
    db.commit()
    return len(articles)


def get_top10(
    db: Session,
    days: int = 7,
    organization_id: int | None = None,
) -> list[ScoredArticle]:
    score_verified_articles(db, organization_id=organization_id)
    cutoff = datetime.utcnow() - timedelta(days=days)
    filters = [
        NewsArticle.status == "verified",
        NewsArticle.total_score.isnot(None),
        NewsArticle.created_at >= cutoff,
    ]
    if organization_id is not None:
        filters.append(NewsArticle.organization_id == organization_id)
    articles = db.query(NewsArticle).filter(*filters).all()

    profile = get_active_profile(db, organization_id=organization_id)
    boosts: dict[str, float] = {}
    pillars = []
    if profile:
        snapshot = compute_quota_snapshot(db, profile)
        boosts = pillar_boost_map(snapshot)
        pillars = [p for p in profile.pillars if p.is_active]

    scored: list[ScoredArticle] = []
    for article in articles:
        if is_editorial_noise(article.title, article.summary or article.excerpt):
            continue
        mult = editorial_score_multiplier(
            article.title,
            article.summary,
            article.excerpt,
        )
        if mult < 0.55:
            continue
        base = float(article.total_score or compute_base_score(article))
        adjusted, boost, matched = apply_quota_boost(article, base, boosts, pillars)
        adjusted = min(100.0, round(adjusted, 2))
        scored.append(
            ScoredArticle(
                article=article,
                total_score=adjusted,
                base_score=base,
                quota_boost=boost,
                matched_pillar=matched,
            )
        )

    scored.sort(key=lambda s: s.total_score, reverse=True)
    return scored[:10]
