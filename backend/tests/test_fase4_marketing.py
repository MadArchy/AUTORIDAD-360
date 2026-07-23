"""Tests Fase 4 marketing — UTM builder + ofertas (SQLite)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.org import Organization
from app.schemas.marketing import CampaignLinkCreate, ServiceOfferCreate
from app.services.marketing_service import (
    build_tracked_url,
    create_campaign_link,
    create_service_offer,
    seed_offers_from_profile_services,
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
    org = Organization(slug="t-mkt", name="Mkt Org")
    session.add(org)
    session.commit()
    yield session, org.id
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_build_tracked_url_merges_and_overwrites():
    url = build_tracked_url(
        "https://example.com/post?ref=x",
        utm_source="linkedin",
        utm_medium="social",
        utm_campaign="gov-ia",
    )
    assert "utm_source=linkedin" in url
    assert "utm_medium=social" in url
    assert "utm_campaign=gov-ia" in url
    assert "ref=x" in url


def test_offer_and_campaign_link_flow(db):
    session, org_id = db
    offer = create_service_offer(
        session,
        organization_id=org_id,
        data=ServiceOfferCreate(name="Asesoría corporativa transfronteriza"),
    )
    assert offer.slug.startswith("asesoria")

    link = create_campaign_link(
        session,
        organization_id=org_id,
        data=CampaignLinkCreate(
            label="LI post Q3",
            base_url="https://juanvasquez.example/contacto",
            utm_source="linkedin",
            utm_medium="social",
            utm_campaign="q3-compliance",
            service_offer_id=offer.id,
        ),
    )
    assert "utm_campaign=q3-compliance" in link.tracked_url
    assert link.service_offer_id == offer.id


def test_seed_offers_idempotent(db):
    session, org_id = db
    created = seed_offers_from_profile_services(
        session,
        organization_id=org_id,
        profile_id=1,
        services=["Compliance y regulación", "Compliance y regulación"],
    )
    assert len(created) == 1
    again = seed_offers_from_profile_services(
        session,
        organization_id=org_id,
        profile_id=1,
        services=["Compliance y regulación"],
    )
    assert again == []
