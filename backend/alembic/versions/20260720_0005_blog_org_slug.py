"""Blog slug unique per organization; backfill null orgs.

Revision ID: 20260720_0005
Revises: 20260720_0004
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260720_0005"
down_revision = "20260720_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    pilot = "(SELECT id FROM organizations WHERE slug = 'agencia-piloto' LIMIT 1)"
    op.execute(
        f"UPDATE blog_posts SET organization_id = {pilot} "
        "WHERE organization_id IS NULL"
    )

    for uc in inspector.get_unique_constraints("blog_posts"):
        name = uc.get("name") or ""
        cols = set(uc.get("column_names") or [])
        if cols == {"slug"} and name:
            op.drop_constraint(name, "blog_posts", type_="unique")

    for ix in inspector.get_indexes("blog_posts"):
        name = ix.get("name") or ""
        cols = set(ix.get("column_names") or [])
        if ix.get("unique") and cols == {"slug"} and name and "org" not in name.lower():
            op.drop_index(name, table_name="blog_posts")

    uniques = {
        uc["name"]
        for uc in sa.inspect(bind).get_unique_constraints("blog_posts")
    }
    if "uq_blog_posts_org_slug" not in uniques:
        op.create_unique_constraint(
            "uq_blog_posts_org_slug",
            "blog_posts",
            ["organization_id", "slug"],
        )


def downgrade() -> None:
    op.drop_constraint("uq_blog_posts_org_slug", "blog_posts", type_="unique")
    op.create_unique_constraint("blog_posts_slug_key", "blog_posts", ["slug"])
