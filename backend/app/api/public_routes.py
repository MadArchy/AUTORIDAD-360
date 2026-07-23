"""Rutas públicas (sin JWT): branding, captura de leads con UTM."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.db.database import get_db
from app.models.learning import Lead
from app.models.org import Organization
from app.models.saas import CustomDomain
from app.services.plans import org_saas_payload
from app.services.quota import get_active_profile

router = APIRouter(prefix="/api/v1/public", tags=["public"])


class PublicLeadCreate(BaseModel):
    contact_name: str = Field(min_length=2, max_length=256)
    contact_email: str | None = None
    contact_company: str | None = None
    notes: str | None = None
    organization_slug: str | None = None
    host: str | None = None
    service_offer_id: int | None = None
    piece_id: int | None = None
    source_channel: str = "blog"
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    landing_url: str | None = None


def _resolve_org(
    db: Session,
    *,
    host: str | None = None,
    organization_slug: str | None = None,
) -> Organization:
    if host:
        hostname = host.strip().lower().split(":")[0].rstrip(".")
        domain = (
            db.query(CustomDomain)
            .filter(
                CustomDomain.hostname == hostname,
                CustomDomain.status.in_(("verified", "pending")),
            )
            .first()
        )
        if domain:
            org = db.query(Organization).filter(Organization.id == domain.organization_id).first()
            if org and org.is_active:
                return org
    if organization_slug:
        org = (
            db.query(Organization)
            .filter(
                Organization.slug == organization_slug.strip().lower(),
                Organization.is_active.is_(True),
            )
            .first()
        )
        if org:
            return org
    # Default piloto
    org = (
        db.query(Organization)
        .filter(Organization.slug.in_(("juan-vasquez", "agencia-piloto")))
        .order_by(Organization.id.asc())
        .first()
    )
    if org:
        return org
    raise HTTPException(404, "Organization not found for host/slug")


def _branding_payload(org: Organization) -> dict:
    saas = org_saas_payload(org)
    branding = dict(saas.get("branding") or {})
    display = branding.get("display_name") or org.name or settings.client_name
    return {
        "organization_id": org.id,
        "organization_slug": org.slug,
        "display_name": display,
        "tagline": branding.get("public_tagline")
        or "Análisis de autoridad para empresas: gobernanza, cumplimiento e inteligencia artificial.",
        "logo_url": branding.get("logo_url"),
        "favicon_url": branding.get("favicon_url"),
        "primary_color": branding.get("primary_color") or "#06b6d4",
        "accent_color": branding.get("accent_color") or branding.get("primary_color") or "#06b6d4",
        "plan_code": saas.get("plan_code"),
    }


@router.get("/branding")
def public_branding(
    request: Request,
    host: str | None = Query(default=None),
    organization_slug: str | None = Query(default=None),
    db: Session = Depends(get_db),
    x_forwarded_host: str | None = Header(default=None, alias="X-Forwarded-Host"),
):
    resolved_host = host or x_forwarded_host or request.headers.get("host")
    org = _resolve_org(db, host=resolved_host, organization_slug=organization_slug)
    return _branding_payload(org)


@router.post("/leads")
def public_create_lead(body: PublicLeadCreate, db: Session = Depends(get_db)):
    """Captura pública de lead con UTM (blog / landing). Rate-limit ops queda a cargo del proxy."""
    org = _resolve_org(db, host=body.host, organization_slug=body.organization_slug)
    profile = get_active_profile(db, organization_id=org.id)
    if not profile:
        raise HTTPException(404, "Profile not found for organization")
    lead = Lead(
        organization_id=org.id,
        profile_id=profile.id,
        piece_id=body.piece_id,
        service_offer_id=body.service_offer_id,
        source_channel=body.source_channel or "blog",
        utm_source=body.utm_source,
        utm_medium=body.utm_medium,
        utm_campaign=body.utm_campaign,
        utm_content=body.utm_content,
        utm_term=body.utm_term,
        landing_url=body.landing_url,
        contact_name=body.contact_name.strip(),
        contact_email=(body.contact_email or "").strip().lower() or None,
        contact_company=body.contact_company,
        status="new",
        is_qualified=False,
        notes=body.notes,
        created_at=datetime.utcnow(),
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return {
        "id": lead.id,
        "status": lead.status,
        "organization_slug": org.slug,
        "utm_campaign": lead.utm_campaign,
        "service_offer_id": lead.service_offer_id,
    }


@router.get("/attribution-summary")
def public_attribution_hint():
    """Documenta el contrato UTM esperado (no datos)."""
    return {
        "utm_fields": ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"],
        "recommended": {
            "utm_source": "blog|linkedin|newsletter",
            "utm_medium": "organic|social|email",
            "utm_campaign": "slug-de-campaña",
            "utm_content": "cta-o-formato",
        },
        "capture": "POST /api/v1/public/leads",
    }
