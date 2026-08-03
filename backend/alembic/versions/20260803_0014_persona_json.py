"""Persona canónica Juan (voz compartida) en professional_profiles.

Revision ID: 20260803_0014
Revises: 20260724_0013
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260803_0014"
down_revision = "20260724_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "professional_profiles",
        sa.Column("persona_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("professional_profiles", "persona_json")
