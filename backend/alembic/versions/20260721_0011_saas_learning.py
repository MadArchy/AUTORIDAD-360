"""Fase 5 SaaS — planes, white-label, refresh.

Revision ID: 20260721_0011
Revises: 20260721_0010
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260721_0011"
down_revision = "20260721_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("plan_code", sa.String(length=32), nullable=True, server_default="pilot"),
    )
    op.add_column("organizations", sa.Column("plan_limits_json", sa.JSON(), nullable=True))
    op.add_column("organizations", sa.Column("branding_json", sa.JSON(), nullable=True))

    op.create_table(
        "custom_domains",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("hostname", sa.String(length=256), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("hostname", name="uq_custom_domains_hostname"),
    )
    op.create_index("ix_custom_domains_organization_id", "custom_domains", ["organization_id"])
    op.create_index("ix_custom_domains_status", "custom_domains", ["status"])

    op.create_table(
        "content_refresh_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("piece_id", sa.Integer(), sa.ForeignKey("content_pieces.id"), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("professional_profiles.id"), nullable=True),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("due_at", sa.DateTime(), nullable=True),
        sa.Column("source_piece_version", sa.Integer(), nullable=True),
        sa.Column("new_piece_id", sa.Integer(), sa.ForeignKey("content_pieces.id"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("decided_by", sa.String(length=128), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_content_refresh_items_organization_id",
        "content_refresh_items",
        ["organization_id"],
    )
    op.create_index("ix_content_refresh_items_piece_id", "content_refresh_items", ["piece_id"])
    op.create_index("ix_content_refresh_items_status", "content_refresh_items", ["status"])


def downgrade() -> None:
    op.drop_table("content_refresh_items")
    op.drop_table("custom_domains")
    op.drop_column("organizations", "branding_json")
    op.drop_column("organizations", "plan_limits_json")
    op.drop_column("organizations", "plan_code")
