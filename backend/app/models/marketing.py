"""Fase 4 — marketing: ofertas, enlaces UTM y suscriptores newsletter."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ServiceOffer(Base):
    """Catálogo tipado de servicios (CTA / interés de lead)."""

    __tablename__ = "service_offers"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_service_offers_org_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    # active | paused | archived
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class CampaignLink(Base):
    """Preset de URL con UTM (no es CRM; solo atribución)."""

    __tablename__ = "campaign_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    label: Mapped[str] = mapped_column(String(256), nullable=False)
    base_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    utm_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tracked_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pieces.id"), nullable=True
    )
    channel_variant_id: Mapped[int | None] = mapped_column(
        ForeignKey("channel_variants.id"), nullable=True
    )
    service_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_offers.id"), nullable=True
    )
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class NewsletterSubscriber(Base):
    """Lista de suscriptores (sin envío ESP en MVP)."""

    __tablename__ = "newsletter_subscribers"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "email",
            name="uq_newsletter_subscribers_org_email",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending | active | unsubscribed
    source_channel: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(128), nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
