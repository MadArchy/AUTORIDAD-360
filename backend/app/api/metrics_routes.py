"""Fase 7 — métricas, leads y recomendaciones de porcentaje."""

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import ProfessionalProfile
from app.models.learning import ContentEngagement, Lead, PercentageRecommendation
from app.services.metrics import compute_dashboard
from app.services.percentage_adjuster import (
    apply_recommendation,
    build_percentage_recommendation,
)
from app.services.quota import get_active_profile, seed_juan_profile
from app.services.tenant import TenantContext, get_tenant_context, require_roles

router = APIRouter(prefix="/api/v1", tags=["fase7-metrics"])

_METRICS_ROLES = ("agency_admin", "strategist", "analyst")
_LEAD_ROLES = ("agency_admin", "strategist", "analyst", "community_manager")
_ENGAGEMENT_ROLES = ("agency_admin", "analyst", "community_manager")
_RECOMMENDATION_MANAGERS = ("agency_admin", "strategist")


class LeadCreate(BaseModel):
    profile_id: int | None = None
    pillar_id: int | None = None
    piece_id: int | None = None
    publish_job_id: int | None = None
    channel_variant_id: int | None = None
    service_offer_id: int | None = None
    source_channel: str = "linkedin"
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    landing_url: str | None = None
    contact_name: str = Field(min_length=2, max_length=256)
    contact_email: str | None = None
    contact_company: str | None = None
    status: str = "new"
    is_qualified: bool = False
    notes: str | None = None


class LeadStatusUpdate(BaseModel):
    status: str
    is_qualified: bool | None = None
    notes: str | None = None
    service_offer_id: int | None = None


class EngagementCreate(BaseModel):
    profile_id: int | None = None
    piece_id: int | None = None
    pillar_id: int | None = None
    channel: str | None = None
    publish_job_id: int | None = None
    external_post_id: str | None = None
    likes: int = 0
    comments: int = 0
    shares: int = 0
    impressions: int = 0
    clicks: int = 0
    saves: int = 0


