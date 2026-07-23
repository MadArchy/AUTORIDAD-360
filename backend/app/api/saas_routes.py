"""Fase 5 — planes, white-label, refresh editorial."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services import saas_service as saas
from app.services.plans import list_plans, org_saas_payload
from app.services.tenant import TenantContext, get_tenant_context, require_roles

router = APIRouter(prefix="/api/v1/saas", tags=["fase5-saas"])

_ADMIN = ("agency_admin", "superadmin", "strategist")
_STAFF = ("agency_admin", "superadmin", "strategist", "analyst", "editor")


class PlanUpdate(BaseModel):
    plan_code: str = Field(min_length=2, max_length=32)
    plan_limits_json: dict | None = None


class BrandingUpdate(BaseModel):
    display_name: str | None = None
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    favicon_url: str | None = None
    public_tagline: str | None = None


class DomainCreate(BaseModel):
    hostname: str = Field(min_length=3, max_length=256)
    is_primary: bool = False


class RefreshDecide(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    accept: bool
    notes: str | None = None


class RefreshComplete(BaseModel):
    actor: str | None = Field(default=None, max_length=128)
    new_piece_id: int | None = None


class RefreshStart(BaseModel):
    actor: str = Field(min_length=2, max_length=128)


@router.get("/plans")
def get_plans(ctx: TenantContext = Depends(get_tenant_context)):
    require_roles(ctx, *_STAFF)
    return list_plans()


@router.get("/me")
def saas_me(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    domains = saas.list_custom_domains(db, organization_id=ctx.org_id)
    return saas.saas_me_dict(ctx.organization, domains)


@router.put("/plan")
def set_plan(
    body: PlanUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, "agency_admin", "superadmin")
    org = saas.update_org_plan(
        db,
        org=ctx.organization,
        plan_code=body.plan_code,
        plan_limits_json=body.plan_limits_json,
    )
    return org_saas_payload(org)


@router.patch("/branding")
def set_branding(
    body: BrandingUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ADMIN)
    try:
        org = saas.update_org_branding(
            db, org=ctx.organization, branding=body.model_dump(exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return org_saas_payload(org)


@router.get("/domains")
def get_domains(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    return [
        saas.domain_to_dict(d)
        for d in saas.list_custom_domains(db, organization_id=ctx.org_id)
    ]


@router.post("/domains")
def create_domain(
    body: DomainCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ADMIN)
    try:
        row = saas.add_custom_domain(
            db, org=ctx.organization, hostname=body.hostname, is_primary=body.is_primary
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return saas.domain_to_dict(row)


@router.post("/domains/{domain_id}/verify")
def verify_domain(
    domain_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Marca dominio verificado (ops manual en MVP; sin DNS worker)."""
    require_roles(ctx, *_ADMIN)
    try:
        row = saas.mark_domain_verified(
            db, organization_id=ctx.org_id, domain_id=domain_id
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return saas.domain_to_dict(row)


@router.get("/refresh")
def get_refresh(
    status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    rows = saas.list_refresh_items(
        db, organization_id=ctx.org_id, status=status, limit=limit
    )
    return [saas.refresh_to_dict(r) for r in rows]


@router.post("/refresh/suggest")
def suggest_refresh(
    stale_days: int = 30,
    limit: int = 20,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ADMIN)
    created = saas.suggest_refresh_items(
        db, organization_id=ctx.org_id, stale_days=stale_days, limit=limit
    )
    return {"created": [saas.refresh_to_dict(r) for r in created], "count": len(created)}


@router.post("/refresh/{item_id}/decide")
def decide_refresh(
    item_id: int,
    body: RefreshDecide,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ADMIN)
    try:
        row = saas.decide_refresh_item(
            db,
            organization_id=ctx.org_id,
            item_id=item_id,
            accept=body.accept,
            actor=body.actor,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return saas.refresh_to_dict(row)


@router.post("/refresh/{item_id}/start")
def start_refresh(
    item_id: int,
    body: RefreshStart,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ADMIN)
    try:
        row = saas.start_refresh_revision(
            db,
            organization_id=ctx.org_id,
            item_id=item_id,
            actor=body.actor,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return saas.refresh_to_dict(row)


@router.post("/refresh/{item_id}/complete")
def complete_refresh(
    item_id: int,
    body: RefreshComplete,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_ADMIN)
    try:
        row = saas.mark_refresh_done(
            db,
            organization_id=ctx.org_id,
            item_id=item_id,
            new_piece_id=body.new_piece_id,
            actor=body.actor,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return saas.refresh_to_dict(row)
