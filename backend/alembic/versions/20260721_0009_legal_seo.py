"""Fase 3 SEO + Legal Authority tables.

Revision ID: 20260721_0009
Revises: 20260721_0008
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260721_0009"
down_revision = "20260721_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "seo_keyword_clusters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("primary_keyword", sa.String(length=256), nullable=False),
        sa.Column("keywords_json", sa.JSON(), nullable=True),
        sa.Column("search_intent", sa.String(length=64), nullable=True),
        sa.Column("jurisdiction", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("organization_id", "slug", name="uq_seo_keyword_clusters_org_slug"),
    )
    op.create_index("ix_seo_keyword_clusters_organization_id", "seo_keyword_clusters", ["organization_id"])
    op.create_index("ix_seo_keyword_clusters_status", "seo_keyword_clusters", ["status"])

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "organization_id",
            "name",
            "version",
            name="uq_prompt_templates_org_name_version",
        ),
    )
    op.create_index("ix_prompt_templates_organization_id", "prompt_templates", ["organization_id"])

    op.create_table(
        "content_briefs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("cluster_id", sa.Integer(), sa.ForeignKey("seo_keyword_clusters.id"), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("slug", sa.String(length=256), nullable=False),
        sa.Column("jurisdiction", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("brief_json", sa.JSON(), nullable=False),
        sa.Column("prompt_template_id", sa.Integer(), sa.ForeignKey("prompt_templates.id"), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_content_briefs_organization_id", "content_briefs", ["organization_id"])
    op.create_index("ix_content_briefs_cluster_id", "content_briefs", ["cluster_id"])
    op.create_index("ix_content_briefs_slug", "content_briefs", ["slug"])
    op.create_index("ix_content_briefs_status", "content_briefs", ["status"])

    op.create_table(
        "legal_claims",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("content_piece_id", sa.Integer(), sa.ForeignKey("content_pieces.id"), nullable=True),
        sa.Column("blog_post_id", sa.Integer(), sa.ForeignKey("blog_posts.id"), nullable=True),
        sa.Column("brief_id", sa.Integer(), sa.ForeignKey("content_briefs.id"), nullable=True),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("jurisdiction", sa.String(length=64), nullable=True),
        sa.Column("claim_type", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_legal_claims_organization_id", "legal_claims", ["organization_id"])
    op.create_index("ix_legal_claims_status", "legal_claims", ["status"])
    op.create_index("ix_legal_claims_content_piece_id", "legal_claims", ["content_piece_id"])
    op.create_index("ix_legal_claims_blog_post_id", "legal_claims", ["blog_post_id"])
    op.create_index("ix_legal_claims_brief_id", "legal_claims", ["brief_id"])

    op.create_table(
        "legal_evidences",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("claim_id", sa.Integer(), sa.ForeignKey("legal_claims.id"), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("source_title", sa.String(length=512), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("evidence_type", sa.String(length=64), nullable=True),
        sa.Column("jurisdiction", sa.String(length=64), nullable=True),
        sa.Column("verified_by", sa.String(length=128), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_legal_evidences_organization_id", "legal_evidences", ["organization_id"])
    op.create_index("ix_legal_evidences_claim_id", "legal_evidences", ["claim_id"])


def downgrade() -> None:
    op.drop_table("legal_evidences")
    op.drop_table("legal_claims")
    op.drop_table("content_briefs")
    op.drop_table("prompt_templates")
    op.drop_table("seo_keyword_clusters")
