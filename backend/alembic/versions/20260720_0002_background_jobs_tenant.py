"""Scope background jobs by organization.

Revision ID: 20260720_0002
Revises: 20260720_0001
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260720_0002"
down_revision = "20260720_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("background_jobs")}
    if "organization_id" not in columns:
        op.add_column(
            "background_jobs",
            sa.Column(
                "organization_id",
                sa.Integer(),
                sa.ForeignKey("organizations.id"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_background_jobs_organization_id",
            "background_jobs",
            ["organization_id"],
            unique=False,
        )

    constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(
            "background_jobs"
        )
    }
    if "uq_background_jobs_name_key" in constraints:
        op.drop_constraint(
            "uq_background_jobs_name_key",
            "background_jobs",
            type_="unique",
        )
    if "uq_background_jobs_org_name_key" not in constraints:
        op.create_unique_constraint(
            "uq_background_jobs_org_name_key",
            "background_jobs",
            ["organization_id", "job_name", "idempotency_key"],
        )


def downgrade() -> None:
    op.drop_constraint(
        "uq_background_jobs_org_name_key",
        "background_jobs",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_background_jobs_name_key",
        "background_jobs",
        ["job_name", "idempotency_key"],
    )
    op.drop_index(
        "ix_background_jobs_organization_id",
        table_name="background_jobs",
    )
    op.drop_column("background_jobs", "organization_id")
