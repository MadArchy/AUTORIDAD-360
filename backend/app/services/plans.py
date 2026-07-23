"""Planes SaaS (entitlements) — sin billing/Stripe en MVP."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.org import Organization, OrgMembership

# Catálogo fijo. plan_limits_json en org puede sobreescribir claves.
PLAN_CATALOG: dict[str, dict[str, Any]] = {
    "pilot": {
        "label": "Piloto",
        "max_seats": 10,
        "max_ai_daily_requests": 200,
        "max_channels": 8,
        "byok_allowed": True,
        "white_label": True,
        "max_custom_domains": 2,
    },
    "starter": {
        "label": "Starter",
        "max_seats": 3,
        "max_ai_daily_requests": 50,
        "max_channels": 3,
        "byok_allowed": False,
        "white_label": False,
        "max_custom_domains": 0,
    },
    "pro": {
        "label": "Pro",
        "max_seats": 15,
        "max_ai_daily_requests": 500,
        "max_channels": 8,
        "byok_allowed": True,
        "white_label": True,
        "max_custom_domains": 3,
    },
    "agency": {
        "label": "Agency",
        "max_seats": 50,
        "max_ai_daily_requests": 2000,
        "max_channels": 8,
        "byok_allowed": True,
        "white_label": True,
        "max_custom_domains": 20,
    },
}

DEFAULT_PLAN = "pilot"


def normalize_plan_code(code: str | None) -> str:
    raw = (code or DEFAULT_PLAN).strip().lower()
    return raw if raw in PLAN_CATALOG else DEFAULT_PLAN


def effective_limits(org: Organization) -> dict[str, Any]:
    code = normalize_plan_code(getattr(org, "plan_code", None))
    base = dict(PLAN_CATALOG[code])
    overrides = getattr(org, "plan_limits_json", None) or {}
    if isinstance(overrides, dict):
        for key, value in overrides.items():
            if key in base and value is not None:
                base[key] = value
    base["plan_code"] = code
    return base


def assert_byok_allowed(org: Organization) -> None:
    limits = effective_limits(org)
    if not limits.get("byok_allowed"):
        raise ValueError(
            f"Plan '{limits['plan_code']}' no permite BYOK. Usa Ollama local o sube a Pro/Agency."
        )


def assert_can_add_seat(db: Session, org: Organization) -> None:
    limits = effective_limits(org)
    max_seats = int(limits.get("max_seats") or 0)
    if max_seats <= 0:
        return
    count = (
        db.query(OrgMembership)
        .filter(
            OrgMembership.organization_id == org.id,
            OrgMembership.is_active.is_(True),
        )
        .count()
    )
    if count >= max_seats:
        raise ValueError(
            f"Límite de asientos del plan '{limits['plan_code']}' alcanzado ({max_seats})."
        )


def assert_can_add_domain(db: Session, org: Organization) -> None:
    from app.models.saas import CustomDomain

    limits = effective_limits(org)
    max_domains = int(limits.get("max_custom_domains") or 0)
    if not limits.get("white_label") or max_domains <= 0:
        raise ValueError(
            f"Plan '{limits['plan_code']}' no incluye white-label / dominios custom."
        )
    count = (
        db.query(CustomDomain)
        .filter(
            CustomDomain.organization_id == org.id,
            CustomDomain.status != "disabled",
        )
        .count()
    )
    if count >= max_domains:
        raise ValueError(f"Límite de dominios custom alcanzado ({max_domains}).")


def list_plans() -> list[dict[str, Any]]:
    return [
        {"code": code, **{k: v for k, v in meta.items()}}
        for code, meta in PLAN_CATALOG.items()
    ]


def org_saas_payload(org: Organization) -> dict[str, Any]:
    limits = effective_limits(org)
    branding = getattr(org, "branding_json", None) or {}
    return {
        "plan_code": limits["plan_code"],
        "plan_label": PLAN_CATALOG[limits["plan_code"]]["label"],
        "limits": {
            k: v
            for k, v in limits.items()
            if k not in ("plan_code", "label")
        },
        "branding": branding if isinstance(branding, dict) else {},
    }
