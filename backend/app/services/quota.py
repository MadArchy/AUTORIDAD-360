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

# Mix editorial alineado a Tipos_de_Noticias_IA_Juan_Vasquez.pdf (opción A)
# (slug, name, description, keywords, target_pct)
JUAN_PILLAR_DEFS: list[tuple[str, str, str, list[str], float]] = [
    (
        "legal-tech-ia",
        "Legal Tech, IA y gobernanza",
        "Implementación de IA, legal tech, empleo y gobernanza tecnológica (núcleo del PDF).",
        [
            "legal tech",
            "gobernanza de ia",
            "gobernanza inteligencia artificial",
            "piloto inteligencia artificial",
            "chatbot empresarial",
            "adopción de ia",
            "automatización laboral",
            "selección algorítmica",
            "herramienta legal",
            "privilegio abogado",
            "error de citación",
            "inteligencia artificial para abogados",
        ],
        30.0,
    ),
    (
        "corporativo-compliance",
        "Regulación, riesgo y compliance IA",
        "Leyes, sanciones, privacidad y responsabilidad empresarial por uso de IA.",
        [
            "regulación inteligencia artificial",
            "ley inteligencia artificial",
            "compliance ia",
            "responsabilidad por ia",
            "demanda inteligencia artificial",
            "sanción ftc",
            "privacidad de datos",
            "ciberseguridad ia",
            "gdpr",
            "datos personales",
            "litigio inteligencia artificial",
            "executive order ai",
            "ai act",
        ],
        25.0,
    ),
    (
        "propiedad-intelectual",
        "PI, patentes e innovación IA",
        "Patentes, inventorship, copyright, secretos y titularidad de resultados de IA.",
        [
            "propiedad intelectual",
            "patente inteligencia artificial",
            "inventorship",
            "inventor ia",
            "copyright ia",
            "secreto empresarial",
            "marca registrada",
            "licencia de ia",
            "uspto",
            "wipo",
            "titularidad de resultados",
        ],
        20.0,
    ),
    (
        "comercio-mx-us",
        "México–EE.UU. (IA y operaciones)",
        "Operación binacional, datos cross-border, nearshoring tech y cumplimiento MX–US.",
        [
            "méxico estados unidos",
            "mx-us",
            "cross-border",
            "datos transfronterizos",
            "nearshoring",
            "t-mec",
            "usmca",
            "binacional",
            "comercio mx",
            "nearshoring tech",
        ],
        15.0,
    ),
    (
        "emprendimiento",
        "Inversión y negocios en IA",
        "Fondos, M&A, data centers, presupuestos corporativos y expansión en IA.",
        [
            "inversión en ia",
            "fondo inteligencia artificial",
            "adquisición ia",
            "data center",
            "presupuesto corporativo ia",
            "venture capital ia",
            "startup ia",
            "m&a inteligencia artificial",
            "alianza tecnológica",
        ],
        10.0,
    ),
]


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


def _article_haystack(article: NewsArticle) -> str:
    data = article.classification_json or {}
    scout = data.get("scout") if isinstance(data.get("scout"), dict) else {}
    article_pillars = _article_pillars(article)
    return " ".join(
        [
            article.title or "",
            article.summary or "",
            article.excerpt or "",
            " ".join(article_pillars),
            (article.category.name if article.category else ""),
            str(scout.get("news_type_slug") or ""),
            str(scout.get("news_type_name") or ""),
            str(data.get("pillar_slug") or ""),
        ]
    ).lower()


def _pillar_match_score(article: NewsArticle, pillar: ContentPillar) -> float:
    """Puntaje de afinidad: tipología/slug explícito > keywords largas > hits cortos."""
    haystack = _article_haystack(article)
    article_pillars = _article_pillars(article)
    slug = pillar.slug.lower()
    name = pillar.name.lower()
    score = 0.0

    # Tipología scout → pillar_slug guardado en classification
    data = article.classification_json or {}
    scout = data.get("scout") if isinstance(data.get("scout"), dict) else {}
    explicit = str(data.get("pillar_slug") or scout.get("pillar_slug") or "").lower()
    if explicit and explicit == slug:
        score += 100.0

    if slug in article_pillars or name in article_pillars:
        score += 40.0

    keywords = [str(k).lower().strip() for k in (pillar.keywords_json or []) if str(k).strip()]
    # Preferir keywords más largas / específicas
    keywords_sorted = sorted(keywords, key=len, reverse=True)
    for kw in keywords_sorted:
        if len(kw) < 3:
            continue
        if kw in haystack:
            score += 5.0 + min(len(kw), 40) * 0.35
    return score


