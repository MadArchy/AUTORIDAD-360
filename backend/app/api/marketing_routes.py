"""Fase 4 — marketing: ofertas, UTM links, newsletter list, CTA variant."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.marketing import (
    CampaignLinkCreate,
    NewsletterSubscriberCreate,
    NewsletterSubscriberUpdate,
    ServiceOfferCreate,
    ServiceOfferUpdate,
    UtmPreviewRequest,
    VariantCtaUpdate,
)
from app.services import marketing_service as mkt
from app.services.quota import get_active_profile
from app.services.tenant import TenantContext, get_tenant_context, require_roles

router = APIRouter(prefix="/api/v1/marketing", tags=["fase4-marketing"])

_ROLES = ("agency_admin", "strategist", "analyst", "community_manager")
_MANAGER = ("agency_admin", "strategist")


@router.get("/offers")
def list_offers(
    status: str | None = "active",
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ROLES)
    if status in ("", "all", "any"):
        status = None
    rows = mkt.list_service_offers(
        db, organization_id=ctx.org_id, status=status, limit=limit
    )
    return [mkt.offer_to_dict(r) for r in rows]


@router.post("/offers")
def create_offer(
    body: ServiceOfferCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_MANAGER)
    row = mkt.create_service_offer(db, organization_id=ctx.org_id, data=body)
    return mkt.offer_to_dict(row)


@router.patch("/offers/{offer_id}")
def patch_offer(
    offer_id: int,
    body: ServiceOfferUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_MANAGER)
    try:
        row = mkt.update_service_offer(
            db, organization_id=ctx.org_id, offer_id=offer_id, data=body
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return mkt.offer_to_dict(row)


@router.post("/offers/seed-from-profile")
def seed_offers(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_MANAGER)
    profile = get_active_profile(db, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    created = mkt.seed_offers_from_profile_services(
        db,
        organization_id=ctx.org_id,
        profile_id=profile.id,
        services=list(profile.services_json or []),
    )
    return {
        "created": [mkt.offer_to_dict(r) for r in created],
        "count": len(created),
    }


@router.get("/campaign-links")
def list_links(
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ROLES)
    rows = mkt.list_campaign_links(db, organization_id=ctx.org_id, limit=limit)
    return [mkt.link_to_dict(r) for r in rows]


@router.post("/campaign-links")
def create_link(
    body: CampaignLinkCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ROLES)
    try:
        row = mkt.create_campaign_link(db, organization_id=ctx.org_id, data=body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return mkt.link_to_dict(row)


@router.post("/utm/preview")
def preview_utm(
    body: UtmPreviewRequest,
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Dry-run tracked URL without persisting."""
    require_roles(ctx, *_ROLES)
    return {
        "tracked_url": mkt.build_tracked_url(
            body.base_url,
            utm_source=body.utm_source,
            utm_medium=body.utm_medium,
            utm_campaign=body.utm_campaign,
            utm_content=body.utm_content,
            utm_term=body.utm_term,
        )
    }


@router.get("/newsletter/subscribers")
def list_subscribers(
    status: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ROLES)
    rows = mkt.list_newsletter_subscribers(
        db, organization_id=ctx.org_id, status=status, limit=limit
    )
    return [mkt.subscriber_to_dict(r) for r in rows]


@router.post("/newsletter/subscribers")
def create_subscriber(
    body: NewsletterSubscriberCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ROLES)
    try:
        row = mkt.create_newsletter_subscriber(
            db, organization_id=ctx.org_id, data=body
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return mkt.subscriber_to_dict(row)


@router.patch("/newsletter/subscribers/{subscriber_id}")
def patch_subscriber(
    subscriber_id: int,
    body: NewsletterSubscriberUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ROLES)
    try:
        row = mkt.update_newsletter_subscriber(
            db,
            organization_id=ctx.org_id,
            subscriber_id=subscriber_id,
            data=body,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return mkt.subscriber_to_dict(row)


@router.patch("/variants/{variant_id}/cta")
def patch_variant_cta(
    variant_id: int,
    body: VariantCtaUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ROLES)
    try:
        row = mkt.update_variant_cta(
            db, organization_id=ctx.org_id, variant_id=variant_id, data=body
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {
        "id": row.id,
        "channel": row.channel,
        "cta_text": row.cta_text,
        "cta_url": row.cta_url,
        "cta_service_offer_id": row.cta_service_offer_id,
    }


@router.get("/attribution")
def attribution_report(
    days: int = 30,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Agrupa leads por UTM/canal/servicio para medir qué convierte."""
    require_roles(ctx, *_ROLES)
    from datetime import datetime, timedelta

    from sqlalchemy import func

    from app.models.learning import Lead

    cutoff = datetime.utcnow() - timedelta(days=max(1, days))
    rows = (
        db.query(
            Lead.source_channel,
            Lead.utm_campaign,
            Lead.utm_source,
            Lead.service_offer_id,
            Lead.status,
            func.count(Lead.id),
        )
        .filter(
            Lead.organization_id == ctx.org_id,
            Lead.created_at >= cutoff,
        )
        .group_by(
            Lead.source_channel,
            Lead.utm_campaign,
            Lead.utm_source,
            Lead.service_offer_id,
            Lead.status,
        )
        .all()
    )
    return {
        "days": days,
        "rows": [
            {
                "source_channel": r[0],
                "utm_campaign": r[1],
                "utm_source": r[2],
                "service_offer_id": r[3],
                "status": r[4],
                "count": r[5],
            }
            for r in rows
        ],
    }
