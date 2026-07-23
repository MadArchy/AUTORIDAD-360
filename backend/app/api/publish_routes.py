"""API de publicación multi-canal."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.publishing import ChannelAccount, MediaAsset, PublishJob, PublishPackage
from app.services.publish_service import (
    SUPPORTED_CHANNELS,
    account_to_dict,
    connect_channel_account,
    create_package_from_calendar_slot,
    create_publish_package_from_source,
    disconnect_channel_account,
    ensure_default_accounts,
    execute_native_publish_job,
    list_unified_schedule,
    mark_job_published,
    media_to_dict,
    package_to_dict,
    schedule_publish_job,
)
from app.services.publish_adapters import supported_native_channels
from app.services.tenant import TenantContext, get_tenant_context, require_roles

router = APIRouter(prefix="/api/v1", tags=["publishing"])

_PUBLISH_STAFF = (
    "agency_admin",
    "strategist",
    "writer",
    "editor",
    "community_manager",
)


class CreatePackageRequest(BaseModel):
    source_type: str = Field(pattern="^(content_piece|blog_post)$")
    source_id: int
    channels: list[str] = Field(default_factory=lambda: ["linkedin", "facebook", "instagram", "blog"])
    media_asset_ids: list[int] = Field(default_factory=list)


class MediaCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=256)
    storage_url: str = Field(min_length=8, max_length=1024)
    kind: str = "image"
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    aspect_ratio: str | None = None
    alt_text: str | None = None


class ConfirmPublishRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    external_url: str | None = None
    external_post_id: str | None = None


class ScheduleJobRequest(BaseModel):
    scheduled_at: datetime
    calendar_slot_id: int | None = None


class FromSlotRequest(BaseModel):
    channels: list[str] | None = None
    media_asset_ids: list[int] = Field(default_factory=list)


class ConnectAccountRequest(BaseModel):
    access_token: str = Field(min_length=8, max_length=4096)
    external_account_id: str | None = Field(default=None, max_length=256)
    prefer_live: bool = False


class ExecuteJobRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    force_live: bool | None = None


@router.get("/publish/channels")
def list_channels(ctx: TenantContext = Depends(get_tenant_context)):
    require_roles(ctx, *_PUBLISH_STAFF)
    return {
        "channels": list(SUPPORTED_CHANNELS),
        "native_adapters": supported_native_channels(),
        "notes": {
            "blog": "Publicación nativa en el blog de la plataforma",
            "linkedin": "Nativo (dry-run/live) si la cuenta está connected; si no, asistido",
            "facebook": "Dry-run con token Graph; live en sprint siguiente",
            "instagram": "Dry-run con token Graph; live en sprint siguiente",
            "tiktok": "Dry-run con token; live pendiente",
            "youtube": "Dry-run con OAuth; upload live pendiente",
            "x": "Modo asistido; post corto",
            "newsletter": "Modo asistido; asunto + cuerpo",
        },
    }


@router.get("/publish/accounts")
def list_accounts(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    rows = ensure_default_accounts(db, ctx.org_id)
    return [account_to_dict(r) for r in rows]


@router.post("/publish/media")
def create_media(
    body: MediaCreateRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    url = str(body.storage_url).strip()
    if not (url.startswith("http://") or url.startswith("https://") or url.startswith("/")):
        raise HTTPException(400, "storage_url must be http(s) or local path")
    asset = MediaAsset(
        organization_id=ctx.org_id,
        kind=body.kind,
        title=body.title,
        storage_url=url,
        mime_type=body.mime_type,
        width=body.width,
        height=body.height,
        aspect_ratio=body.aspect_ratio,
        alt_text=body.alt_text,
        status="ready",
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return media_to_dict(asset)


@router.get("/publish/media")
def list_media(
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    rows = (
        db.query(MediaAsset)
        .filter(MediaAsset.organization_id == ctx.org_id)
        .order_by(MediaAsset.id.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    return [media_to_dict(r) for r in rows]


@router.post("/publish/packages")
def create_package(
    body: CreatePackageRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    try:
        package = create_publish_package_from_source(
            db,
            organization_id=ctx.org_id,
            source_type=body.source_type,
            source_id=body.source_id,
            channels=body.channels,
            media_asset_ids=body.media_asset_ids,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return package_to_dict(db, package)


@router.get("/publish/packages")
def list_packages(
    limit: int = 20,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    rows = (
        db.query(PublishPackage)
        .filter(PublishPackage.organization_id == ctx.org_id)
        .order_by(PublishPackage.id.desc())
        .limit(max(1, min(limit, 50)))
        .all()
    )
    return [package_to_dict(db, row) for row in rows]


@router.get("/publish/packages/{package_id}")
def get_package(
    package_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    package = (
        db.query(PublishPackage)
        .filter(
            PublishPackage.id == package_id,
            PublishPackage.organization_id == ctx.org_id,
        )
        .first()
    )
    if not package:
        raise HTTPException(404, "Package not found")
    return package_to_dict(db, package)


@router.post("/publish/jobs/{job_id}/confirm")
def confirm_job(
    job_id: int,
    body: ConfirmPublishRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    job = (
        db.query(PublishJob)
        .filter(
            PublishJob.id == job_id,
            PublishJob.organization_id == ctx.org_id,
        )
        .first()
    )
    if not job:
        raise HTTPException(404, "Publish job not found")
    job = mark_job_published(
        db,
        job=job,
        external_url=body.external_url,
        external_post_id=body.external_post_id,
        actor=body.actor,
    )
    return {
        "job": {
            "id": job.id,
            "status": job.status,
            "external_url": job.external_url,
            "published_at": job.published_at.isoformat() if job.published_at else None,
        }
    }


@router.post("/publish/jobs/{job_id}/schedule")
def schedule_job(
    job_id: int,
    body: ScheduleJobRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    job = (
        db.query(PublishJob)
        .filter(
            PublishJob.id == job_id,
            PublishJob.organization_id == ctx.org_id,
        )
        .first()
    )
    if not job:
        raise HTTPException(404, "Publish job not found")
    try:
        job = schedule_publish_job(
            db,
            job=job,
            scheduled_at=body.scheduled_at,
            calendar_slot_id=body.calendar_slot_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"job": _job_response(job)}


@router.post("/publish/from-slot/{slot_id}")
def package_from_slot(
    slot_id: int,
    body: FromSlotRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    try:
        package = create_package_from_calendar_slot(
            db,
            organization_id=ctx.org_id,
            slot_id=slot_id,
            channels=body.channels,
            media_asset_ids=body.media_asset_ids or None,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return package_to_dict(db, package)


@router.get("/publish/schedule")
def publish_schedule(
    days: int = 14,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    return list_unified_schedule(db, organization_id=ctx.org_id, days=days)


@router.post("/publish/accounts/{account_id}/connect")
def connect_account(
    account_id: int,
    body: ConnectAccountRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, "agency_admin", "community_manager", "strategist")
    account = (
        db.query(ChannelAccount)
        .filter(
            ChannelAccount.id == account_id,
            ChannelAccount.organization_id == ctx.org_id,
        )
        .first()
    )
    if not account:
        raise HTTPException(404, "Channel account not found")
    try:
        account = connect_channel_account(
            db,
            account=account,
            access_token=body.access_token,
            external_account_id=body.external_account_id,
            prefer_live=body.prefer_live,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return account_to_dict(account)


@router.post("/publish/accounts/{account_id}/disconnect")
def disconnect_account(
    account_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, "agency_admin", "community_manager", "strategist")
    account = (
        db.query(ChannelAccount)
        .filter(
            ChannelAccount.id == account_id,
            ChannelAccount.organization_id == ctx.org_id,
        )
        .first()
    )
    if not account:
        raise HTTPException(404, "Channel account not found")
    return account_to_dict(disconnect_channel_account(db, account=account))


@router.post("/publish/jobs/{job_id}/execute")
def execute_job(
    job_id: int,
    body: ExecuteJobRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_PUBLISH_STAFF)
    job = (
        db.query(PublishJob)
        .filter(
            PublishJob.id == job_id,
            PublishJob.organization_id == ctx.org_id,
        )
        .first()
    )
    if not job:
        raise HTTPException(404, "Publish job not found")
    try:
        result = execute_native_publish_job(
            db,
            job=job,
            actor=body.actor,
            force_live=body.force_live,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return result


def _job_response(job: PublishJob) -> dict:
    return {
        "id": job.id,
        "channel": job.channel,
        "status": job.status,
        "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
        "calendar_slot_id": job.calendar_slot_id,
        "external_url": job.external_url,
        "published_at": job.published_at.isoformat() if job.published_at else None,
    }
