"""API Fase 3 — SEO intelligence + Legal Authority Content Engine."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.legal_seo import ContentBrief, LegalClaim, PromptTemplate, SeoKeywordCluster
from app.schemas.legal_seo import (
    ClaimStatusUpdate,
    ContentBriefCreate,
    KeywordClusterCreate,
    LegalClaimCreate,
    LegalEvidenceCreate,
    PromptTemplateCreate,
)
from app.services.legal_seo_service import (
    add_legal_evidence,
    brief_to_dict,
    claim_to_dict,
    cluster_to_dict,
    create_content_brief,
    create_keyword_cluster,
    create_legal_claim,
    create_prompt_template,
    extract_claims_from_content_piece,
    prompt_to_dict,
    seed_channel_prompt_templates,
    update_claim_status,
)
from app.services.tenant import TenantContext, get_tenant_context, require_roles

router = APIRouter(prefix="/api/v1/seo-legal", tags=["seo-legal"])

_STAFF = (
    "agency_admin",
    "strategist",
    "writer",
    "editor",
    "legal_reviewer",
)


class ExtractClaimsRequest(BaseModel):
    jurisdiction: str = Field(default="MX", max_length=64)


@router.get("/jurisdictions")
def list_jurisdictions(ctx: TenantContext = Depends(get_tenant_context)):
    require_roles(ctx, *_STAFF)
    return {
        "jurisdictions": ["MX", "US", "MX-US", "EU", "LATAM", "global"],
        "note": "No marcar claims como 'verificado jurídico' solo por overlap léxico",
    }


@router.get("/clusters")
def list_clusters(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    rows = (
        db.query(SeoKeywordCluster)
        .filter(SeoKeywordCluster.organization_id == ctx.org_id)
        .order_by(SeoKeywordCluster.id.desc())
        .limit(100)
        .all()
    )
    return [cluster_to_dict(r) for r in rows]


@router.post("/clusters")
def post_cluster(
    body: KeywordClusterCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    return cluster_to_dict(
        create_keyword_cluster(db, organization_id=ctx.org_id, data=body)
    )


@router.get("/briefs")
def list_briefs(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    rows = (
        db.query(ContentBrief)
        .filter(ContentBrief.organization_id == ctx.org_id)
        .order_by(ContentBrief.id.desc())
        .limit(50)
        .all()
    )
    return [brief_to_dict(r) for r in rows]


@router.post("/briefs")
def post_brief(
    body: ContentBriefCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    try:
        row = create_content_brief(db, organization_id=ctx.org_id, data=body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return brief_to_dict(row)


@router.get("/briefs/{brief_id}")
def get_brief(
    brief_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    row = (
        db.query(ContentBrief)
        .filter(ContentBrief.id == brief_id, ContentBrief.organization_id == ctx.org_id)
        .first()
    )
    if not row:
        raise HTTPException(404, "Brief not found")
    return brief_to_dict(row)


@router.get("/prompts")
def list_prompts(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    rows = (
        db.query(PromptTemplate)
        .filter(
            (PromptTemplate.organization_id == ctx.org_id)
            | (PromptTemplate.organization_id.is_(None))
        )
        .order_by(PromptTemplate.name.asc(), PromptTemplate.version.desc())
        .limit(100)
        .all()
    )
    return [prompt_to_dict(r) for r in rows]


@router.post("/prompts")
def post_prompt(
    body: PromptTemplateCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, "agency_admin", "strategist", "legal_reviewer")
    try:
        row = create_prompt_template(db, organization_id=ctx.org_id, data=body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return prompt_to_dict(row)


@router.post("/prompts/seed-channels")
def seed_prompts(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, "agency_admin", "strategist")
    rows = seed_channel_prompt_templates(db, organization_id=ctx.org_id)
    return {"created": [prompt_to_dict(r) for r in rows], "count": len(rows)}


@router.get("/claims")
def list_claims(
    status: str | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    q = db.query(LegalClaim).filter(LegalClaim.organization_id == ctx.org_id)
    if status:
        q = q.filter(LegalClaim.status == status)
    rows = q.order_by(LegalClaim.id.desc()).limit(100).all()
    return [claim_to_dict(db, r) for r in rows]


class ExtractClaimsRequest(BaseModel):
    jurisdiction: str = "MX"


@router.post("/claims/from-piece/{piece_id}")
def extract_from_piece(
    piece_id: int,
    body: ExtractClaimsRequest | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Extrae claims factuales desde una content_piece (no genera SEO masivo)."""
    require_roles(ctx, *_STAFF)
    jur = (body.jurisdiction if body else "MX")
    try:
        rows = extract_claims_from_content_piece(
            db,
            organization_id=ctx.org_id,
            piece_id=piece_id,
            jurisdiction=jur,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {
        "piece_id": piece_id,
        "created": len(rows),
        "claims": [claim_to_dict(db, r) for r in rows],
    }


@router.post("/claims")
def post_claim(
    body: LegalClaimCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    return claim_to_dict(
        db, create_legal_claim(db, organization_id=ctx.org_id, data=body)
    )


@router.post("/evidences")
def post_evidence(
    body: LegalEvidenceCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)
    try:
        row = add_legal_evidence(db, organization_id=ctx.org_id, data=body)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    claim = db.query(LegalClaim).filter(LegalClaim.id == row.claim_id).first()
    return claim_to_dict(db, claim) if claim else {"evidence_id": row.id}


@router.post("/claims/{claim_id}/status")
def post_claim_status(
    claim_id: int,
    body: ClaimStatusUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, "agency_admin", "legal_reviewer", "editor", "strategist")
    try:
        claim = update_claim_status(
            db,
            organization_id=ctx.org_id,
            claim_id=claim_id,
            status=body.status,
            actor=body.actor,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return claim_to_dict(db, claim)
