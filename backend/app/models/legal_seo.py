"""Fase 3 — inteligencia SEO + Legal Authority Content Engine."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class SeoKeywordCluster(Base):
    __tablename__ = "seo_keyword_clusters"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "slug",
            name="uq_seo_keyword_clusters_org_slug",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    primary_keyword: Mapped[str] = mapped_column(String(256), nullable=False)
    keywords_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    search_intent: Mapped[str] = mapped_column(String(64), default="informational")
    # informational | commercial | transactional | navigational
    jurisdiction: Mapped[str] = mapped_column(String(64), default="MX")
    # MX | US | MX-US | EU | global
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ContentBrief(Base):
    __tablename__ = "content_briefs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    cluster_id: Mapped[int | None] = mapped_column(
        ForeignKey("seo_keyword_clusters.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(64), default="MX")
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    # draft | ready | in_production | published | archived
    version: Mapped[int] = mapped_column(Integer, default=1)
    brief_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    prompt_template_id: Mapped[int | None] = mapped_column(
        ForeignKey("prompt_templates.id"), nullable=True
    )
    created_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "name",
            "version",
            name="uq_prompt_templates_org_name_version",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    channel: Mapped[str] = mapped_column(String(64), default="blog")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class LegalClaim(Base):
    __tablename__ = "legal_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    content_piece_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pieces.id"), nullable=True, index=True
    )
    blog_post_id: Mapped[int | None] = mapped_column(
        ForeignKey("blog_posts.id"), nullable=True, index=True
    )
    brief_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_briefs.id"), nullable=True, index=True
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(64), default="MX")
    claim_type: Mapped[str] = mapped_column(String(64), default="factual")
    # factual | legal_opinion | regulatory | citation
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # pending | supported | unsupported | needs_review | withdrawn
    risk_level: Mapped[str] = mapped_column(String(16), default="yellow")
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class LegalEvidence(Base):
    __tablename__ = "legal_evidences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    claim_id: Mapped[int] = mapped_column(
        ForeignKey("legal_claims.id"), nullable=False, index=True
    )
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(64), default="primary_source")
    # primary_source | statute | case_law | regulator | secondary
    jurisdiction: Mapped[str] = mapped_column(String(64), default="MX")
    verified_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
