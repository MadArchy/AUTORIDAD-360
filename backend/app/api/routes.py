from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import (
    BlogPost,
    ContentPackage,
    ContentPiece,
    EditorialPercentage,
    MarketPercentage,
    NewsArticle,
    Organization,
    ProfessionalProfile,
    WeeklyReport,
    get_db,
)
from app.rss.collector import collect_all_feeds
from app.services.content_generation import (
    create_content_package,
    reuse_approved_piece,
    translate_piece,
)
from app.services.content_generation import _refresh_package_status
from app.services.llm import classify_article, process_unclassified, verify_article
from app.services.quota import (
    apply_pdf_pillar_mix,
    compute_quota_snapshot,
    get_active_profile,
    pillar_boost_map,
    seed_juan_profile,
    suggest_quota_articles,
    validate_percentages_sum,
)
from app.services.reports import create_blog_draft_from_article, generate_weekly_report
from app.services.scoring import get_top10, score_verified_articles
from app.tasks import (
    analyze_article_task,
    classify_and_verify,
    collect_rss_feeds,
    generate_blog_draft_task,
    generate_content_package_task,
    generate_weekly_report_task,
)
from app.services.tenant import (
    TenantContext,
    assert_same_org,
    get_tenant_context,
    require_roles,
)

router = APIRouter(prefix="/api/v1", tags=["fase1-3"])

_STAFF = (
    "agency_admin",
    "strategist",
    "writer",
    "editor",
    "legal_reviewer",
    "analyst",
    "community_manager",
)
_BLOG_STAFF = _STAFF
_PROFILE_MANAGERS = (
    "agency_admin",
    "strategist",
)


class ApprovalRequest(BaseModel):
    approved_by: str = Field(min_length=2, max_length=128)


class PieceUpdateRequest(BaseModel):
    body_text: str | None = None
    title: str | None = Field(default=None, max_length=512)
    body_json: dict | list | None = None


class RejectionRequest(BaseModel):
    approved_by: str = Field(min_length=2, max_length=128)
    reason: str = Field(min_length=5)


class BlogSeoUpdate(BaseModel):
    author_name: str | None = Field(default=None, max_length=256)
    reviewer_name: str | None = Field(default=None, max_length=256)
    categories: list[str] | None = None
    seo_description: str | None = Field(default=None, max_length=320)


class EditorialPctUpdate(BaseModel):
    pillar_slug: str
    target_pct: float = Field(ge=0, le=100)


class MarketPctUpdate(BaseModel):
    market_code: str = Field(min_length=2, max_length=8)
    target_pct: float = Field(ge=0, le=100)


class ProfilePercentagesUpdate(BaseModel):
    editorial: list[EditorialPctUpdate]
    markets: list[MarketPctUpdate]


class SearchThemeItem(BaseModel):
    id: int | None = None
    slug: str | None = None
    name: str
    monitor: str | None = None
    why: str | None = None
    editorial_angle: str | None = None
    queries: list[str] = Field(default_factory=list)
    pillar_slug: str | None = None
    is_active: bool = True


class SearchThemesUpdate(BaseModel):
    themes: list[SearchThemeItem] = Field(default_factory=list)
    reset_to_defaults: bool = False


@router.get("/health")
def health():
    from app.services.system_health import get_system_health

    return get_system_health()


@router.get("/health/ready")
def health_ready():
    """200 solo si DB+Redis OK; 503 si degradado (para probes / watchers)."""
    from fastapi.responses import JSONResponse

    from app.services.system_health import get_system_health

    payload = get_system_health()
    deps = payload.get("dependencies") or {}
    ready = bool(deps.get("database", {}).get("ok")) and bool(
        deps.get("redis", {}).get("ok")
    )
    status_code = 200 if ready else 503
    return JSONResponse(
        {**payload, "ready": ready},
        status_code=status_code,
    )


