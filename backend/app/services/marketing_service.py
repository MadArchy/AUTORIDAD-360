"""Fase 4 — ofertas, UTM builder, suscriptores."""
from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.orm import Session

from app.models.marketing import CampaignLink, NewsletterSubscriber, ServiceOffer
from app.models.publishing import ChannelVariant
from app.schemas.marketing import (
    CampaignLinkCreate,
    NewsletterSubscriberCreate,
    NewsletterSubscriberUpdate,
    ServiceOfferCreate,
    ServiceOfferUpdate,
    VariantCtaUpdate,
)


def _slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[áàäâ]", "a", s)
    s = re.sub(r"[éèëê]", "e", s)
    s = re.sub(r"[íìïî]", "i", s)
    s = re.sub(r"[óòöô]", "o", s)
    s = re.sub(r"[úùüû]", "u", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:120] or "offer"


def build_tracked_url(
    base_url: str,
    *,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_content: str | None = None,
    utm_term: str | None = None,
) -> str:
    """Merge UTM params into base_url (existing query preserved; UTMs overwrite)."""
    parsed = urlparse(base_url.strip())
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    mapping = {
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_campaign": utm_campaign,
        "utm_content": utm_content,
        "utm_term": utm_term,
    }
    for key, value in mapping.items():
        if value is not None and str(value).strip():
            params[key] = str(value).strip()
    query = urlencode(params)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment)
    )


