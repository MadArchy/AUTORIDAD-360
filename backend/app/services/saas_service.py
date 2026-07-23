"""Fase 5 — branding, dominios y refresh de contenido."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.content import ContentPiece
from app.models.org import Organization
from app.models.saas import ContentRefreshItem, CustomDomain
from app.services.plans import assert_can_add_domain, effective_limits, org_saas_payload


def update_org_plan(
    db: Session, *, org: Organization, plan_code: str, plan_limits_json: dict | None = None
) -> Organization:
    from app.services.plans import normalize_plan_code

    org.plan_code = normalize_plan_code(plan_code)
    if plan_limits_json is not None:
        org.plan_limits_json = plan_limits_json
    db.commit()
    db.refresh(org)
    return org


def update_org_branding(db: Session, *, org: Organization, branding: dict) -> Organization:
    limits = effective_limits(org)
    if not limits.get("white_label"):
        raise ValueError(
            f"Plan '{limits['plan_code']}' no incluye white-label. Sube a Pro/Agency."
        )
    allowed = {
        "display_name",
        "logo_url",
        "primary_color",
        "accent_color",
        "favicon_url",
        "public_tagline",
    }
    clean = {k: v for k, v in (branding or {}).items() if k in allowed}
    current = dict(org.branding_json or {})
    current.update(clean)
    org.branding_json = current
    db.commit()
    db.refresh(org)
    return org


def add_custom_domain(
    db: Session, *, org: Organization, hostname: str, is_primary: bool = False
) -> CustomDomain:
    assert_can_add_domain(db, org)
    host = hostname.strip().lower().rstrip(".")
    if "." not in host or " " in host or host.startswith("http"):
        raise ValueError("hostname inválido (usa dominio sin esquema, ej. blog.cliente.com)")
    exists = db.query(CustomDomain).filter(CustomDomain.hostname == host).first()
    if exists:
        raise ValueError("hostname ya registrado")
    if is_primary:
        db.query(CustomDomain).filter(
            CustomDomain.organization_id == org.id,
            CustomDomain.is_primary.is_(True),
        ).update({"is_primary": False})
    row = CustomDomain(
        organization_id=org.id,
        hostname=host,
        is_primary=is_primary,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_custom_domains(db: Session, *, organization_id: int) -> list[CustomDomain]:
    return (
        db.query(CustomDomain)
        .filter(CustomDomain.organization_id == organization_id)
        .order_by(CustomDomain.is_primary.desc(), CustomDomain.id.asc())
        .all()
    )


def mark_domain_verified(
    db: Session, *, organization_id: int, domain_id: int
) -> CustomDomain:
    row = (
        db.query(CustomDomain)
        .filter(
            CustomDomain.id == domain_id,
            CustomDomain.organization_id == organization_id,
        )
        .first()
    )
    if not row:
        raise ValueError("Domain not found")
    row.status = "verified"
    row.verified_at = datetime.utcnow()
    db.commit()
    db.refresh(row)
    return row


def suggest_refresh_items(
    db: Session,
    *,
    organization_id: int,
    stale_days: int = 30,
    limit: int = 20,
) -> list[ContentRefreshItem]:
    """Crea sugerencias para piezas approved/published antiguas sin refresh abierto."""
    cutoff = datetime.utcnow() - timedelta(days=max(1, stale_days))
    pieces = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.organization_id == organization_id,
            ContentPiece.status.in_(("approved", "published")),
            ContentPiece.updated_at < cutoff,
        )
        .order_by(ContentPiece.updated_at.asc())
        .limit(limit * 3)
        .all()
    )
    created: list[ContentRefreshItem] = []
    for piece in pieces:
        open_item = (
            db.query(ContentRefreshItem)
            .filter(
                ContentRefreshItem.organization_id == organization_id,
                ContentRefreshItem.piece_id == piece.id,
                ContentRefreshItem.status.in_(
                    ("suggested", "approved", "in_progress")
                ),
            )
            .first()
        )
        if open_item:
            continue
        pkg = piece.package
        item = ContentRefreshItem(
            organization_id=organization_id,
            piece_id=piece.id,
            profile_id=pkg.profile_id if pkg else None,
            reason="stale",
            status="suggested",
            due_at=datetime.utcnow() + timedelta(days=7),
            source_piece_version=piece.version,
            notes=f"Sin actualización desde {piece.updated_at.isoformat() if piece.updated_at else '?'}",
        )
        db.add(item)
        created.append(item)
        if len(created) >= limit:
            break
    if created:
        db.commit()
        for item in created:
            db.refresh(item)
    return created


def list_refresh_items(
    db: Session,
    *,
    organization_id: int,
    status: str | None = None,
    limit: int = 50,
) -> list[ContentRefreshItem]:
    q = db.query(ContentRefreshItem).filter(
        ContentRefreshItem.organization_id == organization_id
    )
    if status:
        q = q.filter(ContentRefreshItem.status == status)
    return q.order_by(ContentRefreshItem.created_at.desc()).limit(limit).all()


def decide_refresh_item(
    db: Session,
    *,
    organization_id: int,
    item_id: int,
    accept: bool,
    actor: str,
    notes: str | None = None,
) -> ContentRefreshItem:
    item = (
        db.query(ContentRefreshItem)
        .filter(
            ContentRefreshItem.id == item_id,
            ContentRefreshItem.organization_id == organization_id,
        )
        .first()
    )
    if not item:
        raise ValueError("Refresh item not found")
    if item.status not in ("suggested", "approved"):
        raise ValueError(f"Cannot decide item in status '{item.status}'")
    item.status = "approved" if accept else "dismissed"
    item.decided_by = actor
    item.decided_at = datetime.utcnow()
    if notes is not None:
        item.notes = notes
    db.commit()
    db.refresh(item)
    return item


def start_refresh_revision(
    db: Session,
    *,
    organization_id: int,
    item_id: int,
    actor: str,
) -> ContentRefreshItem:
    """Crea pieza draft v+1 ligada al refresh (cierra la ambigüedad post-aprobación)."""
    item = (
        db.query(ContentRefreshItem)
        .filter(
            ContentRefreshItem.id == item_id,
            ContentRefreshItem.organization_id == organization_id,
        )
        .first()
    )
    if not item:
        raise ValueError("Refresh item not found")
    if item.status != "approved":
        raise ValueError("Item must be approved before starting revision")
    if item.new_piece_id:
        item.status = "in_progress"
        db.commit()
        db.refresh(item)
        return item

    source = (
        db.query(ContentPiece)
        .filter(
            ContentPiece.id == item.piece_id,
            ContentPiece.organization_id == organization_id,
        )
        .first()
    )
    if not source:
        raise ValueError("Source piece not found")

    new_version = int(source.version or 1) + 1
    draft = ContentPiece(
        organization_id=organization_id,
        package_id=source.package_id,
        article_id=source.article_id,
        parent_piece_id=source.id,
        format_type=source.format_type,
        language=source.language,
        title=f"{source.title} (refresh v{new_version})",
        body_text=source.body_text,
        body_json=source.body_json,
        source_url=source.source_url,
        status="draft",
        version=new_version,
        generation_json={
            "refresh_of": source.id,
            "refresh_item_id": item.id,
            "started_by": actor,
        },
    )
    db.add(draft)
    db.flush()
    item.new_piece_id = draft.id
    item.status = "in_progress"
    item.decided_by = actor
    item.decided_at = datetime.utcnow()
    item.notes = (item.notes or "") + f"\n[start] draft piece #{draft.id} v{new_version}"
    db.commit()
    db.refresh(item)
    return item


def mark_refresh_done(
    db: Session,
    *,
    organization_id: int,
    item_id: int,
    new_piece_id: int | None = None,
    actor: str | None = None,
) -> ContentRefreshItem:
    item = (
        db.query(ContentRefreshItem)
        .filter(
            ContentRefreshItem.id == item_id,
            ContentRefreshItem.organization_id == organization_id,
        )
        .first()
    )
    if not item:
        raise ValueError("Refresh item not found")
    if item.status not in ("approved", "in_progress"):
        raise ValueError("Item must be approved before completion")
    if new_piece_id:
        piece = (
            db.query(ContentPiece)
            .filter(
                ContentPiece.id == new_piece_id,
                ContentPiece.organization_id == organization_id,
            )
            .first()
        )
        if not piece:
            raise ValueError("new_piece_id not found in org")
        item.new_piece_id = new_piece_id
    item.status = "done"
    if actor:
        item.decided_by = actor
    item.decided_at = datetime.utcnow()
    db.commit()
    db.refresh(item)
    return item


def domain_to_dict(row: CustomDomain) -> dict:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "hostname": row.hostname,
        "is_primary": row.is_primary,
        "status": row.status,
        "verified_at": row.verified_at.isoformat() if row.verified_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def refresh_to_dict(row: ContentRefreshItem) -> dict:
    return {
        "id": row.id,
        "organization_id": row.organization_id,
        "piece_id": row.piece_id,
        "profile_id": row.profile_id,
        "reason": row.reason,
        "status": row.status,
        "due_at": row.due_at.isoformat() if row.due_at else None,
        "source_piece_version": row.source_piece_version,
        "new_piece_id": row.new_piece_id,
        "notes": row.notes,
        "decided_by": row.decided_by,
        "decided_at": row.decided_at.isoformat() if row.decided_at else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def saas_me_dict(org: Organization, domains: list[CustomDomain] | None = None) -> dict:
    payload = org_saas_payload(org)
    payload["domains"] = [domain_to_dict(d) for d in (domains or [])]
    return payload
