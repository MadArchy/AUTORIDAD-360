"""Blog SEO fields: author, reviewer, categories, description.

Revision ID: 20260721_0008
Revises: 20260721_0007
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260721_0008"
down_revision = "20260721_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("blog_posts", sa.Column("author_name", sa.String(length=256), nullable=True))
    op.add_column("blog_posts", sa.Column("reviewer_name", sa.String(length=256), nullable=True))
    op.add_column("blog_posts", sa.Column("categories_json", sa.JSON(), nullable=True))
    op.add_column("blog_posts", sa.Column("seo_description", sa.String(length=320), nullable=True))


def downgrade() -> None:
    op.drop_column("blog_posts", "seo_description")
    op.drop_column("blog_posts", "categories_json")
    op.drop_column("blog_posts", "reviewer_name")
    op.drop_column("blog_posts", "author_name")
