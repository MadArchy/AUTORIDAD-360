"""Baseline del esquema canónico Autoridad 360.

Revision ID: 20260720_0001
Revises:
Create Date: 2026-07-20

Esta revisión permite crear una base vacía con Alembic en Postgres o MySQL.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "20260720_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import app.models  # noqa: F401
    from app.db.database import Base

    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    # El baseline no elimina todas las tablas automáticamente: un downgrade
    # destructivo debe hacerse con respaldo y una migración explícita.
    return None
