"""Seed multiempresa — agencia piloto + Juan + 2 abogados + 1 consultor IA."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    AppUser,
    Organization,
    OrgMembership,
    ProfessionalProfile,
)
from app.services.audit import log_audit
from app.config import settings
from app.services.quota import seed_juan_profile


def seed_tenants(db: Session) -> dict:
    agency = db.query(Organization).filter_by(slug="agencia-piloto").first()
    if not agency:
        agency = Organization(
            slug="agencia-piloto",
            name="Agencia Piloto Autoridad 360",
            org_type="agency",
            is_active=True,
        )
        db.add(agency)
        db.flush()

    # Superadmin
    admin = _upsert_user(
        db,
        email="admin@autoridad360.local",
        full_name="Super Admin",
        is_superadmin=True,
    )
    _upsert_membership(db, agency.id, admin.id, "superadmin")

    # Agency admin
    agency_admin = _upsert_user(
        db, email="agencia@autoridad360.local", full_name="Admin Agencia"
    )
    _upsert_membership(db, agency.id, agency_admin.id, "agency_admin")

    # Juan — profesional piloto
    juan_profile = seed_juan_profile(db)
    if juan_profile.organization_id != agency.id:
        juan_profile.organization_id = agency.id
        db.flush()

    juan_user = _upsert_user(
        db, email="juan@autoridad360.local", full_name="Juan Vásquez"
    )
    _upsert_membership(
        db, agency.id, juan_user.id, "professional", profile_id=juan_profile.id
    )

    # Estratega de la agencia
    strategist = _upsert_user(
        db, email="estratega@autoridad360.local", full_name="Estratega Editorial"
    )
    _upsert_membership(db, agency.id, strategist.id, "strategist")

    # Cliente 2: abogado adicional
    lawyer2 = _ensure_client_profile(
        db,
        agency_id=agency.id,
        slug="maria-lopez",
        full_name="María López",
        title="Abogada corporativa",
        email="maria@autoridad360.local",
    )

    # Cliente 3: abogado adicional
    lawyer3 = _ensure_client_profile(
        db,
        agency_id=agency.id,
        slug="carlos-ruiz",
        full_name="Carlos Ruiz",
        title="Abogado litigante",
        email="carlos@autoridad360.local",
    )

    # Cliente 4: consultor IA
    consultant = _ensure_client_profile(
        db,
        agency_id=agency.id,
        slug="ana-ia",
        full_name="Ana Torres",
        title="Consultora de IA",
        email="ana@autoridad360.local",
    )

    # Segunda agencia (aislamiento)
    agency2 = db.query(Organization).filter_by(slug="agencia-norte").first()
    if not agency2:
        agency2 = Organization(
            slug="agencia-norte",
            name="Agencia Norte",
            org_type="agency",
            is_active=True,
        )
        db.add(agency2)
        db.flush()
    other_admin = _upsert_user(
        db, email="norte@autoridad360.local", full_name="Admin Norte"
    )
    _upsert_membership(db, agency2.id, other_admin.id, "agency_admin")

    log_audit(
        db,
        entity_type="organization",
        entity_id=agency.id,
        action="tenants_seeded",
        actor="system",
        output_summary="Seed multiempresa: agencia piloto + 4 profesionales + agencia norte",
    )
    db.commit()

    return {
        "agency": {"id": agency.id, "slug": agency.slug},
        "agency2": {"id": agency2.id, "slug": agency2.slug},
        "users": [
            admin.email,
            agency_admin.email,
            juan_user.email,
            strategist.email,
            lawyer2["email"],
            lawyer3["email"],
            consultant["email"],
            other_admin.email,
        ],
        "profiles": [
            {"slug": juan_profile.slug, "org_id": juan_profile.organization_id},
            lawyer2["profile"],
            lawyer3["profile"],
            consultant["profile"],
        ],
    }


from app.services.auth import get_password_hash

def _upsert_user(
    db: Session, *, email: str, full_name: str, is_superadmin: bool = False
) -> AppUser:
    if settings.is_production:
        raise RuntimeError("Tenant seeds are disabled in production")
    default_pw = get_password_hash(settings.dev_seed_password)
    user = db.query(AppUser).filter_by(email=email.lower()).first()
    if user:
        user.full_name = full_name
        user.is_superadmin = is_superadmin
        user.is_active = True
        if not user.hashed_password:
            user.hashed_password = default_pw
        return user
    user = AppUser(
        email=email.lower(),
        full_name=full_name,
        hashed_password=default_pw,
        is_superadmin=is_superadmin,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _upsert_membership(
    db: Session,
    org_id: int,
    user_id: int,
    role: str,
    profile_id: int | None = None,
) -> OrgMembership:
    m = (
        db.query(OrgMembership)
        .filter_by(organization_id=org_id, user_id=user_id)
        .first()
    )
    if m:
        m.role = role
        m.profile_id = profile_id
        m.is_active = True
        return m
    m = OrgMembership(
        organization_id=org_id,
        user_id=user_id,
        role=role,
        profile_id=profile_id,
        is_active=True,
    )
    db.add(m)
    db.flush()
    return m


def _ensure_client_profile(
    db: Session,
    *,
    agency_id: int,
    slug: str,
    full_name: str,
    title: str,
    email: str,
) -> dict:
    profile = db.query(ProfessionalProfile).filter_by(slug=slug).first()
    if not profile:
        profile = ProfessionalProfile(
            organization_id=agency_id,
            slug=slug,
            full_name=full_name,
            title=title,
            bio=f"Cliente piloto onboarding — {title}",
            services_json=[],
            audiences_json=[],
            markets_json={"primary": ["MX"]},
            is_active=True,
        )
        db.add(profile)
        db.flush()
    else:
        profile.organization_id = agency_id
        profile.full_name = full_name
        profile.title = title

    user = _upsert_user(db, email=email, full_name=full_name)
    _upsert_membership(db, agency_id, user.id, "professional", profile_id=profile.id)
    return {
        "email": email,
        "profile": {"slug": profile.slug, "org_id": profile.organization_id, "id": profile.id},
    }
