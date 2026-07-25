"""Notas de tendencias sociales / publicidad orgánica en el perfil.

Revision ID: 20260724_0013
Revises: 20260724_0012
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260724_0013"
down_revision = "20260724_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "professional_profiles",
        sa.Column("ad_trend_notes_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("professional_profiles", "ad_trend_notes_json")