def _match_pillar(article: NewsArticle, pillar: ContentPillar) -> bool:
    return _pillar_match_score(article, pillar) >= 5.0


def match_best_pillar(
    article: NewsArticle,
    pillars: list[ContentPillar],
    boosts: dict[str, float] | None = None,
) -> tuple[str | None, float]:
    """Mejor pilar por score de keywords/tipología; desempate por boost de cuota."""
    boosts = boosts or {}
    best_slug: str | None = None
    best_key = -1.0
    best_boost = 1.0
    for pillar in pillars:
        affinity = _pillar_match_score(article, pillar)
        if affinity < 5.0:
            continue
        b = float(boosts.get(pillar.slug.lower(), 1.0))
        # Afinidad manda; boost de déficit desempata
        key = affinity + b * 10.0
        if key > best_key:
            best_key = key
            best_slug = pillar.slug
            best_boost = b
    return best_slug, best_boost


def _article_pillars(article: NewsArticle) -> list[str]:
    data = article.classification_json or {}
    raw = data.get("pillars") or []
    return [str(p).strip().lower() for p in raw if str(p).strip()]


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
    if not pillars:
        return base_score, 1.0, None

    matched, boost = match_best_pillar(article, pillars, boosts)
    if not matched:
        return base_score, 1.0, None
    return round(base_score * boost, 2), boost, matched


def apply_pdf_pillar_mix(db: Session, profile: ProfessionalProfile) -> ProfessionalProfile:
    """Actualiza copy, keywords y % de pilares al mix PDF (perfil existente)."""
    validate_percentages_sum([p[4] for p in JUAN_PILLAR_DEFS], "editorial pillars")
    by_slug = {p.slug: p for p in profile.pillars}
    for slug, name, desc, keywords, target in JUAN_PILLAR_DEFS:
        pillar = by_slug.get(slug)
        if not pillar:
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
            by_slug[slug] = pillar
        else:
            pillar.name = name
            pillar.description = desc
            pillar.keywords_json = keywords
            pillar.is_active = True

        row = (
            db.query(EditorialPercentage)
            .filter_by(profile_id=profile.id, pillar_id=pillar.id, period="monthly")
            .first()
        )
        if row:
            row.target_pct = target
        else:
            db.add(
                EditorialPercentage(
                    profile_id=profile.id,
                    pillar_id=pillar.id,
                    target_pct=target,
                    period="monthly",
                )
            )

    # Bio alineada al enfoque PDF
    if profile.slug == "juan-vasquez":
        profile.bio = (
            "Perfil piloto de Autoridad 360. Contenido editorial alineado a "
            "IA, gobernanza, Propiedad Intelectual y el eje México–Estados Unidos."
        )
        profile.title = "Abogado / Consultor — IA, gobernanza y posicionamiento MX-US"

    log_audit(
        db,
        entity_type="professional_profile",
        entity_id=profile.id,
        action="pillar_mix_pdf",
        actor="system",
        output_summary="Mix editorial PDF Juan: 30/25/20/15/10",
        metadata_json={"slug": profile.slug, "mix": "pdf-option-a"},
    )
    db.commit()
    return get_active_profile(db, slug=profile.slug, organization_id=profile.organization_id) or profile


