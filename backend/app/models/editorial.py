"""Modelos editoriales canónicos Fase 1–6 (no sobrescribir con stacks paralelos)."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ArticleStatus(str, Enum):
    COLLECTED = "collected"
    CLASSIFIED = "classified"
    VERIFIED = "verified"
    REJECTED = "rejected"
    APPROVED = "approved"
    PUBLISHED = "published"


class BlogStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class NewsCategory(Base):
    __tablename__ = "news_categories"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_news_categories_org_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    rss_url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    articles: Mapped[list["NewsArticle"]] = relationship(back_populates="category")


class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_url",
            name="uq_news_articles_org_source_url",
        ),
        UniqueConstraint(
            "organization_id",
            "content_hash",
            name="uq_news_articles_org_content_hash",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    category_id: Mapped[int] = mapped_column(ForeignKey("news_categories.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    # 767 caracteres + organization_id caben en un índice UNIQUE utf8mb4 de MySQL
    # (límite InnoDB: 3072 bytes) y siguen cubriendo URLs editoriales normales.
    source_url: Mapped[str] = mapped_column(String(767), nullable=False)
    source_name: Mapped[str] = mapped_column(String(256), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=ArticleStatus.COLLECTED.value)
    classification_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    score_relevance: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_impact: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_reliability: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_freshness: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_content_potential: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_mx_us_relevance: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_conversion: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    total_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    category: Mapped["NewsCategory"] = relationship(back_populates="articles")
    blog_posts: Mapped[list["BlogPost"]] = relationship(back_populates="article")


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    week_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    week_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    report_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BlogPost(Base):
    __tablename__ = "blog_posts"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_blog_posts_org_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    article_id: Mapped[int] = mapped_column(ForeignKey("news_articles.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    slug: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_citation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=BlogStatus.PENDING.value)
    author_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reviewer_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    categories_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(320), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    article: Mapped["NewsArticle"] = relationship(back_populates="blog_posts")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    prompt_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
