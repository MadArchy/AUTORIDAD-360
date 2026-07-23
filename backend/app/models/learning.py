"""Fase 7 — leads, engagement y recomendaciones de porcentaje."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=False, index=True
    )
    pillar_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pillars.id"), nullable=True, index=True
    )
    piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pieces.id"), nullable=True
    )
    publish_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("publish_jobs.id"), nullable=True
    )
    channel_variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("channel_variants.id"), nullable=True
    )
    service_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_offers.id"), nullable=True
    )
    source_channel: Mapped[str] = mapped_column(String(64), default="linkedin")
    # linkedin | newsletter | blog | referral | other
    utm_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(128), nullable=True)
    landing_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    contact_name: Mapped[str] = mapped_column(String(256), nullable=False)
    contact_email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    contact_company: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="new", index=True)
    # new | contacted | qualified | converted | lost
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    converted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ContentEngagement(Base):
    """Interacciones por pieza (likes, comments, etc.) — no guían el ajuste solos."""

    __tablename__ = "content_engagements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=False, index=True
    )
    piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pieces.id"), nullable=True
    )
    pillar_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pillars.id"), nullable=True, index=True
    )
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    publish_job_id: Mapped[int | None] = mapped_column(
        ForeignKey("publish_jobs.id"), nullable=True
    )
    external_post_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int | None] = mapped_column(Integer, default=0)
    saves: Mapped[int | None] = mapped_column(Integer, default=0)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PercentageRecommendation(Base):
    __tablename__ = "percentage_recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="pending")
    # pending | accepted | rejected | superseded
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    changes_json: Mapped[list] = mapped_column(JSON, nullable=False)
    # [{pillar_slug, from_pct, to_pct, delta}]
    min_qualified_leads: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=True
    )
    period_days: Mapped[int] = mapped_column(Integer, default=30)
    metrics_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