def suggest_quota_articles(
    db: Session,
    profile: ProfessionalProfile,
    *,
    limit: int = 5,
    days: int = 30,
) -> list[dict]:
    """Noticias priorizadas por pilares en déficit (collected+verified)."""
    from datetime import timedelta

    from app.services.scoring import RANKABLE_STATUSES

    snapshot = compute_quota_snapshot(db, profile)
    boosts = pillar_boost_map(snapshot)
    pillars = [p for p in profile.pillars if p.is_active]
    pillar_names = {p.slug: p.name for p in pillars}
    deficit_slugs = {
        p.pillar_slug
        for p in snapshot.pillars
        if p.deficit_pct >= MIN_DEFICIT_PCT
    }
    cutoff = datetime.utcnow() - timedelta(days=days)
    filters = [
        NewsArticle.status.in_(RANKABLE_STATUSES),
        NewsArticle.created_at >= cutoff,
    ]
    if profile.organization_id is not None:
        filters.append(NewsArticle.organization_id == profile.organization_id)
    articles = db.query(NewsArticle).filter(*filters).all()

    ranked: list[tuple[float, float, str | None, NewsArticle]] = []
    for article in articles:
        base = float(article.total_score or 0) or 50.0
        adjusted, boost, matched = apply_quota_boost(article, base, boosts, pillars)
        priority = adjusted
        if matched and matched in deficit_slugs:
            priority += 15.0
        elif matched:
            priority += 8.0
        elif boost > 1.0:
            priority += 5.0
        ranked.append((priority, boost, matched, article))

    ranked.sort(key=lambda x: x[0], reverse=True)
    out: list[dict] = []
    for priority, boost, matched, article in ranked[: max(1, limit)]:
        out.append(
            {
                "article_id": article.id,
                "title": article.title,
                "summary": article.summary or article.excerpt,
                "source_name": article.source_name,
                "status": article.status,
                "total_score": round(priority, 2),
                "quota_boost": boost,
                "matched_pillar": matched,
                "matched_pillar_name": pillar_names.get(matched) if matched else None,
                "quota_priority": bool(matched and matched in deficit_slugs),
            }
        )
    return out


def seed_juan_profile(db: Session) -> ProfessionalProfile:
    """Perfil piloto Juan Vásquez con pilares y porcentajes de arranque."""
    from app.services.juan_persona import DEFAULT_JUAN_PERSONA, persist_persona_to_profile
    from app.services.news_typologies import default_search_themes

    existing = db.query(ProfessionalProfile).filter_by(slug="juan-vasquez").first()
    if existing:
        dirty = False
        if not existing.search_themes_json:
            existing.search_themes_json = default_search_themes()
            dirty = True
        if not getattr(existing, "persona_json", None):
            persist_persona_to_profile(db, existing)
            dirty = True
        # Enriquecer título/bio sin pisar ediciones muy distintas
        if not existing.title or "piloto" in (existing.title or "").lower():
            existing.title = DEFAULT_JUAN_PERSONA["title"]
            dirty = True
        if dirty:
            db.commit()
        # No reescribe % en cada seed; usar apply_pdf_pillar_mix / endpoint rebalance
        return get_active_profile(db, slug="juan-vasquez") or existing

    profile = ProfessionalProfile(
        slug="juan-vasquez",
        full_name="Juan J. Vásquez",
        title=DEFAULT_JUAN_PERSONA["title"],
        bio=(
            "Abogado de patentes e IP y counsel de AI Readiness & Governance. "
            "Member en Whitaker Chalk (Fort Worth/Dallas). Formación en ingeniería "
            "eléctrica y ciberseguridad (USAF); JD St. Mary's; Texas Bar 24088582; "
            "USPTO. Práctica en prosecution, FTO, AI/ML, privacy y governance "
            "para GC, boards, CISOs y compliance. Thought leadership MX–US."
        ),
        services_json=[
            "AI Readiness Assessment",
            "Governance program build-out",
            "Patent prosecution & FTO",
            "AI + IP / inventorship counsel",
            "Estrategia de posicionamiento profesional MX–US",
        ],
        audiences_json=[
            "General counsel",
            "CEOs & boards",
            "CISOs",
            "Compliance officers",
            "Empresarios MX con operaciones en US",
            "Founders / legal tech",
        ],
        markets_json={"primary": ["MX", "US"]},
        persona_json=dict(DEFAULT_JUAN_PERSONA),
        is_active=True,
    )
    db.add(profile)
    db.flush()

    for slug, name, desc, keywords, target in JUAN_PILLAR_DEFS:
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

    profile.search_themes_json = default_search_themes()

    validate_percentages_sum([p[4] for p in JUAN_PILLAR_DEFS], "editorial pillars")
    validate_percentages_sum([55.0, 45.0], "markets")

    log_audit(
        db,
        entity_type="professional_profile",
        entity_id=0,
        action="seeded",
        actor="system",
        output_summary="Seed perfil Juan Vásquez + pilares + porcentajes PDF",
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
