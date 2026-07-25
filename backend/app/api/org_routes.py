"""Fase 6 — organizaciones, membresías y onboarding multi-cliente."""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models import (
    AppUser,
    Organization,
    OrgMembership,
    ProfessionalProfile,
    ROLES,
)
from app.services.tenant import (
    assert_same_org,
    client_can_see_profile,
    filter_by_org,
    get_tenant_context,
    require_roles,
)
from app.services.tenant_seed import seed_tenants

router = APIRouter(prefix="/api/v1", tags=["fase6-org"])


class OnboardClientRequest(BaseModel):
    slug: str = Field(min_length=2, max_length=64)
    full_name: str = Field(min_length=2, max_length=256)
    title: str | None = None
    email: str = Field(min_length=5, max_length=256)
    bio: str | None = None


class MembershipRequest(BaseModel):
    email: str
    full_name: str
    role: str


# Using get_tenant_context directly as dependency


@router.post("/orgs/seed")
def seed_orgs(
    db: Session = Depends(get_db),
    ctx=Depends(get_tenant_context),
):
    """Solo development/pilot con auth. En production: 403.

    El piloto no debe exponerse a LAN sin JWT; requiere agency_admin.
    """
    from app.config import settings

    if settings.is_production:
        raise HTTPException(
            403,
            "Tenant seed is disabled in production. Use internal install commands.",
        )
    require_roles(ctx, "agency_admin", "superadmin")
    return seed_tenants(db)


@router.get("/orgs/me")
def my_context(db: Session = Depends(get_db), ctx=Depends(get_tenant_context)):
    from app.services.plans import org_saas_payload
    from app.services.saas_service import list_custom_domains, domain_to_dict

    saas = org_saas_payload(ctx.organization)
    domains = list_custom_domains(db, organization_id=ctx.org_id)
    return {
        "user": {
            "id": ctx.user.id,
            "email": ctx.user.email,
            "full_name": ctx.user.full_name,
            "is_superadmin": ctx.user.is_superadmin,
        },
        "organization": {
            "id": ctx.organization.id,
            "slug": ctx.organization.slug,
            "name": ctx.organization.name,
            "org_type": ctx.organization.org_type,
            "plan_code": saas["plan_code"],
            "plan_label": saas["plan_label"],
            "limits": saas["limits"],
            "branding": saas["branding"],
            "domains": [domain_to_dict(d) for d in domains],
        },
        "role": ctx.role,
        "profile_id": ctx.membership.profile_id,
    }


@router.get("/orgs")
def list_orgs(db: Session = Depends(get_db), ctx=Depends(get_tenant_context)):
    if ctx.is_superadmin:
        orgs = db.query(Organization).filter(Organization.is_active.is_(True)).all()
    else:
        # Solo orgs donde el usuario es miembro
        org_ids = [
            m.organization_id
            for m in db.query(OrgMembership)
            .filter(OrgMembership.user_id == ctx.user.id, OrgMembership.is_active.is_(True))
            .all()
        ]
        orgs = db.query(Organization).filter(Organization.id.in_(org_ids)).all()
    return [
        {
            "id": o.id,
            "slug": o.slug,
            "name": o.name,
            "org_type": o.org_type,
        }
        for o in orgs
    ]


@router.get("/orgs/members")
def list_members(db: Session = Depends(get_db), ctx=Depends(get_tenant_context)):
    require_roles(
        ctx,
        "superadmin",
        "agency_admin",
        "strategist",
        "analyst",
    )
    rows = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.organization_id == ctx.org_id,
            OrgMembership.is_active.is_(True),
        )
        .all()
    )
    out = []
    for m in rows:
        user = db.query(AppUser).filter(AppUser.id == m.user_id).first()
        out.append(
            {
                "membership_id": m.id,
                "user_id": m.user_id,
                "email": user.email if user else None,
                "full_name": user.full_name if user else None,
                "role": m.role,
                "profile_id": m.profile_id,
            }
        )
    return out


