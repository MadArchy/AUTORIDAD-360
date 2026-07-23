"""Unit tests Fase 1 publish + auth sessions (SQLite in-memory)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.models import Base
from app.models.auth_sessions import AuthSession
from app.models.org import AppUser, Organization
from app.models.publishing import ChannelAccount, PublishJob
from app.services.auth import (
    create_access_token,
    create_refresh_session,
    decode_access_token,
    rotate_refresh_session,
)
from app.services.publish_service import (
    _variant_copy,
    create_publish_package_from_source,
    ensure_default_accounts,
    list_unified_schedule,
    mark_job_published,
    package_to_dict,
    schedule_publish_job,
)

engine = create_engine("sqlite:///:memory:")


@event.listens_for(engine, "connect")
def _fk_off(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=OFF")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_variant_copy_linkedin_has_checklist():
    copy = _variant_copy("linkedin", "Titulo", "<p>Cuerpo</p>", "https://ex.com")
    assert "Titulo" in copy["body_text"]
    assert copy["assisted_checklist"]
    assert copy["format_hint"] == "post"


def test_ensure_accounts_and_package(db_session, monkeypatch):
    org = Organization(slug="t1", name="Test Org")
    db_session.add(org)
    db_session.commit()

    monkeypatch.setattr(
        "app.services.publish_service._source_payload",
        lambda *_a, **_k: {
            "title": "Pieza demo",
            "body": "Texto de autoridad",
            "format_type": "linkedin",
            "source_url": "https://example.com/a",
            "status": "approved",
        },
    )

    accounts = ensure_default_accounts(db_session, org.id)
    assert len(accounts) >= 8
    assert (
        db_session.query(ChannelAccount)
        .filter(ChannelAccount.organization_id == org.id, ChannelAccount.channel == "linkedin")
        .count()
        == 1
    )

    package = create_publish_package_from_source(
        db_session,
        organization_id=org.id,
        source_type="content_piece",
        source_id=99,
        channels=["linkedin", "facebook", "blog"],
    )
    data = package_to_dict(db_session, package)
    assert data["status"] == "ready"
    assert len(data["variants"]) == 3
    job_id = data["variants"][0]["job"]["id"]
    job = db_session.query(PublishJob).filter(PublishJob.id == job_id).one()
    when = datetime.utcnow() + timedelta(days=1)
    schedule_publish_job(db_session, job=job, scheduled_at=when, calendar_slot_id=None)
    db_session.refresh(job)
    assert job.scheduled_at is not None
    sched = list_unified_schedule(db_session, organization_id=org.id, days=14)
    assert any(j["id"] == job.id for j in sched["publish_jobs"])
    mark_job_published(db_session, job=job, actor="pytest", external_url="https://li.com/1")
    db_session.refresh(job)
    assert job.status == "published"


def test_refresh_session_rotate(db_session):
    org = Organization(slug="t2", name="Auth Org")
    db_session.add(org)
    db_session.flush()
    user = AppUser(
        email="u@test.local",
        full_name="Unit Tester",
        hashed_password="x",
        is_active=True,
        is_superadmin=False,
    )
    db_session.add(user)
    db_session.commit()

    raw, row = create_refresh_session(db_session, user_id=user.id, user_agent="pytest")
    assert row.jti
    assert db_session.query(AuthSession).count() == 1

    new_raw, new_row, uid = rotate_refresh_session(db_session, raw_token=raw)
    assert uid == user.id
    assert new_raw != raw
    assert new_row.id != row.id
    db_session.refresh(row)
    assert row.is_active is False

    token = create_access_token({"sub": str(user.id), "email": user.email})
    payload = decode_access_token(token)
    assert payload.get("type") == "access"
    assert payload.get("sub") == str(user.id)
