"""Tests Fase 5 SaaS — planes, BYOK gate, refresh (SQLite)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.content import ContentPackage, ContentPiece
from app.models.editorial import NewsArticle
from app.models.org import Organization
from app.services.plans import (
    assert_byok_allowed,
    effective_limits,
    normalize_plan_code,
)
from app.services.saas_service import (
    decide_refresh_item,
    suggest_refresh_items,
    update_org_branding,
    update_org_plan,
)

engine = create_engine("sqlite:///:memory:")


@event.listens_for(engine, "connect")
def _fk_off(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.close()


Session = sessionmaker(bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = Session()
    org = Organization(slug="t-saas", name="SaaS Org", plan_code="starter")
    session.add(org)
    session.commit()
    yield session, org
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_plan_limits_and_byok_gate(db):
    session, org = db
    assert normalize_plan_code("pro") == "pro"
    limits = effective_limits(org)
    assert limits["byok_allowed"] is False
    with pytest.raises(ValueError, match="BYOK"):
        assert_byok_allowed(org)

    update_org_plan(session, org=org, plan_code="pro")
    session.refresh(org)
    assert effective_limits(org)["byok_allowed"] is True
    assert_byok_allowed(org)


def test_branding_requires_white_label(db):
    session, org = db
    with pytest.raises(ValueError, match="white-label"):
        update_org_branding(session, org=org, branding={"display_name": "X"})

    update_org_plan(session, org=org, plan_code="agency")
    session.refresh(org)
    update_org_branding(session, org=org, branding={"display_name": "Marca X"})
    session.refresh(org)
    assert org.branding_json["display_name"] == "Marca X"


def test_suggest_and_decide_refresh(db):
    session, org = db
    article = NewsArticle(
        organization_id=org.id,
        category_id=1,
        title="Art",
        source_url="https://example.com/a",
        source_name="t",
        published_at=datetime.utcnow() - timedelta(days=60),
        full_text="texto completo",
        content_hash="abc123hash",
    )
    session.add(article)
    session.flush()
    pkg = ContentPackage(
        organization_id=org.id,
        article_id=article.id,
        status="done",
    )
    session.add(pkg)
    session.flush()
    piece = ContentPiece(
        organization_id=org.id,
        package_id=pkg.id,
        article_id=article.id,
        format_type="linkedin",
        title="Old",
        body_text="body",
        source_url="https://example.com/a",
        status="approved",
        version=1,
        updated_at=datetime.utcnow() - timedelta(days=45),
    )
    session.add(piece)
    session.commit()

    created = suggest_refresh_items(session, organization_id=org.id, stale_days=30, limit=5)
    assert len(created) == 1
    item = decide_refresh_item(
        session,
        organization_id=org.id,
        item_id=created[0].id,
        accept=True,
        actor="pytest",
    )
    assert item.status == "approved"