@router.post("/orgs/members")
def add_member(body: MembershipRequest, db: Session = Depends(get_db), ctx=Depends(get_tenant_context)):
    require_roles(ctx, "superadmin", "agency_admin")
    if body.role not in ROLES:
        raise HTTPException(400, f"Invalid role. Allowed: {ROLES}")

    from app.services.plans import assert_can_add_seat

    user = db.query(AppUser).filter_by(email=body.email.lower()).first()
    if not user:
        user = AppUser(
            email=body.email.lower(),
            full_name=body.full_name,
            is_active=True,
            is_superadmin=False,
        )
        db.add(user)
        db.flush()

    existing = (
        db.query(OrgMembership)
        .filter_by(organization_id=ctx.org_id, user_id=user.id)
        .first()
    )
    if existing:
        was_active = existing.is_active
        if not was_active:
            try:
                assert_can_add_seat(db, ctx.organization)
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
        existing.role = body.role
        existing.is_active = True
        db.commit()
        return {"membership_id": existing.id, "email": user.email, "role": existing.role}

    try:
        assert_can_add_seat(db, ctx.organization)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    m = OrgMembership(
        organization_id=ctx.org_id,
        user_id=user.id,
        role=body.role,
        is_active=True,
    )
    db.add(m)
    db.commit()
    return {"membership_id": m.id, "email": user.email, "role": m.role}


@router.get("/orgs/clients")
def list_clients(db: Session = Depends(get_db), ctx=Depends(get_tenant_context)):
    """Lista perfiles profesionales visibles según rol."""
    query = db.query(ProfessionalProfile).filter(ProfessionalProfile.is_active.is_(True))
    query = filter_by_org(query, ProfessionalProfile, ctx)
    profiles = query.order_by(ProfessionalProfile.id.asc()).all()

    visible = [p for p in profiles if client_can_see_profile(ctx, p)]
    return [
        {
            "id": p.id,
            "slug": p.slug,
            "full_name": p.full_name,
            "title": p.title,
            "organization_id": p.organization_id,
        }
        for p in visible
    ]


@router.post("/orgs/clients/onboard")
def onboard_client(
    body: OnboardClientRequest, db: Session = Depends(get_db), ctx=Depends(get_tenant_context)
):
    require_roles(ctx, "superadmin", "agency_admin", "strategist")

    if db.query(ProfessionalProfile).filter_by(slug=body.slug).first():
        raise HTTPException(400, f"Profile slug already exists: {body.slug}")

    profile = ProfessionalProfile(
        organization_id=ctx.org_id,
        slug=body.slug,
        full_name=body.full_name,
        title=body.title,
        bio=body.bio or f"Onboarding — {body.full_name}",
        services_json=[],
        audiences_json=[],
        markets_json={"primary": ["MX"]},
        is_active=True,
    )
    db.add(profile)
    db.flush()

    user = db.query(AppUser).filter_by(email=body.email.lower()).first()
    if not user:
        user = AppUser(
            email=body.email.lower(),
            full_name=body.full_name,
            is_active=True,
        )
        db.add(user)
        db.flush()

    m = (
        db.query(OrgMembership)
        .filter_by(organization_id=ctx.org_id, user_id=user.id)
        .first()
    )
    if m:
        m.role = "professional"
        m.profile_id = profile.id
        m.is_active = True
    else:
        m = OrgMembership(
            organization_id=ctx.org_id,
            user_id=user.id,
            role="professional",
            profile_id=profile.id,
            is_active=True,
        )
        db.add(m)

    db.commit()
    return {
        "profile_id": profile.id,
        "slug": profile.slug,
        "email": user.email,
        "organization_id": ctx.org_id,
    }


@router.get("/orgs/roles")
def list_roles():
    return {"roles": list(ROLES)}


@router.get("/orgs/clients/{profile_id}")
def get_client(profile_id: int, db: Session = Depends(get_db), ctx=Depends(get_tenant_context)):
    profile = db.query(ProfessionalProfile).filter(ProfessionalProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(404, "Profile not found")
    assert_same_org(profile.organization_id, ctx)
    if not client_can_see_profile(ctx, profile):
        raise HTTPException(403, "Client cannot view other profiles")
    return {
        "id": profile.id,
        "slug": profile.slug,
        "full_name": profile.full_name,
        "title": profile.title,
        "bio": profile.bio,
        "organization_id": profile.organization_id,
    }
