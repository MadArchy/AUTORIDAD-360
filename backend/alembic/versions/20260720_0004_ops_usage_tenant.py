"""Add tenant scope to operational tasks, decisions and AI usage.

Revision ID: 20260720_0004
Revises: 20260720_0003
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260720_0004"
down_revision = "20260720_0003"
branch_labels = None
depends_on = None


def _add_org_column(table: str) -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns(table)}
    if "organization_id" in columns:
        return
    op.add_column(
        table,
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.id"),
            nullable=True,
        ),
    )
    op.create_index(
        f"ix_{table}_organization_id",
        table,
        ["organization_id"],
        unique=False,
    )


def upgrade() -> None:
    for table in ("editorial_tasks", "decision_logs", "ai_usage_logs"):
        _add_org_column(table)

    op.execute(
        "UPDATE editorial_tasks SET organization_id = "
        "(SELECT organization_id FROM calendar_slots "
        "WHERE calendar_slots.id = editorial_tasks.slot_id) "
        "WHERE editorial_tasks.organization_id IS NULL"
    )
    pilot_org = "(SELECT id FROM organizations WHERE slug = 'agencia-piloto' LIMIT 1)"
    for table in ("decision_logs", "ai_usage_logs"):
        op.execute(
            f"UPDATE {table} SET organization_id = {pilot_org} "
            "WHERE organization_id IS NULL"
        )


def downgrade() -> None:
    for table in ("ai_usage_logs", "decision_logs", "editorial_tasks"):
        op.drop_index(f"ix_{table}_organization_id", table_name=table)
        op.drop_column(table, "organization_id")
