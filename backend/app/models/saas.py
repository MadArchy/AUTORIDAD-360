"""Fase 5 — SaaS: dominios white-label y cola de refresh editorial."""
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


class CustomDomain(Base):
    __tablename__ = "custom_domains"
    __table_args__ = (
        UniqueConstraint("hostname", name="uq_custom_domains_hostname"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    hostname: Mapped[str] = mapped_column(String(256), nullable=False)
    is_primary: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending | verified | disabled
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ContentRefreshItem(Base):
    """Pieza publicada candidata a actualizar (aprobación humana)."""

    __tablename__ = "content_refresh_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    piece_id: Mapped[int] = mapped_column(
        ForeignKey("content_pieces.id"), nullable=False, index=True
    )
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(64), nullable=False, default="stale")
    # stale | low_engagement | claim_risk | manual
    status: Mapped[str] = mapped_column(String(32), default="suggested", index=True)
    # suggested | approved | in_progress | done | dismissed
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_piece_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    new_piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pieces.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
