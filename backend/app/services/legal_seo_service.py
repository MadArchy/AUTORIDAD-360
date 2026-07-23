"""Servicios Fase 3 — clusters, briefs, claims/evidencias, prompts."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.legal_seo import (
    ContentBrief,
    LegalClaim,
    LegalEvidence,
    PromptTemplate,
    SeoKeywordCluster,
)
from app.schemas.legal_seo import (
    ContentBriefCreate,
    KeywordClusterCreate,
    LegalClaimCreate,
    LegalEvidenceCreate,
    PromptTemplateCreate,
)


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "item")[:120]


def create_keyword_cluster(
    db: Session,
    *,
    organization_id: int,
    data: KeywordClusterCreate,
) -> SeoKeywordCluster:
    slug = _slugify(data.name)
    base = slug
    n = 1
    while (
        db.query(SeoKeywordCluster)
        .filter(
            SeoKeywordCluster.organization_id == organization_id,
            SeoKeywordCluster.slug == slug,
        )
        .first()
    ):
        n += 1
        slug = f"{base}-{n}"
    row = SeoKeywordCluster(
        organization_id=organization_id,
        slug=slug,
        name=data.name.strip(),
        primary_keyword=data.primary_keyword.strip(),
        keywords_json=[k.strip() for k in data.keywords if k.strip()][:40],
        search_intent=data.search_intent,
        jurisdiction=data.jurisdiction,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_content_brief(
    db: Session,
    *,
    organization_id: int,
    data: ContentBriefCreate,
) -> ContentBrief:
    cluster = None
    if data.cluster_id:
        cluster = (
            db.query(SeoKeywordCluster)
            .filter(
                SeoKeywordCluster.id == data.cluster_id,
                SeoKeywordCluster.organization_id == organization_id,
            )
            .first()
        )
        if not cluster:
            raise ValueError("Keyword cluster not found")

    primary = data.primary_keyword or (cluster.primary_keyword if cluster else None)
    secondary = data.secondary_keywords or (
        list(cluster.keywords_json or []) if cluster else []
    )
    jurisdiction = data.jurisdiction or (cluster.jurisdiction if cluster else "MX")
    slug = _slugify(data.title)
    brief_payload = {
        "audience": data.audience,
        "angle": data.angle,
        "primary_keyword": primary,
        "secondary_keywords": secondary,
        "sections": [s.model_dump() for s in data.sections],
        "jurisdiction": jurisdiction,
        "version_notes": "v1",
    }
    row = ContentBrief(
        organization_id=organization_id,
        cluster_id=cluster.id if cluster else None,
        title=data.title.strip(),
        slug=slug,
        jurisdiction=jurisdiction,
        status="draft",
        version=1,
        brief_json=brief_payload,
        created_by=data.created_by,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_prompt_template(
    db: Session,
    *,
    organization_id: int | None,
    data: PromptTemplateCreate,
) -> PromptTemplate:
    existing = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.organization_id == organization_id,
            PromptTemplate.name == data.name,
            PromptTemplate.version == data.version,
        )
        .first()
    )
    if existing:
        raise ValueError("Prompt template version already exists")
    row = PromptTemplate(
        organization_id=organization_id,
        name=data.name.strip(),
        channel=data.channel,
        version=data.version,
        body=data.body,
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_legal_claim(
    db: Session,
    *,
    organization_id: int,
    data: LegalClaimCreate,
) -> LegalClaim:
    row = LegalClaim(
        organization_id=organization_id,
        content_piece_id=data.content_piece_id,
        blog_post_id=data.blog_post_id,
        brief_id=data.brief_id,
        claim_text=data.claim_text.strip(),
        jurisdiction=data.jurisdiction,
        claim_type=data.claim_type,
        status="pending",
        risk_level=data.risk_level,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def add_legal_evidence(
    db: Session,
    *,
    organization_id: int,
    data: LegalEvidenceCreate,
) -> LegalEvidence:
    claim = (
        db.query(LegalClaim)
        .filter(
            LegalClaim.id == data.claim_id,
            LegalClaim.organization_id == organization_id,
        )
        .first()
    )
    if not claim:
        raise ValueError("Claim not found")
    row = LegalEvidence(
        organization_id=organization_id,
        claim_id=claim.id,
        source_url=data.source_url.strip(),
        source_title=data.source_title,
        excerpt=data.excerpt,
        evidence_type=data.evidence_type,
        jurisdiction=data.jurisdiction,
        verified_by=data.verified_by,
        verified_at=datetime.utcnow() if data.verified_by else None,
    )
    db.add(row)
    if claim.status == "pending" and data.verified_by:
        claim.status = "needs_review"
    db.commit()
    db.refresh(row)
    return row


def extract_claims_from_content_piece(
    db: Session,
    *,
    organization_id: int,
    piece_id: int,
    jurisdiction: str = "MX",
) -> list[LegalClaim]:
    """Materializa claims factuales de una pieza (reutiliza content_review)."""
    from app.models.content import ContentPiece
    from app.services.content_review import extract_factual_claim_texts

    piece = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == piece_id,
            ContentPiece.organization_id == organization_id,
        )
        .first()
    )
    if not piece:
        raise ValueError("Content piece not found")

    texts = extract_factual_claim_texts(piece)
    created: list[LegalClaim] = []
    for text in texts:
        exists = (
            db.query(LegalClaim)
            .filter(
                LegalClaim.organization_id == organization_id,
                LegalClaim.content_piece_id == piece_id,
                LegalClaim.claim_text == text,
            )
            .first()
        )
        if exists:
            continue
        row = LegalClaim(
            organization_id=organization_id,
            content_piece_id=piece_id,
            claim_text=text,
            jurisdiction=jurisdiction,
            claim_type="factual",
            status="pending",
            risk_level="yellow",
            meta_json={"source": "content_review.extract_factual_claim_texts"},
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
        # Adjunta evidencia candidata desde la URL fuente (no marca supported sola).
        if piece.source_url:
            try:
                add_legal_evidence(
                    db,
                    organization_id=organization_id,
                    data=LegalEvidenceCreate(
                        claim_id=row.id,
                        source_url=piece.source_url,
                        source_title=f"Fuente de la pieza #{piece.id}",
                        excerpt=(piece.body_text or "")[:400] or None,
                        verified_by=None,
                    ),
                )
            except Exception:  # noqa: BLE001
                pass
    return created


def update_claim_status(
    db: Session,
    *,
    organization_id: int,
    claim_id: int,
    status: str,
    actor: str,
) -> LegalClaim:
    claim = (
        db.query(LegalClaim)
        .filter(
            LegalClaim.id == claim_id,
            LegalClaim.organization_id == organization_id,
        )
        .first()
    )
    if not claim:
        raise ValueError("Claim not found")
    if status == "supported":
        evidence_count = (
            db.query(LegalEvidence)
            .filter(LegalEvidence.claim_id == claim.id)
            .count()
        )
        if evidence_count < 1:
            raise ValueError("Cannot mark supported without at least one evidence")
    claim.status = status
    claim.meta_json = {
        **(claim.meta_json or {}),
        "last_status_actor": actor,
        "last_status_at": datetime.utcnow().isoformat(),
    }
    db.commit()
    db.refresh(claim)
    return claim


def cluster_to_dict(row: SeoKeywordCluster) -> dict[str, Any]:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "slug": row.slug,
        "name": row.name,
        "primary_keyword": row.primary_keyword,
        "keywords": row.keywords_json or [],
        "search_intent": row.search_intent,
        "jurisdiction": row.jurisdiction,
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def brief_to_dict(row: ContentBrief) -> dict[str, Any]:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "cluster_id": row.cluster_id,
        "title": row.title,
        "slug": row.slug,
        "jurisdiction": row.jurisdiction,
        "status": row.status,
        "version": row.version,
        "brief": row.brief_json,
        "created_by": row.created_by,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def claim_to_dict(db: Session, row: LegalClaim) -> dict[str, Any]:
    evidences = (
        db.query(LegalEvidence)
        .filter(LegalEvidence.claim_id == row.id)
        .order_by(LegalEvidence.id.asc())
        .all()
    )
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "content_piece_id": row.content_piece_id,
        "blog_post_id": row.blog_post_id,
        "brief_id": row.brief_id,
        "claim_text": row.claim_text,
        "jurisdiction": row.jurisdiction,
        "claim_type": row.claim_type,
        "status": row.status,
        "risk_level": row.risk_level,
        "evidences": [
            {
                "id": e.id,
                "source_url": e.source_url,
                "source_title": e.source_title,
                "excerpt": e.excerpt,
                "evidence_type": e.evidence_type,
                "jurisdiction": e.jurisdiction,
                "verified_by": e.verified_by,
                "verified_at": e.verified_at.isoformat() if e.verified_at else None,
            }
            for e in evidences
        ],
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def resolve_generation_prompt(
    db: Session,
    *,
    organization_id: int | None,
    channel: str,
    format_kwargs: dict[str, Any],
    fallback: str,
) -> tuple[str, int | None]:
    """Usa prompt versionado activo `generate_content` si existe; si no, fallback."""
    q = (
        db.query(PromptTemplate)
        .filter(
            PromptTemplate.name == "generate_content",
            PromptTemplate.is_active.is_(True),
            PromptTemplate.channel.in_([channel, "all", format_kwargs.get("format_type", channel)]),
        )
    )
    if organization_id is not None:
        rows = q.filter(
            (PromptTemplate.organization_id == organization_id)
            | (PromptTemplate.organization_id.is_(None))
        ).all()
    else:
        rows = q.filter(PromptTemplate.organization_id.is_(None)).all()
    if not rows:
        return fallback.format(**format_kwargs), None
    # Prefer org-specific, then highest version
    rows.sort(
        key=lambda r: (0 if r.organization_id == organization_id else 1, -int(r.version or 0))
    )
    chosen = rows[0]
    try:
        return chosen.body.format(**format_kwargs), chosen.id
    except (KeyError, ValueError):
        return fallback.format(**format_kwargs), chosen.id


def prompt_to_dict(row: PromptTemplate) -> dict[str, Any]:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "name": row.name,
        "channel": row.channel,
        "version": row.version,
        "body": row.body,
        "is_active": row.is_active,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def seed_channel_prompt_templates(
    db: Session, *, organization_id: int | None = None
) -> list[PromptTemplate]:
    """Prompts versionados por canal (idempotente por org+name+channel).

    Nota: el UNIQUE DB es (org, name, version); usamos versiones distintas por canal.
    """
    defaults = [
        (
            "generate_content",
            "linkedin",
            1,
            "Eres redactor de autoridad. Formato LinkedIn. Tema: {topic}. Fuente: {source_url}. Canal: linkedin.",
        ),
        (
            "generate_content",
            "newsletter",
            2,
            "Eres redactor de autoridad. Formato newsletter. Tema: {topic}. Fuente: {source_url}. Canal: newsletter.",
        ),
        (
            "generate_content",
            "carousel",
            3,
            "Eres redactor de autoridad. Formato carrusel 5 slides. Tema: {topic}. Fuente: {source_url}. Canal: carousel.",
        ),
        (
            "generate_content",
            "all",
            4,
            "Eres redactor de autoridad multi-formato. Tema: {topic}. Fuente: {source_url}.",
        ),
    ]
    created: list[PromptTemplate] = []
    for name, channel, version, body in defaults:
        exists = (
            db.query(PromptTemplate)
            .filter(
                PromptTemplate.organization_id == organization_id,
                PromptTemplate.name == name,
                PromptTemplate.channel == channel,
            )
            .first()
        )
        if exists:
            continue
        # Evitar chocar UNIQUE (org, name, version)
        while (
            db.query(PromptTemplate)
            .filter(
                PromptTemplate.organization_id == organization_id,
                PromptTemplate.name == name,
                PromptTemplate.version == version,
            )
            .first()
        ):
            version += 10
        row = PromptTemplate(
            organization_id=organization_id,
            name=name,
            channel=channel,
            version=version,
            body=body,
            is_active=True,
        )
        db.add(row)
        created.append(row)
    if created:
        db.commit()
        for row in created:
            db.refresh(row)
    return created
