import math
import logging
from datetime import datetime
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.news import NewsArticle

logger = logging.getLogger(__name__)

# Category Relevance Weights (25%)
CATEGORY_RELEVANCE_WEIGHTS: Dict[str, float] = {
    "ia_y_transformacion_digital": 1.0,
    "derecho_y_regulacion_tech": 1.0,
    "ciberseguridad_y_privacidad": 0.9,
    "propiedad_intelectual_y_datos": 0.95,
    "tendencias_globales_mercado_mx_us": 0.85,
    "negocios_y_estratega_empresarial": 0.8,
    "fintech_y_economia_digital": 0.8,
    "innovacion_y_startups": 0.75,
    "politica_publica_y_tech": 0.75,
    "liderazgo_y_gestion": 0.7,
    "casos_de_estudio_e_industria": 0.7
}

# Source Confiability Tier Weights (15%)
SOURCE_RELIABILITY_WEIGHTS: Dict[str, float] = {
    "MIT Technology Review": 1.0,
    "Harvard Business Review": 1.0,
    "Law.com Tech": 0.95,
    "ABA Journal Tech": 0.95,
    "El Economista MX": 0.9,
    "El Financiero Tech": 0.9,
    "McKinsey Insights": 0.9,
    "TechCrunch AI": 0.85,
    "TechCrunch Startups": 0.85,
    "Krebs on Security": 0.85,
    "Dark Reading": 0.85,
    "CoinDesk": 0.8,
    "IPWatchdog": 0.9
}

IMPACT_KEYWORDS = ["ai", "regulation", "law", "billion", "lawsuit", "security", "breach", "court", "patent", "breakthrough", "transformación", "regulacion", "ciberseguridad"]
MX_US_KEYWORDS = ["mexico", "méxico", "us", "usa", "united states", "border", "nearshoring", "usmca", "tmec", "cross-border", "sec", "fda"]
CONVERSION_KEYWORDS = ["consulting", "legal", "compliance", "governance", "advisory", "inteligencia artificial", "abogado", "asesoría", "estrategia"]

def calculate_article_score(article: NewsArticle, quota_boosts: Dict[str, float] = None) -> float:
    """
    Calculates deterministic Top 10 score for an article based on the 7 roadmap weights:
    - Relevance (25%) + Dynamic Quota Correction Boost (Fase 2)
    - Impact (20%)
    - Reliability (15%)
    - Recency (15%)
    - Content potential (10%)
    - MX-US Relevance (10%)
    - Conversion potential (5%)
    """
    text_content = f"{article.title} {article.content_full or ''}".lower()

    # Dynamic Quota Correction Boost from ProfileService
    quota_multiplier = 1.0
    if quota_boosts and article.category in quota_boosts:
        quota_multiplier = quota_boosts[article.category]

    # 1. Relevance (25%) * Dynamic Quota Boost
    base_rel = CATEGORY_RELEVANCE_WEIGHTS.get(article.category, 0.6)
    rel_score = (base_rel * quota_multiplier) * 0.25

    # 2. Impact (20%)
    impact_matches = sum(1 for kw in IMPACT_KEYWORDS if kw in text_content)
    impact_score = min(impact_matches / 4.0, 1.0) * 0.20

    # 3. Reliability (15%)
    rel_source_score = SOURCE_RELIABILITY_WEIGHTS.get(article.source_name, 0.75) * 0.15

    # 4. Recency (15%) - Exponential decay
    recency_score = 0.5 * 0.15
    if article.published_at:
        hours_old = max((datetime.utcnow() - article.published_at).total_seconds() / 3600.0, 0.0)
        decay = math.exp(-hours_old / 72.0) # 3-day half decay
        recency_score = decay * 0.15

    # 5. Content Potential (10%)
    content_len = len(article.content_full or "")
    potential_score = min(content_len / 3000.0, 1.0) * 0.10

    # 6. MX-US Relevance (10%)
    mx_us_matches = sum(1 for kw in MX_US_KEYWORDS if kw in text_content)
    mx_us_score = min(mx_us_matches / 2.0, 1.0) * 0.10

    # 7. Conversion Potential (5%)
    conv_matches = sum(1 for kw in CONVERSION_KEYWORDS if kw in text_content)
    conv_score = min(conv_matches / 2.0, 1.0) * 0.05

    total = rel_score + impact_score + rel_source_score + recency_score + potential_score + mx_us_score + conv_score
    return round(total * 100.0, 2)

class Top10EngineService:
    def __init__(self, db: Session):
        self.db = db

    def recalculate_all_scores(self) -> int:
        """Calculates and updates top10_score deterministically for all articles using dynamic quota boosts."""
        from app.services.profile_service import ProfileService
        profile_service = ProfileService(self.db)
        stats = profile_service.get_profile_with_quota_stats()
        quota_boosts = stats.get("quota_boosts", {})

        articles = self.db.query(NewsArticle).all()
        count = 0
        for article in articles:
            article.top10_score = calculate_article_score(article, quota_boosts)
            count += 1
        self.db.commit()
        return count

    def get_top_10_articles(self, limit: int = 10) -> List[NewsArticle]:
        """Returns top N articles sorted deterministically by top10_score descending."""
        return self.db.query(NewsArticle).order_by(
            NewsArticle.top10_score.desc(),
            NewsArticle.published_at.desc()
        ).limit(limit).all()