class RecDecision(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    accept: bool
    reason: str | None = None


# _optional_tenant eliminado por JWT


@router.get("/metrics/dashboard")
def metrics_dashboard(
    days: int = 30,
    profile_slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_METRICS_ROLES)
    from app.api.deps_env import allow_auto_seed

    profile = get_active_profile(db, slug=profile_slug, organization_id=ctx.org_id)
    if not profile and allow_auto_seed() and ctx.organization.slug == "agencia-piloto":
        profile = seed_juan_profile(db)
    if not profile:
        raise HTTPException(404, "Profile not found")
    return compute_dashboard(
        db, profile_id=profile.id, organization_id=ctx.org_id, days=days
    )


@router.post("/leads")
def create_lead(
    body: LeadCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_LEAD_ROLES)
    from app.api.deps_env import allow_auto_seed

    profile = None
    if body.profile_id:
        profile = db.query(ProfessionalProfile).filter_by(
            id=body.profile_id,
            organization_id=ctx.org_id,
        ).first()
    else:
        profile = get_active_profile(db, organization_id=ctx.org_id)
        if not profile and allow_auto_seed() and ctx.organization.slug == "agencia-piloto":
            profile = seed_juan_profile(db)
    if not profile:
        raise HTTPException(404, "Profile not found")

    status = body.status
    is_qualified = body.is_qualified or status in ("qualified", "converted")
    lead = Lead(
        organization_id=ctx.org_id,
        profile_id=profile.id,
        pillar_id=body.pillar_id,
        piece_id=body.piece_id,
        publish_job_id=body.publish_job_id,
        channel_variant_id=body.channel_variant_id,
        service_offer_id=body.service_offer_id,
        source_channel=body.source_channel,
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
        utm_content=body.utm_content,
        utm_term=body.utm_term,
        landing_url=body.landing_url,
        contact_name=body.contact_name,
        contact_email=body.contact_email,
        contact_company=body.contact_company,
        status=status,
        is_qualified=is_qualified,
        notes=body.notes,
        converted_at=datetime.utcnow() if status == "converted" else None,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return _lead_response(lead)


@router.get("/leads")
def list_leads(
    status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_LEAD_ROLES)
    q = db.query(Lead).order_by(Lead.created_at.desc())
    q = q.filter(Lead.organization_id == ctx.org_id)
    if status:
        q = q.filter(Lead.status == status)
    return [_lead_response(l) for l in q.limit(limit).all()]


@router.patch("/leads/{lead_id}")
def update_lead(
    lead_id: int,
    body: LeadStatusUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_LEAD_ROLES)
    lead = db.query(Lead).filter(
        Lead.id == lead_id,
        Lead.organization_id == ctx.org_id,
    ).first()
    if not lead:
        raise HTTPException(404, "Lead not found")
    lead.status = body.status
    if body.is_qualified is not None:
        lead.is_qualified = body.is_qualified
    else:
        lead.is_qualified = body.status in ("qualified", "converted")
    if body.notes is not None:
        lead.notes = body.notes
    if body.service_offer_id is not None:
        lead.service_offer_id = body.service_offer_id or None
    if body.status == "converted":
        lead.converted_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    return _lead_response(lead)


@router.get("/engagements")
def list_engagements(
    channel: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ENGAGEMENT_ROLES)
    q = db.query(ContentEngagement).filter(
        ContentEngagement.organization_id == ctx.org_id
    )
    if channel:
        q = q.filter(ContentEngagement.channel == channel)
    rows = q.order_by(ContentEngagement.recorded_at.desc()).limit(limit).all()
    return [_engagement_response(r) for r in rows]


@router.post("/engagements")
def create_engagement(
    body: EngagementCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ENGAGEMENT_ROLES)
    from app.api.deps_env import allow_auto_seed

    profile = None
    if body.profile_id:
        profile = db.query(ProfessionalProfile).filter_by(
            id=body.profile_id,
            organization_id=ctx.org_id,
        ).first()
    else:
        profile = get_active_profile(db, organization_id=ctx.org_id)
        if not profile and allow_auto_seed() and ctx.organization.slug == "agencia-piloto":
            profile = seed_juan_profile(db)
    if not profile:
        raise HTTPException(404, "Profile not found")
    row = ContentEngagement(
        organization_id=ctx.org_id,
        profile_id=profile.id,
        piece_id=body.piece_id,
        pillar_id=body.pillar_id,
        channel=body.channel,
        publish_job_id=body.publish_job_id,
        external_post_id=body.external_post_id,
        likes=body.likes,
        comments=body.comments,
        shares=body.shares,
        impressions=body.impressions,
        clicks=body.clicks,
        saves=body.saves,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    out = _engagement_response(row)
    out["note"] = (
        "Engagement stored for reporting only — does not drive percentage adjustment"
    )
    return out


@router.post("/recommendations/percentages/generate")
def generate_rec(
    days: int = 30,
    profile_slug: str = "juan-vasquez",
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_RECOMMENDATION_MANAGERS)
    from app.api.deps_env import allow_auto_seed

    profile = get_active_profile(db, slug=profile_slug, organization_id=ctx.org_id)
    if not profile and allow_auto_seed() and ctx.organization.slug == "agencia-piloto":
        profile = seed_juan_profile(db)
    if not profile:
        raise HTTPException(404, "Profile not found")
    rec = build_percentage_recommendation(
        db, profile, days=days, organization_id=ctx.org_id
    )
    if not rec:
        return {
            "recommendation": None,
            "message": (
                f"Insufficient evidence: need >= 3 qualified leads in {days} days. "
                "Likes alone never trigger a recommendation."
            ),
        }
    return {"recommendation": _rec_response(rec)}


@router.get("/recommendations/percentages")
def list_recs(
    status: str | None = "pending",
    limit: int = 20,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_METRICS_ROLES)
    q = db.query(PercentageRecommendation).order_by(
        PercentageRecommendation.created_at.desc()
    )
    q = q.filter(PercentageRecommendation.organization_id == ctx.org_id)
    if status:
        q = q.filter(PercentageRecommendation.status == status)
    return [_rec_response(r) for r in q.limit(limit).all()]


@router.post("/recommendations/percentages/{rec_id}/decide")
def decide_rec(
    rec_id: int,
    body: RecDecision,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_RECOMMENDATION_MANAGERS)
    rec = db.query(PercentageRecommendation).filter_by(
        id=rec_id,
        organization_id=ctx.org_id,
    ).first()
    if not rec:
        raise HTTPException(404, "Recommendation not found")
    try:
        rec = apply_recommendation(
            db, rec, actor=body.actor, accept=body.accept, reason=body.reason
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _rec_response(rec)


def _lead_response(lead: Lead) -> dict:
    return {
        "id": lead.id,
        "organization_id": lead.organization_id,
        "profile_id": lead.profile_id,
        "pillar_id": lead.pillar_id,
        "piece_id": lead.piece_id,
        "publish_job_id": lead.publish_job_id,
        "channel_variant_id": lead.channel_variant_id,
        "service_offer_id": lead.service_offer_id,
        "source_channel": lead.source_channel,
        "utm_source": lead.utm_source,
        "utm_medium": lead.utm_medium,
        "utm_campaign": lead.utm_campaign,
        "utm_content": lead.utm_content,
        "utm_term": lead.utm_term,
        "landing_url": lead.landing_url,
        "contact_name": lead.contact_name,
        "contact_email": lead.contact_email,
        "contact_company": lead.contact_company,
        "status": lead.status,
        "is_qualified": lead.is_qualified,
        "notes": lead.notes,
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "converted_at": lead.converted_at.isoformat() if lead.converted_at else None,
    }


def _engagement_response(row: ContentEngagement) -> dict:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "profile_id": row.profile_id,
        "piece_id": row.piece_id,
        "pillar_id": row.pillar_id,
        "channel": row.channel,
        "publish_job_id": row.publish_job_id,
        "external_post_id": row.external_post_id,
        "likes": row.likes,
        "comments": row.comments,
        "shares": row.shares,
        "impressions": row.impressions,
        "clicks": row.clicks or 0,
        "saves": row.saves or 0,
        "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
    }


def _rec_response(rec: PercentageRecommendation) -> dict:
    return {
        "id": rec.id,
        "profile_id": rec.profile_id,
        "organization_id": rec.organization_id,
        "status": rec.status,
        "rationale": rec.rationale,
        "evidence": rec.evidence_json,
        "changes": rec.changes_json,
        "min_qualified_leads": rec.min_qualified_leads,
        "created_at": rec.created_at.isoformat() if rec.created_at else None,
        "decided_at": rec.decided_at.isoformat() if rec.decided_at else None,
        "decided_by": rec.decided_by,
        "decision_reason": rec.decision_reason,
    }
