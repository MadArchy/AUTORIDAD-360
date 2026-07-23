"""Motor de publicación multi-canal (asistido primero; APIs después)."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.models.content import ContentPiece
from app.models.editorial import BlogPost
from app.models.publishing import (
    ChannelAccount,
    ChannelVariant,
    MediaAsset,
    PublishJob,
    PublishPackage,
)

SUPPORTED_CHANNELS = (
    "blog",
    "linkedin",
    "facebook",
    "instagram",
    "tiktok",
    "youtube",
    "x",
    "newsletter",
)

CHANNEL_DEFAULTS: dict[str, dict[str, str]] = {
    "blog": {"format_hint": "article", "aspect_ratio": "16:9"},
    "linkedin": {"format_hint": "post", "aspect_ratio": "1:1"},
    "facebook": {"format_hint": "post", "aspect_ratio": "1:1"},
    "instagram": {"format_hint": "carousel", "aspect_ratio": "4:5"},
    "tiktok": {"format_hint": "reel", "aspect_ratio": "9:16"},
    "youtube": {"format_hint": "short", "aspect_ratio": "9:16"},
    "x": {"format_hint": "post", "aspect_ratio": "16:9"},
    "newsletter": {"format_hint": "newsletter", "aspect_ratio": "16:9"},
}


def ensure_default_accounts(db: Session, organization_id: int) -> list[ChannelAccount]:
    existing = {
        (a.channel, a.account_label): a
        for a in db.query(ChannelAccount)
        .filter(ChannelAccount.organization_id == organization_id)
        .all()
    }
    created: list[ChannelAccount] = []
    for channel in SUPPORTED_CHANNELS:
        key = (channel, "default")
        if key in existing:
            created.append(existing[key])
            continue
        row = ChannelAccount(
            organization_id=organization_id,
            channel=channel,
            account_label="default",
            status="assisted" if channel != "blog" else "connected",
            meta_json={"mode": "assisted" if channel != "blog" else "native"},
        )
        db.add(row)
        created.append(row)
    db.commit()
    for row in created:
        db.refresh(row)
    return created


def _source_payload(
    db: Session,
    *,
    source_type: str,
    source_id: int,
    organization_id: int,
) -> dict[str, Any]:
    if source_type == "content_piece":
        piece = (
            db.query(ContentPiece)
            .filter(
                ContentPiece.id == source_id,
                ContentPiece.organization_id == organization_id,
            )
            .first()
        )
        if not piece:
            raise ValueError("Content piece not found")
        return {
            "title": piece.title,
            "body": piece.body_text,
            "format_type": piece.format_type,
            "source_url": piece.source_url,
            "status": piece.status,
        }
    if source_type == "blog_post":
        post = (
            db.query(BlogPost)
            .filter(
                BlogPost.id == source_id,
                BlogPost.organization_id == organization_id,
            )
            .first()
        )
        if not post:
            raise ValueError("Blog post not found")
        return {
            "title": post.title,
            "body": post.content_html,
            "format_type": "blog",
            "source_url": post.source_url,
            "status": post.status,
            "slug": post.slug,
        }
    raise ValueError(f"Unsupported source_type: {source_type}")


def _variant_copy(channel: str, title: str, body: str, source_url: str | None) -> dict[str, Any]:
    plain = (
        str(body or "")
        .replace("<br />", "\n")
        .replace("<br/>", "\n")
        .replace("</p>", "\n")
    )
    import re

    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = re.sub(r"\s+", " ", plain).strip()
    defaults = CHANNEL_DEFAULTS[channel]
    if channel == "linkedin":
        text = f"{title}\n\n{plain[:1200]}"
        if source_url:
            text += f"\n\nFuente: {source_url}"
        text += "\n\n#IA #Gobernanza #Cumplimiento"
    elif channel in {"facebook", "instagram"}:
        text = f"{title}\n\n{plain[:900]}"
        if source_url:
            text += f"\n\nMás detalle: {source_url}"
    elif channel == "tiktok":
        text = f"Hook: {title[:80]}\nScript corto (30-45s):\n1) Problema\n2) Qué cambió\n3) Qué debe revisar la empresa\nCTA: comenta 'checklist'"
    elif channel == "youtube":
        text = (
            f"Título sugerido: {title[:90]}\n\nDescripción:\n{plain[:1500]}\n\n"
            "Capítulos sugeridos:\n00:00 Contexto\n00:20 Qué ocurrió\n00:45 Implicaciones\n01:10 Checklist"
        )
    elif channel == "x":
        text = f"{title[:200]}\n\n{plain[:160]}"
        if source_url:
            text = f"{text}\n{source_url}"[:270]
    elif channel == "newsletter":
        text = f"Asunto: {title}\n\n{plain[:2000]}"
    else:  # blog
        text = plain or title
    return {
        "headline": title[:512],
        "body_text": text,
        "format_hint": defaults["format_hint"],
        "aspect_ratio": defaults["aspect_ratio"],
        "hashtags": ["IA", "Gobernanza", "Empresas"] if channel != "blog" else [],
        "cta_text": "Agenda una revisión de preparación de IA",
        "assisted_checklist": [
            "Revisar tono y jurisdicción",
            "Adjuntar imagen/video con ratio correcto",
            "Confirmar CTA y hashtags",
            "Publicar o programar en la app nativa si el canal es asistido",
        ],
    }


def create_publish_package_from_source(
    db: Session,
    *,
    organization_id: int,
    source_type: str,
    source_id: int,
    channels: list[str] | None = None,
    media_asset_ids: list[int] | None = None,
) -> PublishPackage:
    ensure_default_accounts(db, organization_id)
    source = _source_payload(
        db,
        source_type=source_type,
        source_id=source_id,
        organization_id=organization_id,
    )
    selected = [c for c in (channels or ["linkedin", "facebook", "instagram", "blog"]) if c in SUPPORTED_CHANNELS]
    if not selected:
        raise ValueError("No valid channels selected")

    if media_asset_ids:
        count = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.organization_id == organization_id,
                MediaAsset.id.in_(media_asset_ids),
            )
            .count()
        )
        if count != len(set(media_asset_ids)):
            raise ValueError("One or more media assets were not found for this organization")

    package = PublishPackage(
        organization_id=organization_id,
        source_type=source_type,
        source_id=source_id,
        title=str(source["title"])[:512],
        status="ready",
        brief_json={
            "source_status": source.get("status"),
            "source_url": source.get("source_url"),
            "channels": selected,
        },
    )
    db.add(package)
    db.flush()

    for channel in selected:
        copy = _variant_copy(
            channel,
            str(source["title"]),
            str(source.get("body") or ""),
            source.get("source_url"),
        )
        variant = ChannelVariant(
            organization_id=organization_id,
            package_id=package.id,
            channel=channel,
            format_hint=copy["format_hint"],
            headline=copy["headline"],
            body_text=copy["body_text"],
            hashtags_json=copy["hashtags"],
            cta_text=copy["cta_text"],
            media_asset_ids_json=media_asset_ids or [],
            aspect_ratio=copy["aspect_ratio"],
            status="ready",
            payload_json={
                "assisted_checklist": copy["assisted_checklist"],
                "mode": "assisted" if channel != "blog" else "native",
            },
        )
        db.add(variant)
        db.flush()
        account = (
            db.query(ChannelAccount)
            .filter(
                ChannelAccount.organization_id == organization_id,
                ChannelAccount.channel == channel,
                ChannelAccount.account_label == "default",
            )
            .first()
        )
        job = PublishJob(
            organization_id=organization_id,
            variant_id=variant.id,
            channel_account_id=account.id if account else None,
            channel=channel,
            status="assisted_ready" if channel != "blog" else "queued",
            result_json={"mode": "assisted" if channel != "blog" else "native"},
        )
        db.add(job)

    db.commit()
    db.refresh(package)
    return package


def mark_job_published(
    db: Session,
    *,
    job: PublishJob,
    external_url: str | None = None,
    external_post_id: str | None = None,
    actor: str | None = None,
) -> PublishJob:
    job.status = "published"
    job.published_at = datetime.utcnow()
    job.external_url = external_url
    job.external_post_id = external_post_id
    job.result_json = {
        **(job.result_json or {}),
        "confirmed_by": actor,
        "confirmed_at": datetime.utcnow().isoformat(),
    }
    package = (
        db.query(PublishPackage)
        .join(ChannelVariant, ChannelVariant.package_id == PublishPackage.id)
        .filter(ChannelVariant.id == job.variant_id)
        .first()
    )
    if package:
        jobs = (
            db.query(PublishJob)
            .join(ChannelVariant, ChannelVariant.id == PublishJob.variant_id)
            .filter(ChannelVariant.package_id == package.id)
            .all()
        )
        if jobs and all(j.status == "published" for j in jobs):
            package.status = "published"
        else:
            package.status = "partially_published"

    slot_id = job.calendar_slot_id
    if slot_id:
        sibling_jobs = (
            db.query(PublishJob)
            .filter(
                PublishJob.calendar_slot_id == slot_id,
                PublishJob.organization_id == job.organization_id,
            )
            .all()
        )
        if sibling_jobs and all(j.status == "published" for j in sibling_jobs):
            from app.models.operations import CalendarSlot
            from app.services.calendar_ops import advance_slot

            slot = (
                db.query(CalendarSlot)
                .filter(
                    CalendarSlot.id == slot_id,
                    CalendarSlot.organization_id == job.organization_id,
                )
                .first()
            )
            if slot and slot.status == "scheduled":
                try:
                    advance_slot(
                        db,
                        slot,
                        "published",
                        actor or "publish-confirm",
                        reason="Todos los publish_jobs del slot confirmados",
                        risk_override=True,
                    )
                except ValueError:
                    pass
                else:
                    db.refresh(job)
                    return job

    db.commit()
    db.refresh(job)
    return job


def package_to_dict(db: Session, package: PublishPackage) -> dict[str, Any]:
    variants = (
        db.query(ChannelVariant)
        .filter(ChannelVariant.package_id == package.id)
        .order_by(ChannelVariant.id.asc())
        .all()
    )
    jobs = (
        db.query(PublishJob)
        .filter(PublishJob.variant_id.in_([v.id for v in variants] or [-1]))
        .all()
    )
    jobs_by_variant = {j.variant_id: j for j in jobs}
    return {
        "id": package.id,
        "organization_id": package.organization_id,
        "source_type": package.source_type,
        "source_id": package.source_id,
        "title": package.title,
        "status": package.status,
        "brief": package.brief_json,
        "created_at": package.created_at.isoformat() if package.created_at else None,
        "variants": [
            {
                "id": v.id,
                "channel": v.channel,
                "format_hint": v.format_hint,
                "headline": v.headline,
                "body_text": v.body_text,
                "hashtags": v.hashtags_json or [],
                "cta_text": v.cta_text,
                "cta_url": getattr(v, "cta_url", None),
                "cta_service_offer_id": getattr(v, "cta_service_offer_id", None),
                "media_asset_ids": v.media_asset_ids_json or [],
                "aspect_ratio": v.aspect_ratio,
                "status": v.status,
                "payload": v.payload_json,
                "job": _job_dict(jobs_by_variant.get(v.id)),
            }
            for v in variants
        ],
    }


def _job_dict(job: PublishJob | None) -> dict[str, Any] | None:
    if not job:
        return None
    return {
        "id": job.id,
        "channel": job.channel,
        "status": job.status,
        "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else None,
        "calendar_slot_id": job.calendar_slot_id,
        "external_url": job.external_url,
        "external_post_id": job.external_post_id,
        "error_message": job.error_message,
        "result": job.result_json,
        "published_at": job.published_at.isoformat() if job.published_at else None,
    }


FORMAT_TO_CHANNELS: dict[str, list[str]] = {
    "linkedin": ["linkedin"],
    "carousel": ["instagram", "facebook"],
    "newsletter": ["newsletter"],
    "video_script": ["youtube", "tiktok"],
    "blog": ["blog"],
}


def schedule_publish_job(
    db: Session,
    *,
    job: PublishJob,
    scheduled_at: datetime,
    calendar_slot_id: int | None = None,
) -> PublishJob:
    if job.status == "published":
        raise ValueError("Cannot reschedule a published job")
    job.scheduled_at = scheduled_at
    if calendar_slot_id is not None:
        job.calendar_slot_id = calendar_slot_id
    if job.status in {"queued", "assisted_ready"}:
        job.status = "assisted_ready" if job.channel != "blog" else "queued"
    job.result_json = {
        **(job.result_json or {}),
        "scheduled": True,
        "scheduled_at": scheduled_at.isoformat(),
    }
    db.commit()
    db.refresh(job)
    return job


def create_package_from_calendar_slot(
    db: Session,
    *,
    organization_id: int,
    slot_id: int,
    channels: list[str] | None = None,
    media_asset_ids: list[int] | None = None,
) -> PublishPackage:
    from app.models.operations import CalendarSlot

    slot = (
        db.query(CalendarSlot)
        .filter(
            CalendarSlot.id == slot_id,
            CalendarSlot.organization_id == organization_id,
        )
        .first()
    )
    if not slot:
        raise ValueError("Calendar slot not found")
    if not slot.piece_id:
        raise ValueError("Slot has no content piece attached")

    selected = channels or FORMAT_TO_CHANNELS.get(slot.format_type, ["linkedin"])
    package = create_publish_package_from_source(
        db,
        organization_id=organization_id,
        source_type="content_piece",
        source_id=slot.piece_id,
        channels=selected,
        media_asset_ids=media_asset_ids,
    )
    jobs = (
        db.query(PublishJob)
        .join(ChannelVariant, ChannelVariant.id == PublishJob.variant_id)
        .filter(ChannelVariant.package_id == package.id)
        .all()
    )
    for job in jobs:
        job.calendar_slot_id = slot.id
        job.scheduled_at = slot.scheduled_at
    package.brief_json = {
        **(package.brief_json or {}),
        "calendar_slot_id": slot.id,
        "slot_format": slot.format_type,
        "slot_title": slot.title,
    }
    db.commit()
    db.refresh(package)
    return package


def list_unified_schedule(
    db: Session,
    *,
    organization_id: int,
    days: int = 14,
) -> dict[str, Any]:
    from app.models.operations import CalendarSlot

    now = datetime.utcnow()
    horizon = now + timedelta(days=max(1, min(days, 60)))
    past = now - timedelta(days=2)

    jobs = (
        db.query(PublishJob)
        .filter(
            PublishJob.organization_id == organization_id,
            PublishJob.scheduled_at.isnot(None),
            PublishJob.scheduled_at >= past,
            PublishJob.scheduled_at <= horizon,
        )
        .order_by(PublishJob.scheduled_at.asc())
        .all()
    )
    slots = (
        db.query(CalendarSlot)
        .filter(
            CalendarSlot.organization_id == organization_id,
            CalendarSlot.scheduled_at >= past,
            CalendarSlot.scheduled_at <= horizon,
        )
        .order_by(CalendarSlot.scheduled_at.asc())
        .all()
    )
    return {
        "from": past.isoformat(),
        "to": horizon.isoformat(),
        "publish_jobs": [_job_dict(j) for j in jobs],
        "calendar_slots": [
            {
                "id": s.id,
                "title": s.title,
                "format_type": s.format_type,
                "channel": s.channel,
                "status": s.status,
                "piece_id": s.piece_id,
                "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
                "risk_level": s.risk_level,
            }
            for s in slots
        ],
    }


def media_to_dict(asset: MediaAsset) -> dict[str, Any]:
    return {
        "id": asset.id,
        "organization_id": asset.organization_id,
        "kind": asset.kind,
        "title": asset.title,
        "storage_url": asset.storage_url,
        "mime_type": asset.mime_type,
        "width": asset.width,
        "height": asset.height,
        "aspect_ratio": asset.aspect_ratio,
        "alt_text": asset.alt_text,
        "status": asset.status,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }


def account_to_dict(account: ChannelAccount) -> dict[str, Any]:
    meta = dict(account.meta_json or {})
    has_token = bool(meta.pop("encrypted_access_token", None))
    meta.pop("access_token", None)
    return {
        "id": account.id,
        "organization_id": account.organization_id,
        "channel": account.channel,
        "account_label": account.account_label,
        "status": account.status,
        "external_account_id": account.external_account_id,
        "has_credentials": has_token,
        "native_ready": account.status == "connected" and has_token,
        "meta": meta,
    }


def connect_channel_account(
    db: Session,
    *,
    account: ChannelAccount,
    access_token: str,
    external_account_id: str | None = None,
    prefer_live: bool = False,
) -> ChannelAccount:
    from app.services.crypto_keys import encrypt_secret

    token = access_token.strip()
    if len(token) < 8:
        raise ValueError("access_token demasiado corto")
    meta = dict(account.meta_json or {})
    meta["encrypted_access_token"] = encrypt_secret(token)
    meta["mode"] = "native"
    meta["prefer_live"] = prefer_live
    meta["connected_at"] = datetime.utcnow().isoformat()
    account.meta_json = meta
    account.status = "connected"
    if external_account_id:
        account.external_account_id = external_account_id.strip()[:256]
    account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(account)
    return account


def disconnect_channel_account(db: Session, *, account: ChannelAccount) -> ChannelAccount:
    meta = dict(account.meta_json or {})
    meta.pop("encrypted_access_token", None)
    meta.pop("access_token", None)
    meta["mode"] = "assisted"
    meta["disconnected_at"] = datetime.utcnow().isoformat()
    account.meta_json = meta
    account.status = "assisted"
    account.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(account)
    return account


def _account_access_token(account: ChannelAccount | None) -> str | None:
    if not account or not account.meta_json:
        return None
    enc = account.meta_json.get("encrypted_access_token")
    if not enc:
        return None
    from app.services.crypto_keys import decrypt_secret

    try:
        return decrypt_secret(enc)
    except Exception:  # noqa: BLE001
        return None


def execute_native_publish_job(
    db: Session,
    *,
    job: PublishJob,
    actor: str,
    force_live: bool | None = None,
) -> dict[str, Any]:
    """Intenta adaptador nativo; si no aplica, indica assisted_required."""
    from app.config import settings
    from app.services.publish_adapters import get_adapter

    if job.status == "published":
        raise ValueError("Job already published")

    adapter = get_adapter(job.channel)
    if not adapter:
        return {
            "ok": False,
            "mode": "assisted_required",
            "message": f"Canal {job.channel} sin adaptador nativo; confirma en modo asistido",
        }

    account = None
    if job.channel_account_id:
        account = (
            db.query(ChannelAccount)
            .filter(ChannelAccount.id == job.channel_account_id)
            .first()
        )
    variant = db.query(ChannelVariant).filter(ChannelVariant.id == job.variant_id).first()
    if not variant:
        raise ValueError("Variant not found")

    media_urls: list[str] = []
    ids = variant.media_asset_ids_json or []
    if ids:
        assets = (
            db.query(MediaAsset)
            .filter(
                MediaAsset.organization_id == job.organization_id,
                MediaAsset.id.in_(ids),
            )
            .all()
        )
        media_urls = [a.storage_url for a in assets]

    prefer_live = bool((account.meta_json or {}).get("prefer_live")) if account else False
    live = settings.publish_native_live if force_live is None else force_live
    if prefer_live and force_live is None:
        live = settings.publish_native_live and prefer_live

    result = adapter.publish(
        body_text=variant.body_text,
        headline=variant.headline,
        access_token=_account_access_token(account),
        external_account_id=account.external_account_id if account else None,
        live=bool(live),
        media_urls=media_urls,
    )

    job.attempt_count = (job.attempt_count or 0) + 1
    job.result_json = {
        **(job.result_json or {}),
        "adapter": result.mode,
        "adapter_message": result.message,
        "adapter_raw": result.raw,
        "executed_by": actor,
        "executed_at": datetime.utcnow().isoformat(),
    }

    if result.ok:
        job = mark_job_published(
            db,
            job=job,
            external_url=result.external_url,
            external_post_id=result.external_post_id,
            actor=actor,
        )
        return {
            "ok": True,
            "mode": result.mode,
            "message": result.message,
            "job": _job_dict(job),
        }

    job.status = "assisted_ready" if result.mode == "assisted_required" else "failed"
    if result.mode != "assisted_required":
        job.error_message = result.message[:2000]
    db.commit()
    db.refresh(job)
    return {
        "ok": False,
        "mode": result.mode,
        "message": result.message,
        "job": _job_dict(job),
    }