@router.get("/articles")
def list_articles(
    status: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = 50,
    max_age_hours: int | None = 36,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    from datetime import datetime, timedelta

    from sqlalchemy import or_
    from app.models import NewsCategory
    from sqlalchemy.orm import joinedload

    limit = max(1, min(int(limit or 50), 200))
    query = (
        db.query(NewsArticle)
        .options(joinedload(NewsArticle.category))
        .outerjoin(NewsCategory)
        .filter(NewsArticle.organization_id == ctx.org_id)
    )

    if status:
        query = query.filter(NewsArticle.status == status)
    if category:
        cat = category.strip()
        query = query.filter(
            or_(
                NewsCategory.name.ilike(cat),
                NewsCategory.slug.ilike(cat),
            )
        )
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(
            or_(
                NewsArticle.title.ilike(term),
                NewsArticle.summary.ilike(term),
                NewsArticle.source_name.ilike(term),
                NewsArticle.full_text.ilike(term),
                NewsCategory.name.ilike(term),
                NewsCategory.slug.ilike(term),
            )
        )

    # Por defecto solo noticias recientes (fecha de publicación real, no de importación).
    # max_age_hours=0 o negativo desactiva el filtro.
    if max_age_hours is not None and int(max_age_hours) > 0:
        cutoff = datetime.utcnow() - timedelta(hours=int(max_age_hours))
        query = query.filter(
            NewsArticle.published_at.isnot(None),
            NewsArticle.published_at >= cutoff,
        )

    articles = query.order_by(
        NewsArticle.published_at.desc(),
        NewsArticle.created_at.desc(),
    ).limit(limit).all()
    out = []
    for a in articles:
        cj = a.classification_json or {}
        scout = cj.get("scout") if isinstance(cj, dict) else None
        news_type = (
            cj.get("news_type_slug")
            or (scout or {}).get("news_type_slug")
            or None
        )
        news_type_name = (
            cj.get("news_type_name")
            or (scout or {}).get("news_type_name")
            or None
        )
        out.append(
            {
                "id": a.id,
                "title": a.title,
                "source_url": a.source_url,
                "source_name": a.source_name,
                "status": a.status,
                "total_score": float(a.total_score) if a.total_score else None,
                "summary": a.summary,
                "published_at": a.published_at.isoformat() if a.published_at else None,
                "category": a.category.name if a.category else None,
                "news_type": news_type,
                "news_type_name": news_type_name,
            }
        )
    return out


@router.get("/articles/{article_id}")
def get_article(
    article_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    article = (
        db.query(NewsArticle)
        .filter(
            NewsArticle.id == article_id,
            NewsArticle.organization_id == ctx.org_id,
        )
        .first()
    )
    if not article:
        raise HTTPException(404, "Article not found")
    return {
        "id": article.id,
        "title": article.title,
        "source_url": article.source_url,
        "source_name": article.source_name,
        "status": article.status,
        "full_text": article.full_text,
        "summary": article.summary,
        "classification_json": article.classification_json,
        "verification_json": article.verification_json,
        "total_score": float(article.total_score) if article.total_score else None,
        "scores": {
            "relevance": float(article.score_relevance or 0),
            "impact": float(article.score_impact or 0),
            "reliability": float(article.score_reliability or 0),
            "freshness": float(article.score_freshness or 0),
            "content_potential": float(article.score_content_potential or 0),
            "mx_us_relevance": float(article.score_mx_us_relevance or 0),
            "conversion": float(article.score_conversion or 0),
        },
    }


@router.post("/articles/{article_id}/classify")
def classify_one(
    article_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    article = (
        db.query(NewsArticle)
        .filter(
            NewsArticle.id == article_id,
            NewsArticle.organization_id == ctx.org_id,
        )
        .first()
    )
    if not article:
        raise HTTPException(404, "Article not found")
    return classify_article(db, article)


@router.post("/articles/{article_id}/verify")
def verify_one(
    article_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    article = (
        db.query(NewsArticle)
        .filter(
            NewsArticle.id == article_id,
            NewsArticle.organization_id == ctx.org_id,
        )
        .first()
    )
    if not article:
        raise HTTPException(404, "Article not found")
    return verify_article(db, article)


@router.post("/articles/{article_id}/reject")
def reject_article(
    article_id: int,
    body: RejectionRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    article = (
        db.query(NewsArticle)
        .filter(
            NewsArticle.id == article_id,
            NewsArticle.organization_id == ctx.org_id,
        )
        .first()
    )
    if not article:
        raise HTTPException(404, "Article not found")
    article.status = "rejected"
    article.verification_json = {
        **(article.verification_json or {}),
        "publishable": False,
        "human_rejection": {
            "by": body.approved_by,
            "reason": body.reason,
            "at": datetime.utcnow().isoformat(),
        },
    }
    db.commit()
    db.refresh(article)
    return {"id": article.id, "status": article.status}


@router.post("/articles/{article_id}/analyze")
def analyze_article_async(
    article_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_roles(ctx, *_STAFF)
    exists = (
        db.query(NewsArticle.id)
        .filter(
            NewsArticle.id == article_id,
            NewsArticle.organization_id == ctx.org_id,
        )
        .first()
    )
    if not exists:
        raise HTTPException(404, "Article not found")
    from app.services.job_runner import enqueue_job, job_to_dict

    job = enqueue_job(
        db,
        job_name="analyze_article",
        celery_task=analyze_article_task,
        idempotency_key=idempotency_key,
        organization_id=ctx.org_id,
        task_kwargs={
            "article_id": article_id,
            "organization_id": ctx.org_id,
        },
    )
    return job_to_dict(job)


@router.get("/top10")
def top10(
    days: int = 1,
    limit: int = 10,
    persist: bool = False,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    scored = get_top10(
        db,
        days=days,
        organization_id=ctx.org_id,
        limit=limit,
        persist=persist,
    )
    return [
        {
            "rank": i,
            "article_id": s.article.id,
            "id": s.article.id,
            "title": s.article.title,
            "source_url": s.article.source_url,
            "source_name": s.article.source_name,
            "status": s.article.status,
            "category": s.article.category,
            "summary": s.article.summary or s.article.excerpt,
            "excerpt": s.article.excerpt or s.article.summary,
            "published_at": s.article.published_at.isoformat() if s.article.published_at else None,
            "total_score": s.total_score,
            "top10_score": s.total_score,
            "base_score": s.base_score,
            "quota_boost": s.quota_boost,
            "matched_pillar": s.matched_pillar,
            "matched_pillar_name": s.matched_pillar_name,
            "quota_priority": bool(s.quota_boost and s.quota_boost > 1.0),
            "scores": {
                "relevance": float(s.article.score_relevance or 0),
                "impact": float(s.article.score_impact or 0),
                "reliability": float(s.article.score_reliability or 0),
                "freshness": float(s.article.score_freshness or 0),
                "content_potential": float(s.article.score_content_potential or 0),
                "mx_us_relevance": float(s.article.score_mx_us_relevance or 0),
                "conversion": float(s.article.score_conversion or 0),
            },
        }
        for i, s in enumerate(scored, start=1)
    ]


@router.get("/reports/latest")
def latest_report(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    report = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.organization_id == ctx.org_id)
        .order_by(WeeklyReport.created_at.desc())
        .first()
    )
    if not report:
        raise HTTPException(404, "No report yet")
    return {
        "id": report.id,
        "week_start": report.week_start.date().isoformat(),
        "week_end": report.week_end.date().isoformat(),
        "report_json": report.report_json,
        "markdown": report.markdown_content,
    }


@router.get("/blog/pending")
def pending_blog_posts(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_BLOG_STAFF)
    posts = (
        db.query(BlogPost)
        .filter(
            BlogPost.status == "pending",
            BlogPost.organization_id == ctx.org_id,
        )
        .order_by(BlogPost.created_at.desc())
        .all()
    )
    return _blog_list_response(posts, db)


@router.get("/blog/editorial")
def editorial_blog_posts(
    article_id: int | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Borradores y aprobados del admin (listos para publicar). No incluye published."""
    require_roles(ctx, *_BLOG_STAFF)
    q = db.query(BlogPost).filter(
        BlogPost.organization_id == ctx.org_id,
        BlogPost.status.in_(("pending", "approved")),
    )
    if article_id is not None:
        q = q.filter(BlogPost.article_id == article_id)
    posts = q.order_by(BlogPost.created_at.desc()).limit(40).all()
    return _blog_list_response(posts, db)


@router.get("/blog/published")
def published_blog_posts(
    org: str = "agencia-piloto",
    db: Session = Depends(get_db),
):
    """Público — sin auth. Solo status=published."""
    organization = (
        db.query(Organization)
        .filter(Organization.slug == org, Organization.is_active.is_(True))
        .first()
    )
    if not organization:
        raise HTTPException(404, "Organization not found")
    posts = (
        db.query(BlogPost)
        .filter(
            BlogPost.status == "published",
            BlogPost.organization_id == organization.id,
        )
        .order_by(BlogPost.published_at.desc())
        .all()
    )
    return _blog_list_response(posts, db)


@router.get("/blog/{slug}")
def get_blog_post(
    slug: str,
    org: str = "agencia-piloto",
    db: Session = Depends(get_db),
):
    """Público: solo posts published (blog Next.js / estático)."""
    organization = (
        db.query(Organization)
        .filter(Organization.slug == org, Organization.is_active.is_(True))
        .first()
    )
    if not organization:
        raise HTTPException(404, "Organization not found")
    post = (
        db.query(BlogPost)
        .filter(
            BlogPost.slug == slug,
            BlogPost.status == "published",
            BlogPost.organization_id == organization.id,
        )
        .first()
    )
    if not post:
        raise HTTPException(404, "Post not found")
    return _blog_response(post, db)


@router.post("/blog/from-top10")
def create_blog_drafts_from_top10(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_BLOG_STAFF)
    scored = get_top10(db, days=7, organization_id=ctx.org_id)
    created = []
    for item in scored:
        post = create_blog_draft_from_article(
            db, item.article, organization_id=ctx.org_id
        )
        created.append(
            {"post_id": post.id, "article_id": item.article.id, "title": post.title}
        )
    return {"created": len(created), "posts": created}


@router.post("/blog/from-article/{article_id}")
def create_blog_draft(
    article_id: int,
    regenerate: bool = True,
    async_mode: bool = False,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_roles(ctx, *_BLOG_STAFF)
    article = (
        db.query(NewsArticle)
        .filter(
            NewsArticle.id == article_id,
            NewsArticle.organization_id == ctx.org_id,
        )
        .first()
    )
    if not article:
        raise HTTPException(404, "Article not found")
    if async_mode:
        from app.services.job_runner import enqueue_job, job_to_dict

        job = enqueue_job(
            db,
            job_name="blog_draft",
            celery_task=generate_blog_draft_task,
            idempotency_key=idempotency_key,
            organization_id=ctx.org_id,
            task_kwargs={
                "article_id": article_id,
                "regenerate": regenerate,
                "organization_id": ctx.org_id,
            },
        )
        return job_to_dict(job)
    post = create_blog_draft_from_article(
        db, article, regenerate=regenerate, organization_id=ctx.org_id
    )
    return _blog_response(post, db)


def _claim_blog_org(post: BlogPost, ctx: TenantContext, db: Session) -> None:
    """Backfill organization_id en posts legacy; luego valida aislamiento."""
    if post.organization_id is None:
        post.organization_id = ctx.org_id
        db.flush()
    else:
        assert_same_org(post.organization_id, ctx)


@router.post("/blog/{post_id}/approve")
def approve_blog_post(
    post_id: int,
    body: ApprovalRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_BLOG_STAFF)
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    _claim_blog_org(post, ctx, db)
    if post.status not in ("pending", "rejected"):
        raise HTTPException(400, f"Cannot approve post in status '{post.status}'")

    from app.services.html_sanitize import sanitize_editorial_html

    post.content_html = sanitize_editorial_html(post.content_html)
    post.status = "approved"
    post.approved_by = body.approved_by
    post.approved_at = datetime.utcnow()
    post.rejection_reason = None
    from app.services.blog_seo import apply_blog_seo_defaults

    apply_blog_seo_defaults(db, post, reviewer=body.approved_by)

    article = db.query(NewsArticle).filter(NewsArticle.id == post.article_id).first()
    if article:
        article.status = "approved"

    db.commit()
    db.refresh(post)
    return _blog_response(post, db)


@router.post("/blog/{post_id}/reject")
def reject_blog_post(
    post_id: int,
    body: RejectionRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_BLOG_STAFF)
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    _claim_blog_org(post, ctx, db)
    if post.status != "pending":
        raise HTTPException(400, f"Cannot reject post in status '{post.status}'")

    post.status = "rejected"
    post.approved_by = body.approved_by
    post.approved_at = datetime.utcnow()
    post.rejection_reason = body.reason
    db.commit()
    db.refresh(post)
    return _blog_response(post, db)


@router.post("/blog/{post_id}/publish")
def publish_blog_post(
    post_id: int,
    body: ApprovalRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_BLOG_STAFF)
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    _claim_blog_org(post, ctx, db)
    if post.status != "approved":
        raise HTTPException(400, "Post must be approved before publishing")

    from app.services.html_sanitize import sanitize_editorial_html

    post.content_html = sanitize_editorial_html(post.content_html)
    post.status = "published"
    post.published_at = datetime.utcnow()
    if not post.approved_by:
        post.approved_by = body.approved_by
    from app.services.blog_seo import apply_blog_seo_defaults

    apply_blog_seo_defaults(db, post, reviewer=body.approved_by)

    article = db.query(NewsArticle).filter(NewsArticle.id == post.article_id).first()
    if article:
        article.status = "published"

    db.commit()
    db.refresh(post)
    return _blog_response(post, db)


@router.patch("/blog/{post_id}/seo")
def update_blog_seo(
    post_id: int,
    body: BlogSeoUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_BLOG_STAFF)
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found")
    _claim_blog_org(post, ctx, db)
    if body.author_name is not None:
        post.author_name = body.author_name.strip() or None
    if body.reviewer_name is not None:
        post.reviewer_name = body.reviewer_name.strip() or None
    if body.categories is not None:
        post.categories_json = [c.strip() for c in body.categories if c and c.strip()][:12]
    if body.seo_description is not None:
        post.seo_description = body.seo_description.strip()[:320] or None
    db.commit()
    db.refresh(post)
    return _blog_response(post, db)


@router.post("/profile/seed")
def seed_profile(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PROFILE_MANAGERS)
    from app.api.deps_env import require_non_production

    require_non_production("Profile seed")
    if ctx.organization.slug != "agencia-piloto":
        raise HTTPException(404, "No seed profile is defined for this organization")
    profile = seed_juan_profile(db)
    return _profile_response(profile, db)


@router.get("/profile")
def get_profile(
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    from app.api.deps_env import allow_auto_seed

    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile and allow_auto_seed():
        profile = seed_juan_profile(db)
        profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    # Sembrar tipologías del PDF si el perfil aún no las tiene
    if not profile.search_themes_json:
        from app.services.news_typologies import default_search_themes

        profile.search_themes_json = default_search_themes()
        db.commit()
        db.refresh(profile)
    return _profile_response(profile, db)


@router.get("/profile/quota")
def get_quota_status(
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    from app.api.deps_env import allow_auto_seed

    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile and allow_auto_seed():
        profile = seed_juan_profile(db)
        profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    snapshot = compute_quota_snapshot(db, profile)
    boosts = pillar_boost_map(snapshot)
    return {
        "profile_id": snapshot.profile_id,
        "profile_slug": snapshot.profile_slug,
        "month_total_pieces": snapshot.month_total,
        "pillars": [
            {
                "pillar_id": p.pillar_id,
                "slug": p.pillar_slug,
                "name": p.pillar_name,
                "target_pct": p.target_pct,
                "actual_pct": p.actual_pct,
                "deficit_pct": p.deficit_pct,
                "count": p.count,
                "quota_boost": boosts.get(p.pillar_slug.lower(), 1.0),
                "needs_boost": p.deficit_pct >= 2.0,
            }
            for p in snapshot.pillars
        ],
        "markets": snapshot.markets,
    }


@router.put("/profile/percentages")
def update_percentages(
    body: ProfilePercentagesUpdate,
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PROFILE_MANAGERS)
    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    try:
        validate_percentages_sum([e.target_pct for e in body.editorial], "editorial")
        validate_percentages_sum([m.target_pct for m in body.markets], "markets")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    pillars_by_slug = {p.slug: p for p in profile.pillars}
    for item in body.editorial:
        pillar = pillars_by_slug.get(item.pillar_slug)
        if not pillar:
            raise HTTPException(400, f"Unknown pillar: {item.pillar_slug}")
        row = (
            db.query(EditorialPercentage)
            .filter_by(profile_id=profile.id, pillar_id=pillar.id, period="monthly")
            .first()
        )
        if row:
            row.target_pct = item.target_pct
        else:
            db.add(
                EditorialPercentage(
                    profile_id=profile.id,
                    pillar_id=pillar.id,
                    target_pct=item.target_pct,
                    period="monthly",
                )
            )

    for item in body.markets:
        code = item.market_code.upper()
        row = (
            db.query(MarketPercentage)
            .filter_by(profile_id=profile.id, market_code=code, period="monthly")
            .first()
        )
        if row:
            row.target_pct = item.target_pct
        else:
            db.add(
                MarketPercentage(
                    profile_id=profile.id,
                    market_code=code,
                    target_pct=item.target_pct,
                    period="monthly",
                )
            )

    db.commit()
    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    return _profile_response(profile, db)


@router.put("/profile/search-themes")
def update_search_themes(
    body: SearchThemesUpdate,
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Temas de búsqueda (tipologías PDF + temas custom) que alimentan la patrulla."""
    require_roles(ctx, *_PROFILE_MANAGERS)
    from app.services.news_typologies import default_search_themes, normalize_themes

    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    if body.reset_to_defaults:
        themes = default_search_themes()
    else:
        themes = normalize_themes([t.model_dump() for t in body.themes])
        if not themes:
            raise HTTPException(400, "Debes enviar al menos un tema con nombre")

    profile.search_themes_json = themes
    db.commit()
    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    return _profile_response(profile, db)


@router.post("/profile/pillars/rebalance")
def rebalance_pillars_pdf(
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Aplica el mix editorial PDF (30/25/20/15/10) al perfil."""
    require_roles(ctx, *_PROFILE_MANAGERS)
    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    profile = apply_pdf_pillar_mix(db, profile)
    return _profile_response(profile, db)


@router.get("/profile/quota-suggestions")
def quota_suggestions(
    limit: int = 5,
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Noticias prioritarias para pilares en déficit (Hoy)."""
    require_roles(ctx, *_STAFF)
    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return {
        "profile_slug": profile.slug,
        "suggestions": suggest_quota_articles(db, profile, limit=min(max(limit, 1), 15)),
    }


@router.get("/profile/percentage-recommendations")
def profile_percentage_recommendations(
    days: int = 30,
    generate: bool = False,
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Devuelve recomendación pendiente; con generate=true calcula una nueva vía leads."""
    require_roles(ctx, *_PROFILE_MANAGERS)
    from app.models.learning import PercentageRecommendation
    from app.services.percentage_adjuster import (
        MIN_QUALIFIED_TOTAL,
        build_percentage_recommendation,
    )

    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")

    pending = (
        db.query(PercentageRecommendation)
        .filter(
            PercentageRecommendation.profile_id == profile.id,
            PercentageRecommendation.status == "pending",
        )
        .order_by(PercentageRecommendation.created_at.desc())
        .first()
    )
    if pending and not generate:
        return {"recommendation": _pct_rec_response(pending), "message": None}

    if generate:
        rec = build_percentage_recommendation(
            db, profile, days=days, organization_id=ctx.org_id
        )
        if rec:
            return {"recommendation": _pct_rec_response(rec), "message": None}
        return {
            "recommendation": _pct_rec_response(pending) if pending else None,
            "message": (
                f"Faltan leads calificados: se necesitan al menos {MIN_QUALIFIED_TOTAL} "
                f"en {days} días. Los likes no mueven porcentajes."
            ),
        }

    return {
        "recommendation": None,
        "message": "No hay sugerencia pendiente. Genera una con leads calificados.",
    }


@router.post("/profile/percentage-recommendations/{rec_id}/accept")
def accept_percentage_recommendation(
    rec_id: int,
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PROFILE_MANAGERS)
    from app.models.learning import PercentageRecommendation
    from app.services.percentage_adjuster import apply_recommendation

    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    rec = (
        db.query(PercentageRecommendation)
        .filter_by(id=rec_id, profile_id=profile.id)
        .first()
    )
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    try:
        apply_recommendation(
            db,
            rec,
            actor=getattr(ctx.user, "email", None) or "agency_admin",
            accept=True,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    return _profile_response(profile, db)


@router.post("/profile/percentage-recommendations/{rec_id}/reject")
def reject_percentage_recommendation(
    rec_id: int,
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PROFILE_MANAGERS)
    from app.models.learning import PercentageRecommendation
    from app.services.percentage_adjuster import apply_recommendation

    profile = get_active_profile(db, slug=slug, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    rec = (
        db.query(PercentageRecommendation)
        .filter_by(id=rec_id, profile_id=profile.id)
        .first()
    )
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    try:
        apply_recommendation(
            db,
            rec,
            actor=getattr(ctx.user, "email", None) or "agency_admin",
            accept=False,
            reason="Rejected from Profile UI",
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "id": rec_id, "status": "rejected"}


@router.get("/profile/ad-trend-notes")
def get_ad_trend_notes(
    slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Últimas notas de tendencias sociales + publicidad orgánica guardadas."""
    require_roles(ctx, *_STAFF)
    from app.services.trend_ad_advisor import get_stored_ad_trend_notes

    notes = get_stored_ad_trend_notes(
        db, organization_id=ctx.org_id, slug=slug
    )
    return {"notes": notes, "message": None if notes else "Aún no hay notas. Genera con tu perfil."}


@router.post("/profile/ad-trend-notes/generate")
def generate_ad_trend_notes_endpoint(
    slug: str = "juan-vasquez",
    async_mode: bool = False,
    max_queries: int = 12,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Investiga noticias del día (DB + motores) y regenera notas. Sync por defecto (UI Hoy)."""
    require_roles(ctx, *_STAFF)
    from app.services.trend_ad_advisor import generate_ad_trend_notes

    if async_mode:
        from app.services.job_runner import enqueue_job, job_to_dict
        from app.tasks import generate_trend_ad_notes_task

        job = enqueue_job(
            db,
            job_name="generate_trend_ad_notes",
            celery_task=generate_trend_ad_notes_task,
            idempotency_key=f"trend-ad-notes:{ctx.org_id}:{slug}",
            task_kwargs={
                "organization_id": ctx.org_id,
                "slug": slug,
                "max_queries": min(max(max_queries, 4), 20),
            },
            organization_id=ctx.org_id,
        )
        return {"job": job_to_dict(job), "notes": None}

    try:
        notes = generate_ad_trend_notes(
            db,
            organization_id=ctx.org_id,
            slug=slug,
            max_queries=min(max(max_queries, 4), 20),
            persist=True,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"No se pudieron generar las notas: {exc}") from exc
    return {"notes": notes, "job": None}


@router.post("/profile/ad-trend-notes/generate-image")
def generate_ad_trend_note_image(
    platform: str,
    slug: str = "juan-vasquez",
    use_openai: bool = True,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Genera la imagen de una plataforma bajo demanda (botón Crear imagen en Hoy)."""
    require_roles(ctx, *_STAFF)
    from app.services.trend_ad_advisor import generate_ad_note_image

    try:
        result = generate_ad_note_image(
            db,
            platform=platform,
            organization_id=ctx.org_id,
            slug=slug,
            use_openai=use_openai,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"No se pudo generar la imagen: {exc}") from exc
    return result


def _pct_rec_response(rec) -> dict:
    return {
        "id": rec.id,
        "profile_id": rec.profile_id,
        "status": rec.status,
        "rationale": rec.rationale,
        "evidence": rec.evidence_json,
        "changes": rec.changes_json or [],
        "min_qualified_leads": rec.min_qualified_leads,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
    }


def _profile_response(profile: ProfessionalProfile, db: Session) -> dict:
    from app.services.news_typologies import default_search_themes, normalize_themes

    snapshot = compute_quota_snapshot(db, profile)
    boosts = pillar_boost_map(snapshot)
    themes = normalize_themes(profile.search_themes_json)
    if not themes:
        themes = default_search_themes()
    return {
        "id": profile.id,
        "slug": profile.slug,
        "full_name": profile.full_name,
        "title": profile.title,
        "bio": profile.bio,
        "services": profile.services_json or [],
        "audiences": profile.audiences_json or [],
        "markets": profile.markets_json or {},
        "search_themes": themes,
        "pillars": [
            {
                "id": p.id,
                "slug": p.slug,
                "name": p.name,
                "description": p.description,
                "keywords": p.keywords_json or [],
            }
            for p in profile.pillars
            if p.is_active
        ],
        "editorial_percentages": [
            {
                "pillar_slug": ep.pillar.slug if ep.pillar else None,
                "pillar_name": ep.pillar.name if ep.pillar else None,
                "target_pct": float(ep.target_pct),
            }
            for ep in profile.editorial_percentages
        ],
        "market_percentages": [
            {"market_code": mp.market_code, "target_pct": float(mp.target_pct)}
            for mp in profile.market_percentages
        ],
        "quota": {
            "month_total_pieces": snapshot.month_total,
            "pillars": [
                {
                    "slug": p.pillar_slug,
                    "name": p.pillar_name,
                    "target_pct": p.target_pct,
                    "actual_pct": p.actual_pct,
                    "deficit_pct": p.deficit_pct,
                    "count": p.count,
                    "quota_boost": boosts.get(p.pillar_slug.lower(), 1.0),
                    "needs_boost": p.deficit_pct >= 2.0,
                }
                for p in snapshot.pillars
            ],
            "deficit_pillars": [
                {
                    "slug": p.pillar_slug,
                    "name": p.pillar_name,
                    "deficit_pct": p.deficit_pct,
                    "quota_boost": boosts.get(p.pillar_slug.lower(), 1.0),
                }
                for p in snapshot.pillars
                if p.deficit_pct >= 2.0
            ],
        },
    }


class GeneratePackageRequest(BaseModel):
    languages: list[str] = Field(default_factory=lambda: ["es"])
    prefer_llm: bool = True
    formats: list[str] | None = None
    package_id: int | None = None
    regenerate: bool = False
    # local = Ollama | cloud = API key | auto = local primero, cloud si falla
    provider_mode: str = "local"


@router.post("/content/from-article/{article_id}")
def generate_content_package(
    article_id: int,
    body: GeneratePackageRequest | None = None,
    async_mode: bool = False,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_roles(ctx, *_STAFF)
    article = (
        db.query(NewsArticle)
        .filter(
            NewsArticle.id == article_id,
            NewsArticle.organization_id == ctx.org_id,
        )
        .first()
    )
    if not article:
        raise HTTPException(404, "Article not found")
    req = body or GeneratePackageRequest()
    if async_mode:
        from app.services.job_runner import enqueue_job, job_to_dict

        job = enqueue_job(
            db,
            job_name="content_package",
            celery_task=generate_content_package_task,
            idempotency_key=idempotency_key,
            organization_id=ctx.org_id,
            task_kwargs={
                "article_id": article_id,
                "languages": req.languages,
                "prefer_llm": req.prefer_llm,
                "organization_id": ctx.org_id,
                "formats": req.formats,
                "package_id": req.package_id,
                "regenerate": req.regenerate,
                "provider_mode": req.provider_mode,
            },
        )
        return job_to_dict(job)
    try:
        package = create_content_package(
            db,
            article,
            languages=req.languages,
            prefer_llm=req.prefer_llm,
            organization_id=ctx.org_id,
            formats=req.formats,
            package_id=req.package_id,
            regenerate=req.regenerate,
            provider_mode=req.provider_mode,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _package_response(package, db)


@router.get("/content/packages")
def list_packages(
    limit: int = 20,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    from sqlalchemy.orm import selectinload

    packages = (
        db.query(ContentPackage)
        .options(selectinload(ContentPackage.pieces))
        .filter(ContentPackage.organization_id == ctx.org_id)
        .order_by(ContentPackage.created_at.desc())
        .limit(limit)
        .all()
    )
    article_ids = {package.article_id for package in packages}
    articles = {
        article.id: article
        for article in db.query(NewsArticle)
        .filter(
            NewsArticle.organization_id == ctx.org_id,
            NewsArticle.id.in_(article_ids),
        )
        .all()
    } if article_ids else {}
    return [
        _package_response(
            package,
            db,
            pieces=sorted(package.pieces, key=lambda piece: piece.id),
            article=articles.get(package.article_id),
        )
        for package in packages
    ]


@router.get("/content/packages/{package_id}")
def get_package(
    package_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    package = (
        db.query(ContentPackage)
        .filter(
            ContentPackage.id == package_id,
            ContentPackage.organization_id == ctx.org_id,
        )
        .first()
    )
    if not package:
        raise HTTPException(404, "Package not found")
    return _package_response(package, db)


@router.get("/content/pending")
def pending_content(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    pieces = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.status == "pending_approval",
            ContentPiece.organization_id == ctx.org_id,
        )
        .order_by(ContentPiece.created_at.desc())
        .all()
    )
    return [_piece_response(p) for p in pieces]


@router.get("/content/pieces/{piece_id}")
def get_piece(
    piece_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    piece = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == piece_id,
            ContentPiece.organization_id == ctx.org_id,
        )
        .first()
    )
    if not piece:
        raise HTTPException(404, "Piece not found")
    return _piece_response(piece)


@router.patch("/content/pieces/{piece_id}")
def update_piece(
    piece_id: int,
    body: PieceUpdateRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Edición humana del borrador antes de aprobar/publicar."""
    require_roles(ctx, *_STAFF)
    piece = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == piece_id,
            ContentPiece.organization_id == ctx.org_id,
        )
        .first()
    )
    if not piece:
        raise HTTPException(404, "Piece not found")
    if body.title is not None:
        piece.title = body.title.strip() or piece.title
    if body.body_text is not None:
        piece.body_text = body.body_text
        if piece.format_type == "carousel":
            try:
                import json as _json

                parsed = _json.loads(body.body_text)
                if isinstance(parsed, list):
                    piece.body_json = {"slides": parsed}
                elif isinstance(parsed, dict):
                    piece.body_json = parsed
            except Exception:
                pass
    if body.body_json is not None:
        piece.body_json = body.body_json if isinstance(body.body_json, dict) else {"slides": body.body_json}
    # Tras editar, vuelve a pendiente de aprobación
    if piece.status == "approved":
        piece.status = "pending_approval"
        piece.approved_by = None
        piece.approved_at = None
    package = db.query(ContentPackage).filter(ContentPackage.id == piece.package_id).first()
    if package:
        _refresh_package_status(package, db)
    db.commit()
    db.refresh(piece)
    return _piece_response(piece)


@router.post("/content/pieces/{piece_id}/approve")
def approve_piece(
    piece_id: int,
    body: ApprovalRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    piece = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == piece_id,
            ContentPiece.organization_id == ctx.org_id,
        )
        .first()
    )
    if not piece:
        raise HTTPException(404, "Piece not found")
    # Idempotente: ya aprobada
    if piece.status == "approved":
        return _piece_response(piece)
    approvable = (
        "pending_approval",
        "rejected",
        "brand_failed",
        "factual_failed",
        "argumentative_failed",
        "draft",
    )
    if piece.status not in approvable:
        raise HTTPException(400, f"Cannot approve piece in status '{piece.status}'")
    # Solo se puede aprobar si pasó factual (o re-revisión manual consciente)
    factual = piece.factual_review_json or {}
    if not factual.get("passed") and not body.approved_by:
        raise HTTPException(400, "Cannot approve: factual review did not pass")
    # Aprobación humana explícita puede sobrepasar fallo factual (queda auditada)
    if not factual.get("passed"):
        piece.rejection_reason = None
        # marca override en brand/factual meta
        piece.factual_review_json = {
            **(factual or {}),
            "passed": True,
            "human_override": True,
            "override_by": body.approved_by,
        }

    piece.status = "approved"
    piece.approved_by = body.approved_by
    piece.approved_at = datetime.utcnow()
    piece.rejection_reason = None
    package = db.query(ContentPackage).filter(ContentPackage.id == piece.package_id).first()
    if package:
        _refresh_package_status(package, db)
    db.commit()
    db.refresh(piece)
    return _piece_response(piece)


@router.post("/content/pieces/{piece_id}/reject")
def reject_piece(
    piece_id: int,
    body: RejectionRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    piece = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == piece_id,
            ContentPiece.organization_id == ctx.org_id,
        )
        .first()
    )
    if not piece:
        raise HTTPException(404, "Piece not found")
    piece.status = "rejected"
    piece.approved_by = body.approved_by
    piece.approved_at = datetime.utcnow()
    piece.rejection_reason = body.reason
    package = db.query(ContentPackage).filter(ContentPackage.id == piece.package_id).first()
    if package:
        _refresh_package_status(package, db)
    db.commit()
    db.refresh(piece)
    return _piece_response(piece)


@router.post("/content/pieces/{piece_id}/reuse")
def reuse_piece(
    piece_id: int,
    prefer_llm: bool = False,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    piece = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == piece_id,
            ContentPiece.organization_id == ctx.org_id,
        )
        .first()
    )
    if not piece:
        raise HTTPException(404, "Piece not found")
    try:
        created = reuse_approved_piece(db, piece, prefer_llm=prefer_llm)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"created": len(created), "pieces": [_piece_response(p) for p in created]}


@router.post("/content/pieces/{piece_id}/translate")
def translate_content_piece(
    piece_id: int,
    target_lang: str = "en",
    prefer_llm: bool = True,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    piece = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == piece_id,
            ContentPiece.organization_id == ctx.org_id,
        )
        .first()
    )
    if not piece:
        raise HTTPException(404, "Piece not found")
    try:
        translated = translate_piece(db, piece, target_lang=target_lang, prefer_llm=prefer_llm)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _piece_response(translated)


def _piece_response(piece: ContentPiece) -> dict:
    return {
        "id": piece.id,
        "package_id": piece.package_id,
        "article_id": piece.article_id,
        "parent_piece_id": piece.parent_piece_id,
        "format_type": piece.format_type,
        "language": piece.language,
        "title": piece.title,
        "body_text": piece.body_text,
        "body_json": piece.body_json,
        "source_url": piece.source_url,
        "status": piece.status,
        "version": piece.version,
        "factual_review": piece.factual_review_json,
        "brand_review": piece.brand_review_json,
        "generation_mode": (piece.generation_json or {}).get("generation_mode"),
        "llm_error": (piece.generation_json or {}).get("llm_error"),
        "model_used": (piece.generation_json or {}).get("model_used"),
        "creatives": (piece.generation_json or {}).get("creatives"),
        "approved_by": piece.approved_by,
        "approved_at": piece.approved_at.isoformat() if piece.approved_at else None,
        "rejection_reason": piece.rejection_reason,
    }


def _package_response(
    package: ContentPackage,
    db: Session,
    *,
    pieces: list[ContentPiece] | None = None,
    article: NewsArticle | None = None,
) -> dict:
    if pieces is None:
        pieces = (
            db.query(ContentPiece)
            .filter(ContentPiece.package_id == package.id)
            .order_by(ContentPiece.id.asc())
            .all()
        )
    if article is None:
        article = db.query(NewsArticle).filter(NewsArticle.id == package.article_id).first()
    return {
        "id": package.id,
        "article_id": package.article_id,
        "profile_id": package.profile_id,
        "status": package.status,
        "article_title": article.title if article else None,
        "article_summary": article.summary if article else None,
        "source_url": article.source_url if article else None,
        "pieces": [_piece_response(p) for p in pieces],
        "created_at": package.created_at.isoformat() if package.created_at else None,
    }


def _blog_list_response(posts: list[BlogPost], db: Session) -> list[dict]:
    article_ids = {post.article_id for post in posts}
    articles = {
        article.id: article
        for article in db.query(NewsArticle)
        .filter(NewsArticle.id.in_(article_ids))
        .all()
    } if article_ids else {}
    return [
        _blog_response(post, db, article=articles.get(post.article_id))
        for post in posts
    ]


def _blog_response(
    post: BlogPost,
    db: Session,
    *,
    article: NewsArticle | None = None,
) -> dict:
    if article is None:
        article = db.query(NewsArticle).filter(NewsArticle.id == post.article_id).first()
    verification = None
    if article and isinstance(article.verification_json, dict):
        v = article.verification_json
        facts = v.get("facts") if isinstance(v.get("facts"), list) else []
        verification = {
            "publishable": v.get("publishable"),
            "summary_verified": v.get("summary_verified"),
            "fact_support_ratio": v.get("fact_support_ratio"),
            "facts_checked": len(facts),
            "facts_supported": sum(1 for f in facts if f.get("supported")),
            "unsupported_claims": v.get("unsupported_claims") or [],
        }
    from app.config import settings
    from app.services.blog_seo import categories_for_article

    cats = post.categories_json if post.categories_json else categories_for_article(db, article)
    return {
        "id": post.id,
        "organization_id": post.organization_id,
        "article_id": post.article_id,
        "title": post.title,
        "slug": post.slug,
        "content_html": post.content_html,
        "source_url": post.source_url,
        "source_citation": post.source_citation,
        "status": post.status,
        "author_name": post.author_name or (settings.client_name or "Juan Vásquez"),
        "reviewer_name": post.reviewer_name or post.approved_by,
        "categories": cats or [],
        "seo_description": post.seo_description,
        "approved_by": post.approved_by,
        "approved_at": post.approved_at.isoformat() if post.approved_at else None,
        "rejection_reason": post.rejection_reason,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "original_summary": article.summary if article else None,
        "original_full_text": article.full_text[:2000] if article and article.full_text else None,
        "verification": verification,
    }


class CopilotRequest(BaseModel):
    instruction: str = Field(min_length=2, max_length=2000)
    target_field: str = Field(default="full_text")
    provider_mode: str = Field(default="auto")
    draft_text: str | None = Field(default=None, max_length=50000)


@router.post("/content/pieces/{piece_id}/copilot")
def copilot_refine_piece_route(
    piece_id: int,
    req: CopilotRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Chat IA sobre una pieza de formato (Estudio). No persiste; el front aplica y guarda."""
    require_roles(ctx, *_STAFF)
    try:
        from app.services.ai_copilot_service import refine_content_piece

        return refine_content_piece(
            db,
            piece_id,
            instruction=req.instruction,
            organization_id=ctx.org_id,
            draft_text=req.draft_text,
            provider_mode=req.provider_mode,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, f"Copiloto no disponible: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"Error inesperado del copiloto: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


class GenerateImagesRequest(BaseModel):
    use_openai: bool = True
    include_article_context: bool = True


@router.post("/content/pieces/{piece_id}/generate-images")
def generate_piece_images(
    piece_id: int,
    body: GenerateImagesRequest | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Genera creatividades PNG (OpenAI fondo + tipografía de marca, o solo marca)."""
    require_roles(ctx, *_STAFF)
    piece = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == piece_id,
            ContentPiece.organization_id == ctx.org_id,
        )
        .first()
    )
    if not piece:
        raise HTTPException(404, "Piece not found")
    req = body or GenerateImagesRequest()
    try:
        from app.services.social_creative_service import generate_creatives_for_piece

        result = generate_creatives_for_piece(
            db,
            piece,
            organization_id=ctx.org_id,
            use_openai=bool(req.use_openai),
            include_article_context=bool(req.include_article_context),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"No se pudieron generar las imágenes: {exc}") from exc
    return {
        **result,
        "piece": _piece_response(piece),
    }


@router.post("/articles/{article_id}/copilot")
def copilot_refine_article_route(
    article_id: int,
    req: CopilotRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    try:
        from app.services.ai_copilot_service import refine_article_content
        res = refine_article_content(
            db,
            article_id=article_id,
            instruction=req.instruction,
            target_field=req.target_field,
            provider_mode=req.provider_mode,
            organization_id=ctx.org_id,
        )
        return res
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, f"Copiloto no disponible: {exc}") from exc
    except Exception as exc:
        raise HTTPException(500, f"Error inesperado del copiloto: {exc}") from exc


@router.post("/blog/{post_id}/copilot")
def copilot_refine_blog_route(
    post_id: int,
    req: CopilotRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    try:
        from app.services.ai_copilot_service import refine_blog_post_content
        res = refine_blog_post_content(
            db,
            post_id=post_id,
            instruction=req.instruction,
            target_field=req.target_field if req.target_field != "full_text" else "content_html",
            provider_mode=req.provider_mode,
        )
        return res
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc
