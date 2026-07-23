"""Auth sessions + publishing tables.

Revision ID: 20260721_0006
Revises: 20260720_0005
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260721_0006"
down_revision = "20260720_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id"), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_jti", "auth_sessions", ["jti"], unique=True)
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table(
        "channel_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("account_label", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("external_account_id", sa.String(length=256), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "organization_id",
            "channel",
            "account_label",
            name="uq_channel_accounts_org_channel_label",
        ),
    )
    op.create_index("ix_channel_accounts_organization_id", "channel_accounts", ["organization_id"])
    op.create_index("ix_channel_accounts_channel", "channel_accounts", ["channel"])

    op.create_table(
        "media_assets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("storage_url", sa.String(length=1024), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("alt_text", sa.String(length=512), nullable=True),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_media_assets_organization_id", "media_assets", ["organization_id"])

    op.create_table(
        "publish_packages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("brief_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_publish_packages_organization_id", "publish_packages", ["organization_id"])
    op.create_index("ix_publish_packages_source_id", "publish_packages", ["source_id"])
    op.create_index("ix_publish_packages_status", "publish_packages", ["status"])

    op.create_table(
        "channel_variants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("package_id", sa.Integer(), sa.ForeignKey("publish_packages.id"), nullable=False),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("format_hint", sa.String(length=64), nullable=False),
        sa.Column("headline", sa.String(length=512), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("hashtags_json", sa.JSON(), nullable=True),
        sa.Column("cta_text", sa.String(length=256), nullable=True),
        sa.Column("media_asset_ids_json", sa.JSON(), nullable=True),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_channel_variants_organization_id", "channel_variants", ["organization_id"])
    op.create_index("ix_channel_variants_package_id", "channel_variants", ["package_id"])
    op.create_index("ix_channel_variants_channel", "channel_variants", ["channel"])

    op.create_table(
        "publish_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("variant_id", sa.Integer(), sa.ForeignKey("channel_variants.id"), nullable=False),
        sa.Column("channel_account_id", sa.Integer(), sa.ForeignKey("channel_accounts.id"), nullable=True),
        sa.Column("channel", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("external_post_id", sa.String(length=256), nullable=True),
        sa.Column("external_url", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_publish_jobs_organization_id", "publish_jobs", ["organization_id"])
    op.create_index("ix_publish_jobs_variant_id", "publish_jobs", ["variant_id"])
    op.create_index("ix_publish_jobs_channel", "publish_jobs", ["channel"])
    op.create_index("ix_publish_jobs_status", "publish_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("publish_jobs")
    op.drop_table("channel_variants")
    op.drop_table("publish_packages")
    op.drop_table("media_assets")
    op.drop_table("channel_accounts")
    op.drop_table("auth_sessions")
