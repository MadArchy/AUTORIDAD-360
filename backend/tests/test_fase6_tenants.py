"""Tests Fase 6 — roles y aislamiento."""

from types import SimpleNamespace

from app.models.org import ROLES
from app.services.tenant import AGENCY_ROLES, client_can_see_profile


def test_roles_include_roadmap_set():
    expected = {
        "superadmin",
        "agency_admin",
        "strategist",
        "writer",
        "professional",
        "editor",
        "legal_reviewer",
        "community_manager",
        "analyst",
    }
    assert expected.issubset(set(ROLES))


def test_agency_sees_all_org_clients():
    ctx = SimpleNamespace(
        is_agency_staff=True,
        is_client=False,
        org_id=1,
        membership=SimpleNamespace(profile_id=None),
    )
    p1 = SimpleNamespace(id=10, organization_id=1)
    p2 = SimpleNamespace(id=11, organization_id=2)
    assert client_can_see_profile(ctx, p1) is True
    assert client_can_see_profile(ctx, p2) is False


def test_client_sees_only_own_profile():
    ctx = SimpleNamespace(
        is_agency_staff=False,
        is_client=True,
        org_id=1,
        membership=SimpleNamespace(profile_id=10),
    )
    own = SimpleNamespace(id=10, organization_id=1)
    other = SimpleNamespace(id=11, organization_id=1)
    assert client_can_see_profile(ctx, own) is True
    assert client_can_see_profile(ctx, other) is False


def test_agency_roles_do_not_include_professional():
    assert "professional" not in AGENCY_ROLES
