"""Fase 4 marketing & attribution.

Revision ID: 20260721_0010
Revises: 20260721_0009
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260721_0010"
down_revision = "20260721_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "service_offers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("professional_profiles.id"), nullable=True),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("organization_id", "slug", name="uq_service_offers_org_slug"),
    )
    op.create_index("ix_service_offers_organization_id", "service_offers", ["organization_id"])
    op.create_index("ix_service_offers_profile_id", "service_offers", ["profile_id"])
    op.create_index("ix_service_offers_status", "service_offers", ["status"])

    op.create_table(
        "campaign_links",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=False),
        sa.Column("base_url", sa.String(length=1024), nullable=False),
        sa.Column("utm_source", sa.String(length=128), nullable=True),
        sa.Column("utm_medium", sa.String(length=128), nullable=True),
        sa.Column("utm_campaign", sa.String(length=128), nullable=True),
        sa.Column("utm_content", sa.String(length=128), nullable=True),
        sa.Column("utm_term", sa.String(length=128), nullable=True),
        sa.Column("tracked_url", sa.String(length=2048), nullable=False),
        sa.Column("piece_id", sa.Integer(), sa.ForeignKey("content_pieces.id"), nullable=True),
        sa.Column("channel_variant_id", sa.Integer(), sa.ForeignKey("channel_variants.id"), nullable=True),
        sa.Column("service_offer_id", sa.Integer(), sa.ForeignKey("service_offers.id"), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_campaign_links_organization_id", "campaign_links", ["organization_id"])

    op.create_table(
        "newsletter_subscribers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("profile_id", sa.Integer(), sa.ForeignKey("professional_profiles.id"), nullable=True),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("source_channel", sa.String(length=64), nullable=True),
        sa.Column("utm_source", sa.String(length=128), nullable=True),
        sa.Column("utm_medium", sa.String(length=128), nullable=True),
        sa.Column("utm_campaign", sa.String(length=128), nullable=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint(
            "organization_id",
            "email",
            name="uq_newsletter_subscribers_org_email",
        ),
    )
    op.create_index(
        "ix_newsletter_subscribers_organization_id",
        "newsletter_subscribers",
        ["organization_id"],
    )
    op.create_index("ix_newsletter_subscribers_profile_id", "newsletter_subscribers", ["profile_id"])
    op.create_index("ix_newsletter_subscribers_status", "newsletter_subscribers", ["status"])

    # Leads — attribution spine
    op.add_column("leads", sa.Column("publish_job_id", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("channel_variant_id", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("service_offer_id", sa.Integer(), nullable=True))
    op.add_column("leads", sa.Column("utm_source", sa.String(length=128), nullable=True))
    op.add_column("leads", sa.Column("utm_medium", sa.String(length=128), nullable=True))
    op.add_column("leads", sa.Column("utm_campaign", sa.String(length=128), nullable=True))
    op.add_column("leads", sa.Column("utm_content", sa.String(length=128), nullable=True))
    op.add_column("leads", sa.Column("utm_term", sa.String(length=128), nullable=True))
    op.add_column("leads", sa.Column("landing_url", sa.String(length=1024), nullable=True))
    op.create_foreign_key(
        "fk_leads_publish_job_id", "leads", "publish_jobs", ["publish_job_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_leads_channel_variant_id",
        "leads",
        "channel_variants",
        ["channel_variant_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_leads_service_offer_id",
        "leads",
        "service_offers",
        ["service_offer_id"],
        ["id"],
    )

    # Engagements — channel-scoped insights
    op.add_column("content_engagements", sa.Column("channel", sa.String(length=32), nullable=True))
    op.add_column("content_engagements", sa.Column("publish_job_id", sa.Integer(), nullable=True))
    op.add_column(
        "content_engagements",
        sa.Column("external_post_id", sa.String(length=256), nullable=True),
    )
    op.add_column("content_engagements", sa.Column("clicks", sa.Integer(), nullable=True))
    op.add_column("content_engagements", sa.Column("saves", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_content_engagements_publish_job_id",
        "content_engagements",
        "publish_jobs",
        ["publish_job_id"],
        ["id"],
    )

    # Channel variants — CTA URL + service
    op.add_column("channel_variants", sa.Column("cta_url", sa.String(length=1024), nullable=True))
    op.add_column("channel_variants", sa.Column("cta_service_offer_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_channel_variants_cta_service_offer_id",
        "channel_variants",
        "service_offers",
        ["cta_service_offer_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_channel_variants_cta_service_offer_id", "channel_variants", type_="foreignkey")
    op.drop_column("channel_variants", "cta_service_offer_id")
    op.drop_column("channel_variants", "cta_url")

    op.drop_constraint(
        "fk_content_engagements_publish_job_id", "content_engagements", type_="foreignkey"
    )
    op.drop_column("content_engagements", "saves")
    op.drop_column("content_engagements", "clicks")
    op.drop_column("content_engagements", "external_post_id")
    op.drop_column("content_engagements", "publish_job_id")
    op.drop_column("content_engagements", "channel")

    op.drop_constraint("fk_leads_service_offer_id", "leads", type_="foreignkey")
    op.drop_constraint("fk_leads_channel_variant_id", "leads", type_="foreignkey")
    op.drop_constraint("fk_leads_publish_job_id", "leads", type_="foreignkey")
    op.drop_column("leads", "landing_url")
    op.drop_column("leads", "utm_term")
    op.drop_column("leads", "utm_content")
    op.drop_column("leads", "utm_campaign")
    op.drop_column("leads", "utm_medium")
    op.drop_column("leads", "utm_source")
    op.drop_column("leads", "service_offer_id")
    op.drop_column("leads", "channel_variant_id")
    op.drop_column("leads", "publish_job_id")

    op.drop_table("newsletter_subscribers")
    op.drop_table("campaign_links")
    op.drop_table("service_offers")
