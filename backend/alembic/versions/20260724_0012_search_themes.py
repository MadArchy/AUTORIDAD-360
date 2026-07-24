"""Temas de búsqueda editables en el perfil profesional.

Revision ID: 20260724_0012
Revises: 20260721_0011
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260724_0012"
down_revision = "20260721_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "professional_profiles",
        sa.Column("search_themes_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("professional_profiles", "search_themes_json")
