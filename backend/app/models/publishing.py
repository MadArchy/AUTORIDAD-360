"""Publicación multi-canal: cuentas, medios, variantes y jobs."""
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


class ChannelAccount(Base):
    __tablename__ = "channel_accounts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "channel",
            "account_label",
            name="uq_channel_accounts_org_channel_label",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # blog | linkedin | facebook | instagram | tiktok | youtube | x | newsletter
    account_label: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    status: Mapped[str] = mapped_column(String(32), default="assisted")
    # assisted | connected | disabled
    external_account_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="image")
    # image | video | thumbnail | document
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    storage_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(512), nullable=True)
    aspect_ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # 1:1 | 4:5 | 9:16 | 16:9
    status: Mapped[str] = mapped_column(String(32), default="ready")
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PublishPackage(Base):
    __tablename__ = "publish_packages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # content_piece | blog_post | package
    source_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    # draft | ready | partially_published | published | failed
    brief_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ChannelVariant(Base):
    __tablename__ = "channel_variants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    package_id: Mapped[int] = mapped_column(
        ForeignKey("publish_packages.id"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    format_hint: Mapped[str] = mapped_column(String(64), nullable=False, default="post")
    # post | carousel | reel | short | article | newsletter
    headline: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    hashtags_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    cta_text: Mapped[str | None] = mapped_column(String(256), nullable=True)
    cta_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cta_service_offer_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_offers.id"), nullable=True
    )
    media_asset_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    aspect_ratio: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PublishJob(Base):
    __tablename__ = "publish_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    variant_id: Mapped[int] = mapped_column(
        ForeignKey("channel_variants.id"), nullable=False, index=True
    )
    channel_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("channel_accounts.id"), nullable=True
    )
    calendar_slot_id: Mapped[int | None] = mapped_column(
        ForeignKey("calendar_slots.id"), nullable=True, index=True
    )
    channel: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    # queued | assisted_ready | publishing | published | failed | cancelled
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    external_post_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
