"""Schemas Pydantic — Fase 4 marketing / atribución."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ServiceOfferCreate(BaseModel):
    name: str = Field(min_length=2, max_length=256)
    slug: str | None = Field(default=None, max_length=128)
    description: str | None = None
    profile_id: int | None = None
    status: str = "active"
    meta_json: dict | None = None


class ServiceOfferUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=256)
    description: str | None = None
    status: str | None = None
    meta_json: dict | None = None


class CampaignLinkCreate(BaseModel):
    label: str = Field(min_length=2, max_length=256)
    base_url: str = Field(min_length=8, max_length=1024)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)
    utm_content: str | None = Field(default=None, max_length=128)
    utm_term: str | None = Field(default=None, max_length=128)
    piece_id: int | None = None
    channel_variant_id: int | None = None
    service_offer_id: int | None = None

    @field_validator("base_url")
    @classmethod
    def _http_url(cls, v: str) -> str:
        low = v.strip().lower()
        if not (low.startswith("http://") or low.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.strip()


class UtmPreviewRequest(BaseModel):
    base_url: str = Field(min_length=8, max_length=1024)
    utm_source: str | None = Field(default=None, max_length=128)
    utm_medium: str | None = Field(default=None, max_length=128)
    utm_campaign: str | None = Field(default=None, max_length=128)
    utm_content: str | None = Field(default=None, max_length=128)
    utm_term: str | None = Field(default=None, max_length=128)

    @field_validator("base_url")
    @classmethod
    def _http_url(cls, v: str) -> str:
        low = v.strip().lower()
        if not (low.startswith("http://") or low.startswith("https://")):
            raise ValueError("base_url must start with http:// or https://")
        return v.strip()


class NewsletterSubscriberCreate(BaseModel):
    email: str = Field(min_length=5, max_length=256)
    profile_id: int | None = None
    status: str = "pending"
    source_channel: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        email = v.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("invalid email")
        return email


class NewsletterSubscriberUpdate(BaseModel):
    status: str
    source_channel: str | None = None


class VariantCtaUpdate(BaseModel):
    cta_text: str | None = Field(default=None, max_length=256)
    cta_url: str | None = Field(default=None, max_length=1024)
    cta_service_offer_id: int | None = None
