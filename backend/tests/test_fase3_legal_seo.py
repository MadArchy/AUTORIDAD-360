"""Tests unitarios Fase 3 — schemas + servicio (SQLite)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.org import Organization
from app.schemas.legal_seo import (
    ContentBriefCreate,
    KeywordClusterCreate,
    LegalClaimCreate,
    LegalEvidenceCreate,
)
from app.services.legal_seo_service import (
    add_legal_evidence,
    create_content_brief,
    create_keyword_cluster,
    create_legal_claim,
    update_claim_status,
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
    org = Organization(slug="t-seo", name="SEO Org")
    session.add(org)
    session.commit()
    yield session, org.id
    session.close()
    Base.metadata.drop_all(bind=engine)


def test_cluster_brief_claim_evidence_flow(db):
    session, org_id = db
    cluster = create_keyword_cluster(
        session,
        organization_id=org_id,
        data=KeywordClusterCreate(
            name="Gobernanza IA MX",
            primary_keyword="gobernanza de ia mexico",
            keywords=["cumplimiento ia", "riesgo consejo"],
            search_intent="informational",
            jurisdiction="MX",
        ),
    )
    assert cluster.slug.startswith("gobernanza")

    brief = create_content_brief(
        session,
        organization_id=org_id,
        data=ContentBriefCreate(
            title="Checklist de gobernanza IA para el consejo",
            cluster_id=cluster.id,
            jurisdiction="MX",
            angle="Qué debe preguntar el GC mañana",
            created_by="pytest",
        ),
    )
    assert brief.brief_json["primary_keyword"] == "gobernanza de ia mexico"

    claim = create_legal_claim(
        session,
        organization_id=org_id,
        data=LegalClaimCreate(
            claim_text="La CNBV emitió lineamientos sobre uso de modelos de IA en 2024.",
            jurisdiction="MX",
            brief_id=brief.id,
            claim_type="regulatory",
        ),
    )
    with pytest.raises(ValueError, match="evidence"):
        update_claim_status(
            session,
            organization_id=org_id,
            claim_id=claim.id,
            status="supported",
            actor="legal",
        )

    add_legal_evidence(
        session,
        organization_id=org_id,
        data=LegalEvidenceCreate(
            claim_id=claim.id,
            source_url="https://www.gob.mx/cnbv/ejemplo",
            source_title="Comunicado CNBV",
            excerpt="Lineamientos…",
            verified_by="legal@test",
            jurisdiction="MX",
        ),
    )
    updated = update_claim_status(
        session,
        organization_id=org_id,
        claim_id=claim.id,
        status="supported",
        actor="legal",
    )
    assert updated.status == "supported"


def test_extract_factual_claim_texts_skips_opinion():
    from app.models.content import ContentPiece
    from app.services.content_review import extract_factual_claim_texts

    piece = ContentPiece(
        package_id=1,
        article_id=1,
        format_type="linkedin",
        title="t",
        body_text=(
            "La CNBV publicó lineamientos sobre modelos de IA en 2024. "
            "En mi opinión esto cambia todo. "
            "El regulador exige documentación del modelo."
        ),
        source_url="https://ex.com",
        status="draft",
    )
    claims = extract_factual_claim_texts(piece)
    assert any("CNBV" in c for c in claims)
    assert not any("opinión" in c.lower() for c in claims)
