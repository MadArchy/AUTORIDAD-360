"""Schemas Pydantic — Fase 3 SEO + Legal Authority."""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


ALLOWED_JURISDICTIONS = frozenset({"MX", "US", "MX-US", "EU", "LATAM", "global"})
ALLOWED_INTENTS = frozenset(
    {"informational", "commercial", "transactional", "navigational"}
)
ALLOWED_CLAIM_TYPES = frozenset(
    {"factual", "legal_opinion", "regulatory", "citation"}
)
ALLOWED_CLAIM_STATUSES = frozenset(
    {"pending", "supported", "unsupported", "needs_review", "withdrawn"}
)


class KeywordClusterCreate(BaseModel):
    name: str = Field(min_length=2, max_length=256)
    primary_keyword: str = Field(min_length=2, max_length=256)
    keywords: list[str] = Field(default_factory=list)
    search_intent: str = "informational"
    jurisdiction: str = "MX"

    @field_validator("search_intent")
    @classmethod
    def _intent(cls, v: str) -> str:
        if v not in ALLOWED_INTENTS:
            raise ValueError(f"search_intent must be one of {sorted(ALLOWED_INTENTS)}")
        return v

    @field_validator("jurisdiction")
    @classmethod
    def _jur(cls, v: str) -> str:
        if v not in ALLOWED_JURISDICTIONS:
            raise ValueError(f"jurisdiction must be one of {sorted(ALLOWED_JURISDICTIONS)}")
        return v


class BriefSection(BaseModel):
    heading: str = Field(min_length=2, max_length=256)
    notes: str = Field(default="", max_length=4000)
    must_cover: list[str] = Field(default_factory=list)


class ContentBriefCreate(BaseModel):
    title: str = Field(min_length=4, max_length=512)
    cluster_id: int | None = None
    jurisdiction: str = "MX"
    audience: str = Field(default="GC / consejo / compliance", max_length=256)
    angle: str = Field(default="", max_length=1024)
    sections: list[BriefSection] = Field(default_factory=list)
    primary_keyword: str | None = None
    secondary_keywords: list[str] = Field(default_factory=list)
    created_by: str | None = Field(default=None, max_length=128)

    @field_validator("jurisdiction")
    @classmethod
    def _jur(cls, v: str) -> str:
        if v not in ALLOWED_JURISDICTIONS:
            raise ValueError(f"jurisdiction must be one of {sorted(ALLOWED_JURISDICTIONS)}")
        return v


class PromptTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    channel: str = Field(default="blog", max_length=64)
    body: str = Field(min_length=20)
    version: int = Field(default=1, ge=1)


class LegalClaimCreate(BaseModel):
    claim_text: str = Field(min_length=10, max_length=4000)
    jurisdiction: str = "MX"
    claim_type: str = "factual"
    content_piece_id: int | None = None
    blog_post_id: int | None = None
    brief_id: int | None = None
    risk_level: str = "yellow"

    @field_validator("jurisdiction")
    @classmethod
    def _jur(cls, v: str) -> str:
        if v not in ALLOWED_JURISDICTIONS:
            raise ValueError(f"jurisdiction must be one of {sorted(ALLOWED_JURISDICTIONS)}")
        return v

    @field_validator("claim_type")
    @classmethod
    def _ctype(cls, v: str) -> str:
        if v not in ALLOWED_CLAIM_TYPES:
            raise ValueError(f"claim_type must be one of {sorted(ALLOWED_CLAIM_TYPES)}")
        return v


class LegalEvidenceCreate(BaseModel):
    claim_id: int
    source_url: str = Field(min_length=8, max_length=1024)
    source_title: str | None = Field(default=None, max_length=512)
    excerpt: str | None = Field(default=None, max_length=4000)
    evidence_type: str = "primary_source"
    jurisdiction: str = "MX"
    verified_by: str | None = Field(default=None, max_length=128)

    @field_validator("source_url")
    @classmethod
    def _url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("source_url must be http(s)")
        return v

    @field_validator("jurisdiction")
    @classmethod
    def _jur(cls, v: str) -> str:
        if v not in ALLOWED_JURISDICTIONS:
            raise ValueError(f"jurisdiction must be one of {sorted(ALLOWED_JURISDICTIONS)}")
        return v


class ClaimStatusUpdate(BaseModel):
    status: str
    actor: str = Field(min_length=2, max_length=128)

    @field_validator("status")
    @classmethod
    def _st(cls, v: str) -> str:
        if v not in ALLOWED_CLAIM_STATUSES:
            raise ValueError(f"status must be one of {sorted(ALLOWED_CLAIM_STATUSES)}")
        return v
