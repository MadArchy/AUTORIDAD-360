"""Link publish jobs to calendar slots.

Revision ID: 20260721_0007
Revises: 20260721_0006
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260721_0007"
down_revision = "20260721_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "publish_jobs",
        sa.Column("calendar_slot_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_publish_jobs_calendar_slot_id",
        "publish_jobs",
        "calendar_slots",
        ["calendar_slot_id"],
        ["id"],
    )
    op.create_index(
        "ix_publish_jobs_calendar_slot_id",
        "publish_jobs",
        ["calendar_slot_id"],
    )
    op.create_index(
        "ix_publish_jobs_scheduled_at",
        "publish_jobs",
        ["scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_publish_jobs_scheduled_at", table_name="publish_jobs")
    op.drop_index("ix_publish_jobs_calendar_slot_id", table_name="publish_jobs")
    op.drop_constraint("fk_publish_jobs_calendar_slot_id", "publish_jobs", type_="foreignkey")
    op.drop_column("publish_jobs", "calendar_slot_id")
