"""Scope editorial source uniqueness by organization.

Revision ID: 20260720_0003
Revises: 20260720_0002
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260720_0003"
down_revision = "20260720_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pilot_org = "(SELECT id FROM organizations WHERE slug = 'agencia-piloto' LIMIT 1)"
    for table in (
        "news_categories",
        "news_articles",
        "weekly_reports",
        "blog_posts",
        "content_packages",
        "content_pieces",
        "background_jobs",
    ):
        op.execute(
            f"UPDATE {table} SET organization_id = {pilot_org} "
            "WHERE organization_id IS NULL"
        )

    category_constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(
            "news_categories"
        )
    }
    if "uq_news_categories_org_slug" not in category_constraints:
        op.create_unique_constraint(
            "uq_news_categories_org_slug",
            "news_categories",
            ["organization_id", "slug"],
        )

    article_constraints = {
        constraint["name"]
        for constraint in sa.inspect(op.get_bind()).get_unique_constraints(
            "news_articles"
        )
    }
    for legacy_name in (
        "news_articles_source_url_key",
        "news_articles_content_hash_key",
    ):
        if legacy_name in article_constraints:
            op.drop_constraint(legacy_name, "news_articles", type_="unique")
    if "uq_news_articles_org_source_url" not in article_constraints:
        op.create_unique_constraint(
            "uq_news_articles_org_source_url",
            "news_articles",
            ["organization_id", "source_url"],
        )
    if "uq_news_articles_org_content_hash" not in article_constraints:
        op.create_unique_constraint(
            "uq_news_articles_org_content_hash",
            "news_articles",
            ["organization_id", "content_hash"],
        )


def downgrade() -> None:
    op.drop_constraint(
        "uq_news_articles_org_content_hash",
        "news_articles",
        type_="unique",
    )
    op.drop_constraint(
        "uq_news_articles_org_source_url",
        "news_articles",
        type_="unique",
    )
    op.create_unique_constraint(
        "news_articles_content_hash_key",
        "news_articles",
        ["content_hash"],
    )
    op.create_unique_constraint(
        "news_articles_source_url_key",
        "news_articles",
        ["source_url"],
    )
    op.drop_constraint(
        "uq_news_categories_org_slug",
        "news_categories",
        type_="unique",
    )
