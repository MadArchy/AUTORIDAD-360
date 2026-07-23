"""Contexto de tenant y reglas de aislamiento multiempresa."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session, Query

from app.models import AppUser, Organization, OrgMembership, ProfessionalProfile, ROLES
from app.db.database import get_db

# Roles de agencia que ven todos los clientes de su org
AGENCY_ROLES = {
    "superadmin",
    "agency_admin",
    "strategist",
    "writer",
    "editor",
    "legal_reviewer",
    "community_manager",
    "analyst",
}


@dataclass
class TenantContext:
    user: AppUser
    organization: Organization
    role: str
    membership: OrgMembership

    @property
    def org_id(self) -> int:
        return self.organization.id

    @property
    def is_superadmin(self) -> bool:
        return self.user.is_superadmin or self.role == "superadmin"

    @property
    def is_agency_staff(self) -> bool:
        return self.role in AGENCY_ROLES or self.is_superadmin

    @property
    def is_client(self) -> bool:
        return self.role == "professional"


from fastapi.security import OAuth2PasswordBearer
from app.services.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_tenant_context(
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
    x_org_slug: str | None = Header(default=None),
    x_user_email: str | None = Header(default=None),
) -> TenantContext:
    """
    Resolución de tenant: JWT Bearer (preferido).
    X-User-Email solo si APP_ENV=development|pilot.
    """
    from app.config import settings

    email = None
    if token:
        payload = decode_access_token(token)
        if not payload or not payload.get("email"):
            raise HTTPException(401, "Token inválido o expirado")
        email = payload.get("email")
    elif x_user_email:
        if not settings.allow_header_auth:
            raise HTTPException(
                401,
                "Header auth disabled in production. Use Authorization: Bearer <token>.",
            )
        email = x_user_email
    else:
        raise HTTPException(
            401,
            "Not authenticated. Use Authorization: Bearer <token>"
            + (" or X-User-Email (dev/pilot)." if settings.allow_header_auth else "."),
        )

    email = email.lower().strip()
    org_slug = (x_org_slug or "agencia-piloto").strip()

    user = db.query(AppUser).filter(AppUser.email == email, AppUser.is_active.is_(True)).first()
    if not user:
        raise HTTPException(401, f"User not found: {email}. Seed tenants first.")

    org = (
        db.query(Organization)
        .filter(Organization.slug == org_slug, Organization.is_active.is_(True))
        .first()
    )
    if not org:
        raise HTTPException(404, f"Organization not found: {org_slug}")

    if user.is_superadmin:
        # Superadmin puede operar en cualquier org
        membership = (
            db.query(OrgMembership)
            .filter(
                OrgMembership.organization_id == org.id,
                OrgMembership.user_id == user.id,
                OrgMembership.is_active.is_(True),
            )
            .first()
        )
        role = membership.role if membership else "superadmin"
        if not membership:
            membership = OrgMembership(
                organization_id=org.id,
                user_id=user.id,
                role="superadmin",
                is_active=True,
            )
        db.info["organization_id"] = org.id
        return TenantContext(user=user, organization=org, role=role, membership=membership)

    membership = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.organization_id == org.id,
            OrgMembership.user_id == user.id,
            OrgMembership.is_active.is_(True),
        )
        .first()
    )
    if not membership:
        raise HTTPException(403, f"User {email} has no access to org {org_slug}")

    if membership.role not in ROLES and membership.role != "superadmin":
        raise HTTPException(400, f"Invalid role: {membership.role}")

    db.info["organization_id"] = org.id
    return TenantContext(
        user=user, organization=org, role=membership.role, membership=membership
    )


def require_roles(ctx: TenantContext, *allowed: str) -> None:
    if ctx.is_superadmin:
        return
    if ctx.role not in allowed:
        raise HTTPException(403, f"Role '{ctx.role}' not allowed. Need one of: {allowed}")


def filter_by_org(query: Query, model, ctx: TenantContext) -> Query:
    """Aísla por organization_id. Superadmin en org ve esa org (no cross-tenant)."""
    if not hasattr(model, "organization_id"):
        return query
    return query.filter(model.organization_id == ctx.org_id)


def assert_same_org(entity_org_id: int | None, ctx: TenantContext) -> None:
    if entity_org_id is None:
        raise HTTPException(403, "Entity has no organization_id")
    if entity_org_id != ctx.org_id and not ctx.is_superadmin:
        raise HTTPException(403, "Cross-organization access denied")
    if entity_org_id != ctx.org_id and ctx.is_superadmin:
        # Superadmin still scoped to X-Org-Slug for safety in MVP
        raise HTTPException(403, "Switch X-Org-Slug to access that organization")


def client_can_see_profile(ctx: TenantContext, profile: ProfessionalProfile) -> bool:
    if ctx.is_agency_staff:
        return profile.organization_id == ctx.org_id
    if ctx.is_client:
        return (
            profile.organization_id == ctx.org_id
            and ctx.membership.profile_id == profile.id
        )
    return False
