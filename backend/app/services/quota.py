"""Corrección de cuota editorial — determinística, sin prompts.

Si un pilar va por debajo de su meta mensual, sube la prioridad
de noticias alineadas a ese pilar en el cálculo del Top 10.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session, joinedload

from app.models import (
    BlogPost,
    ContentPillar,
    EditorialPercentage,
    MarketPercentage,
    NewsArticle,
    ProfessionalProfile,
)
from app.services.audit import log_audit

# Qué tanto puede empujar un déficit de cuota el score final (0.5 = hasta +50%)
QUOTA_BOOST_FACTOR = 0.5
# Déficit mínimo (%) para aplicar boost (evita ruido)
MIN_DEFICIT_PCT = 2.0


@dataclass
class PillarQuotaStatus:
    pillar_id: int
    pillar_slug: str
    pillar_name: str
    target_pct: float
    actual_pct: float
    deficit_pct: float
    count: int


@dataclass
class QuotaSnapshot:
    profile_id: int
    profile_slug: str
    month_total: int
    pillars: list[PillarQuotaStatus]
    markets: list[dict]


def _month_bounds(now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.utcnow()
    start = datetime(now.year, now.month, 1)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1)
    else:
        end = datetime(now.year, now.month + 1, 1)
    return start, end


def validate_percentages_sum(values: Iterable[float], label: str = "percentages") -> None:
    total = round(sum(float(v) for v in values), 2)
    if abs(total - 100.0) > 0.01:
        raise ValueError(f"{label} must sum to 100, got {total}")


def get_active_profile(
    db: Session,
    slug: str | None = None,
    organization_id: int | None = None,
) -> ProfessionalProfile | None:
    query = db.query(ProfessionalProfile).filter(ProfessionalProfile.is_active.is_(True))
    if organization_id is not None:
        query = query.filter(ProfessionalProfile.organization_id == organization_id)
    if slug:
        query = query.filter(ProfessionalProfile.slug == slug)
    return (
        query.options(
            joinedload(ProfessionalProfile.pillars),
            joinedload(ProfessionalProfile.editorial_percentages).joinedload(
                EditorialPercentage.pillar
            ),
            joinedload(ProfessionalProfile.market_percentages),
        )
        .order_by(ProfessionalProfile.id.asc())
        .first()
    )


def _article_pillars(article: NewsArticle) -> list[str]:
    data = article.classification_json or {}
    raw = data.get("pillars") or []
    return [str(p).strip().lower() for p in raw if str(p).strip()]


def _match_pillar(article: NewsArticle, pillar: ContentPillar) -> bool:
    article_pillars = _article_pillars(article)
    slug = pillar.slug.lower()
    name = pillar.name.lower()
    if slug in article_pillars or name in article_pillars:
        return True
    keywords = [str(k).lower() for k in (pillar.keywords_json or [])]
    haystack = " ".join(
        [
            article.title or "",
            article.summary or "",
            " ".join(article_pillars),
            (article.category.name if article.category else ""),
        ]
    ).lower()
    return any(k in haystack for k in keywords if k)


def compute_quota_snapshot(db: Session, profile: ProfessionalProfile) -> QuotaSnapshot:
    start, end = _month_bounds()
    post_filters = [
        BlogPost.status.in_(["approved", "published"]),
        BlogPost.created_at >= start,
        BlogPost.created_at < end,
    ]
    if profile.organization_id is not None:
        post_filters.append(BlogPost.organization_id == profile.organization_id)
    posts = db.query(BlogPost).filter(*post_filters).all()
    articles_by_id: dict[int, NewsArticle] = {}
    if posts:
        ids = [p.article_id for p in posts]
        for a in db.query(NewsArticle).filter(NewsArticle.id.in_(ids)).all():
            articles_by_id[a.id] = a

    month_total = len(posts)
    pillars_status: list[PillarQuotaStatus] = []

    for pct in profile.editorial_percentages:
        pillar = pct.pillar
        if not pillar or not pillar.is_active:
            continue
        count = 0
        for post in posts:
            article = articles_by_id.get(post.article_id)
            if article and _match_pillar(article, pillar):
                count += 1
        actual = (count / month_total * 100.0) if month_total > 0 else 0.0
        target = float(pct.target_pct)
        deficit = max(0.0, target - actual)
        pillars_status.append(
            PillarQuotaStatus(
                pillar_id=pillar.id,
                pillar_slug=pillar.slug,
                pillar_name=pillar.name,
                target_pct=target,
                actual_pct=round(actual, 2),
                deficit_pct=round(deficit, 2),
                count=count,
            )
        )

    markets = [
        {
            "market_code": m.market_code,
            "target_pct": float(m.target_pct),
        }
        for m in profile.market_percentages
    ]

    return QuotaSnapshot(
        profile_id=profile.id,
        profile_slug=profile.slug,
        month_total=month_total,
        pillars=pillars_status,
        markets=markets,
    )


def pillar_boost_map(snapshot: QuotaSnapshot) -> dict[str, float]:
    """slug → multiplicador (1.0 = sin boost, 1.5 = máximo con factor 0.5)."""
    boosts: dict[str, float] = {}
    for p in snapshot.pillars:
        if p.deficit_pct < MIN_DEFICIT_PCT:
            boosts[p.pillar_slug.lower()] = 1.0
            continue
        # deficit 20% con factor 0.5 → boost 1.10
        multiplier = 1.0 + (p.deficit_pct / 100.0) * QUOTA_BOOST_FACTOR
        boosts[p.pillar_slug.lower()] = round(multiplier, 4)
    return boosts


def apply_quota_boost(
    article: NewsArticle,
    base_score: float,
    boosts: dict[str, float],
    pillars: list[ContentPillar],
) -> tuple[float, float, str | None]:
    """
    Returns (adjusted_score, boost_applied, matched_pillar_slug).
    Usa el mayor boost entre pilares que matchean (el más deficitario).
    """
    if not boosts or not pillars:
        return base_score, 1.0, None

    best_boost = 1.0
    best_slug: str | None = None
    for pillar in pillars:
        if not _match_pillar(article, pillar):
            continue
        b = boosts.get(pillar.slug.lower(), 1.0)
        if b > best_boost:
            best_boost = b
            best_slug = pillar.slug

    return round(base_score * best_boost, 2), best_boost, best_slug


def seed_juan_profile(db: Session) -> ProfessionalProfile:
    """Perfil piloto Juan Vásquez con pilares y porcentajes de arranque."""
    existing = db.query(ProfessionalProfile).filter_by(slug="juan-vasquez").first()
    if existing:
        return existing

    profile = ProfessionalProfile(
        slug="juan-vasquez",
        full_name="Juan Vásquez",
        title="Abogado / Consultor — posicionamiento MX-US",
        bio=(
            "Perfil piloto de Autoridad 360. Contenido editorial alineado a "
            "derecho corporativo, comercio MX-US, compliance e IA legal."
        ),
        services_json=[
            "Asesoría corporativa transfronteriza",
            "Compliance y regulación",
            "Estrategia de posicionamiento profesional",
        ],
        audiences_json=[
            "Empresarios MX con operaciones en US",
            "Founders / legal tech",
            "Directores de cumplimiento",
        ],
        markets_json={"primary": ["MX", "US"]},
        is_active=True,
    )
    db.add(profile)
    db.flush()

    pillar_defs = [
        (
            "corporativo-compliance",
            "Corporativo y Compliance",
            "Derecho societario, cumplimiento y regulación",
            ["corporativo", "compliance", "regulación", "sociedades", "sec", "cnbv", "gobierno corporativo", "aml"],
            30.0,
        ),
        (
            "comercio-mx-us",
            "Comercio e Inmigración MX-US",
            "Trade, visas y operaciones transfronterizas",
            ["comercio", "inmigración", "visa", "trade", "mx-us", "uscis", "t-mec", "usmca", "arancel", "nearshoring", "aduana"],
            25.0,
        ),
        (
            "legal-tech-ia",
            "Legal Tech e IA",
            "Tecnología legal e inteligencia artificial aplicada",
            ["ia", "inteligencia artificial", "legal tech", "tecnología", "privacidad", "datos personales", "gdpr"],
            20.0,
        ),
        (
            "propiedad-intelectual",
            "Propiedad Intelectual",
            "Marcas, patentes y activos intangibles",
            ["propiedad intelectual", "marca", "patente", "wipo", "copyright", "marca registrada"],
            15.0,
        ),
        (
            "emprendimiento",
            "Emprendimiento y Negocios",
            "Startups, finanzas y estrategia de negocio",
            ["emprendimiento", "startup", "negocios", "finanzas", "inversión", "pyme"],
            10.0,
        ),
    ]

    for slug, name, desc, keywords, target in pillar_defs:
        pillar = ContentPillar(
            profile_id=profile.id,
            slug=slug,
            name=name,
            description=desc,
            keywords_json=keywords,
            is_active=True,
        )
        db.add(pillar)
        db.flush()
        db.add(
            EditorialPercentage(
                profile_id=profile.id,
                pillar_id=pillar.id,
                target_pct=target,
                period="monthly",
            )
        )

    db.add(MarketPercentage(profile_id=profile.id, market_code="MX", target_pct=55.0))
    db.add(MarketPercentage(profile_id=profile.id, market_code="US", target_pct=45.0))

    validate_percentages_sum([p[4] for p in pillar_defs], "editorial pillars")
    validate_percentages_sum([55.0, 45.0], "markets")

    log_audit(
        db,
        entity_type="professional_profile",
        entity_id=0,
        action="seeded",
        actor="system",
        output_summary="Seed perfil Juan Vásquez + pilares + porcentajes",
        metadata_json={"slug": "juan-vasquez"},
    )
    db.commit()

    loaded = get_active_profile(db, slug="juan-vasquez")
    if loaded:
        log_audit(
            db,
            entity_type="professional_profile",
            entity_id=loaded.id,
            action="seeded_complete",
            actor="system",
            metadata_json={"slug": loaded.slug},
        )
        db.commit()
        return loaded
    return profile