def create_service_offer(
    db: Session, *, organization_id: int, data: ServiceOfferCreate
) -> ServiceOffer:
    slug = (data.slug or _slugify(data.name)).strip().lower()
    base = slug
    n = 1
    while (
        db.query(ServiceOffer)
        .filter(
            ServiceOffer.organization_id == organization_id,
            ServiceOffer.slug == slug,
        )
        .first()
    ):
        n += 1
        slug = f"{base}-{n}"
    row = ServiceOffer(
        organization_id=organization_id,
        profile_id=data.profile_id,
        slug=slug,
        name=data.name.strip(),
        description=data.description,
        status=data.status or "active",
        meta_json=data.meta_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_service_offers(
    db: Session, *, organization_id: int, status: str | None = None, limit: int = 50
) -> list[ServiceOffer]:
    q = db.query(ServiceOffer).filter(ServiceOffer.organization_id == organization_id)
    if status:
        q = q.filter(ServiceOffer.status == status)
    return q.order_by(ServiceOffer.name.asc()).limit(limit).all()


def update_service_offer(
    db: Session, *, organization_id: int, offer_id: int, data: ServiceOfferUpdate
) -> ServiceOffer:
    row = (
        db.query(ServiceOffer)
        .filter(
            ServiceOffer.id == offer_id,
            ServiceOffer.organization_id == organization_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Service offer not found")
    if data.name is not None:
        row.name = data.name.strip()
    if data.description is not None:
        row.description = data.description
    if data.status is not None:
        row.status = data.status
    if data.meta_json is not None:
        row.meta_json = data.meta_json
    db.commit()
    db.refresh(row)
    return row


def seed_offers_from_profile_services(
    db: Session, *, organization_id: int, profile_id: int, services: list[str]
) -> list[ServiceOffer]:
    """Idempotent: create active offers for profile service strings that lack a slug match."""
    created: list[ServiceOffer] = []
    for name in services or []:
        if not str(name).strip():
            continue
        slug = _slugify(str(name))
        exists = (
            db.query(ServiceOffer)
            .filter(
                ServiceOffer.organization_id == organization_id,
                ServiceOffer.slug == slug,
            )
            .first()
        )
        if exists:
            continue
        row = ServiceOffer(
            organization_id=organization_id,
            profile_id=profile_id,
            slug=slug,
            name=str(name).strip(),
            status="active",
        )
        db.add(row)
        created.append(row)
    if created:
        db.commit()
        for row in created:
            db.refresh(row)
    return created


def create_campaign_link(
    db: Session, *, organization_id: int, data: CampaignLinkCreate
) -> CampaignLink:
    if data.service_offer_id:
        offer = (
            db.query(ServiceOffer)
            .filter(
                ServiceOffer.id == data.service_offer_id,
                ServiceOffer.organization_id == organization_id,
            )
            .first()
        )
        if not offer:
            raise ValueError("Service offer not found")
    tracked = build_tracked_url(
        data.base_url,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
        utm_content=data.utm_content,
        utm_term=data.utm_term,
    )
    row = CampaignLink(
        organization_id=organization_id,
        label=data.label.strip(),
        base_url=data.base_url.strip(),
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
        utm_content=data.utm_content,
        utm_term=data.utm_term,
        tracked_url=tracked,
        piece_id=data.piece_id,
        channel_variant_id=data.channel_variant_id,
        service_offer_id=data.service_offer_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_campaign_links(
    db: Session, *, organization_id: int, limit: int = 50
) -> list[CampaignLink]:
    return (
        db.query(CampaignLink)
        .filter(CampaignLink.organization_id == organization_id)
        .order_by(CampaignLink.created_at.desc())
        .limit(limit)
        .all()
    )


def create_newsletter_subscriber(
    db: Session, *, organization_id: int, data: NewsletterSubscriberCreate
) -> NewsletterSubscriber:
    existing = (
        db.query(NewsletterSubscriber)
        .filter(
            NewsletterSubscriber.organization_id == organization_id,
            NewsletterSubscriber.email == data.email,
        )
        .first()
    )
    if existing:
        raise ValueError("Subscriber already exists")
    row = NewsletterSubscriber(
        organization_id=organization_id,
        profile_id=data.profile_id,
        email=data.email,
        status=data.status or "pending",
        source_channel=data.source_channel,
        utm_source=data.utm_source,
        utm_medium=data.utm_medium,
        utm_campaign=data.utm_campaign,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_newsletter_subscribers(
    db: Session, *, organization_id: int, status: str | None = None, limit: int = 100
) -> list[NewsletterSubscriber]:
    q = db.query(NewsletterSubscriber).filter(
        NewsletterSubscriber.organization_id == organization_id
    )
    if status:
        q = q.filter(NewsletterSubscriber.status == status)
    return q.order_by(NewsletterSubscriber.created_at.desc()).limit(limit).all()


def update_newsletter_subscriber(
    db: Session,
    *,
    organization_id: int,
    subscriber_id: int,
    data: NewsletterSubscriberUpdate,
) -> NewsletterSubscriber:
    row = (
        db.query(NewsletterSubscriber)
        .filter(
            NewsletterSubscriber.id == subscriber_id,
            NewsletterSubscriber.organization_id == organization_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Subscriber not found")
    row.status = data.status
    if data.source_channel is not None:
        row.source_channel = data.source_channel
    db.commit()
    db.refresh(row)
    return row


def update_variant_cta(
    db: Session, *, organization_id: int, variant_id: int, data: VariantCtaUpdate
) -> ChannelVariant:
    row = (
        db.query(ChannelVariant)
        .filter(
            ChannelVariant.id == variant_id,
            ChannelVariant.organization_id == organization_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Variant not found")
    if data.cta_text is not None:
        row.cta_text = data.cta_text
    if data.cta_url is not None:
        row.cta_url = data.cta_url
    if data.cta_service_offer_id is not None:
        if data.cta_service_offer_id == 0:
            row.cta_service_offer_id = None
        else:
            offer = (
                db.query(ServiceOffer)
                .filter(
                    ServiceOffer.id == data.cta_service_offer_id,
                    ServiceOffer.organization_id == organization_id,
                )
                .first()
            )
            if not offer:
                raise ValueError("Service offer not found")
            row.cta_service_offer_id = offer.id
    db.commit()
    db.refresh(row)
    return row


def offer_to_dict(row: ServiceOffer) -> dict:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "profile_id": row.profile_id,
        "slug": row.slug,
        "name": row.name,
        "description": row.description,
        "status": row.status,
        "meta_json": row.meta_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def link_to_dict(row: CampaignLink) -> dict:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "label": row.label,
        "base_url": row.base_url,
        "utm_source": row.utm_source,
        "utm_medium": row.utm_medium,
        "utm_campaign": row.utm_campaign,
        "utm_content": row.utm_content,
        "utm_term": row.utm_term,
        "tracked_url": row.tracked_url,
        "piece_id": row.piece_id,
        "channel_variant_id": row.channel_variant_id,
        "service_offer_id": row.service_offer_id,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def subscriber_to_dict(row: NewsletterSubscriber) -> dict:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "profile_id": row.profile_id,
        "email": row.email,
        "status": row.status,
        "source_channel": row.source_channel,
        "utm_source": row.utm_source,
        "utm_medium": row.utm_medium,
        "utm_campaign": row.utm_campaign,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }
