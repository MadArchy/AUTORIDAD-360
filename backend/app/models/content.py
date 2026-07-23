from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ContentPackage(Base):
    __tablename__ = "content_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), nullable=False)
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    pieces: Mapped[list["ContentPiece"]] = relationship(back_populates="package")


class ContentPiece(Base):
    __tablename__ = "content_pieces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    package_id: Mapped[int] = mapped_column(
        ForeignKey("content_packages.id"), nullable=False
    )
    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), nullable=False)
    parent_piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pieces.id"), nullable=True
    )
    format_type: Mapped[str] = mapped_column(String(32), nullable=False)
    language: Mapped[str] = mapped_column(String(8), default="es")
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    body_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    version: Mapped[int] = mapped_column(Integer, default=1)
    factual_review_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    brand_review_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    package: Mapped["ContentPackage"] = relationship(back_populates="pieces")


# Alias de compatibilidad con código paralelo (Antigravity)
MultiFormatContent = ContentPackage
