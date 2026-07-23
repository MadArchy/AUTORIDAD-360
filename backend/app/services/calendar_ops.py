"""Calendario, tareas y decisiones — Fase 4."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import ContentPiece, ProfessionalProfile
from app.models.operations import CadenceRule, CalendarSlot, DecisionLog, EditorialTask
from app.services.audit import log_audit
from app.services.quota import get_active_profile
from app.services.risk import (
    assert_transition,
    assess_piece_risk,
    can_approve_with_risk,
    risk_payload,
)

# Cadencia piloto Juan Vásquez
DEFAULT_CADENCE = [
    ("linkedin", "week", 3),
    ("video_script", "month", 2),
    ("carousel", "week", 1),
    ("newsletter", "week", 1),
]

TASK_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "linkedin": [
        ("attach_script", "Adjuntar copy LinkedIn"),
        ("notify", "Notificar a community manager"),
        ("mark_done", "Marcar listo para publicar"),
        ("publish", "Publicar en LinkedIn"),
    ],
    "video_script": [
        ("attach_script", "Adjuntar guion de video"),
        ("notify", "Notificar a Juan para grabación"),
        ("record_video", "Recibir video grabado"),
        ("send_to_edit", "Enviar a edición"),
        ("mark_done", "Marcar edición completa"),
        ("publish", "Publicar video"),
    ],
    "carousel": [
        ("attach_script", "Adjuntar slides/carrusel"),
        ("send_to_edit", "Diseño / revisión visual"),
        ("mark_done", "Marcar listo"),
        ("publish", "Publicar carrusel"),
    ],
    "newsletter": [
        ("attach_script", "Adjuntar borrador newsletter"),
        ("notify", "Revisión editorial"),
        ("mark_done", "Marcar listo"),
        ("publish", "Enviar newsletter"),
    ],
}


def log_decision(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    actor: str,
    from_status: str | None = None,
    to_status: str | None = None,
    risk_level: str | None = None,
    reason: str | None = None,
    version: int | None = None,
    snapshot_json: dict | None = None,
    organization_id: int | None = None,
) -> DecisionLog:
    entry = DecisionLog(
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        risk_level=risk_level,
        actor=actor,
        reason=reason,
        version=version,
        snapshot_json=snapshot_json,
    )
    db.add(entry)
    log_audit(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor=actor,
        output_summary=(reason or action)[:300],
        metadata_json={
            "from_status": from_status,
            "to_status": to_status,
            "risk_level": risk_level,
        },
    )
    return entry


def seed_cadence(db: Session, profile: ProfessionalProfile | None = None) -> list[CadenceRule]:
    profile = profile or get_active_profile(db)
    if not profile:
        raise ValueError("No active profile")
    created = []
    for format_type, frequency, count in DEFAULT_CADENCE:
        existing = (
            db.query(CadenceRule)
            .filter_by(profile_id=profile.id, format_type=format_type, frequency=frequency)
            .first()
        )
        if existing:
            created.append(existing)
            continue
        rule = CadenceRule(
            organization_id=profile.organization_id,
            profile_id=profile.id,
            format_type=format_type,
            frequency=frequency,
            target_count=count,
            is_active=True,
        )
        db.add(rule)
        created.append(rule)
    db.commit()
    return created


def _next_weekdays(start: datetime, n: int) -> list[datetime]:
    """Próximos n días laborables (lun–vie) a las 10:00 UTC."""
    days: list[datetime] = []
    cursor = start.replace(hour=10, minute=0, second=0, microsecond=0)
    if cursor.weekday() >= 5:
        cursor += timedelta(days=(7 - cursor.weekday()))
    while len(days) < n:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor += timedelta(days=1)
    return days


def generate_calendar(
    db: Session,
    *,
    weeks: int = 2,
    profile: ProfessionalProfile | None = None,
) -> list[CalendarSlot]:
    profile = profile or get_active_profile(db)
    if not profile:
        raise ValueError("No active profile")
    seed_cadence(db, profile)
    rules = (
        db.query(CadenceRule)
        .filter(CadenceRule.profile_id == profile.id, CadenceRule.is_active.is_(True))
        .all()
    )

    start = datetime.utcnow() + timedelta(days=1)
    slots: list[CalendarSlot] = []

    for rule in rules:
        if rule.frequency == "week":
            total = rule.target_count * weeks
            dates = _next_weekdays(start, total)
        else:
            # month → repartir en el horizonte de weeks
            total = max(1, round(rule.target_count * (weeks / 4)))
            dates = _next_weekdays(start, total)

        for i, when in enumerate(dates):
            title = f"{rule.format_type.replace('_', ' ').title()} #{i + 1}"
            slot = CalendarSlot(
                organization_id=getattr(profile, "organization_id", None),
                profile_id=profile.id,
                format_type=rule.format_type,
                title=title,
                scheduled_at=when,
                status="planned",
                risk_level="yellow",
                channel=_channel_for(rule.format_type),
            )
            db.add(slot)
            db.flush()
            _create_tasks_for_slot(db, slot)
            slots.append(slot)

    db.commit()
    return slots


def _channel_for(format_type: str) -> str:
    return {
        "linkedin": "linkedin",
        "video_script": "youtube/linkedin-video",
        "carousel": "linkedin-carousel",
        "newsletter": "email",
    }.get(format_type, format_type)


def _create_tasks_for_slot(db: Session, slot: CalendarSlot) -> list[EditorialTask]:
    templates = TASK_TEMPLATES.get(
        slot.format_type,
        [("mark_done", "Completar pieza"), ("publish", "Publicar")],
    )
    tasks = []
    for i, (task_type, title) in enumerate(templates):
        due = slot.scheduled_at - timedelta(days=max(0, len(templates) - i - 1))
        task = EditorialTask(
            organization_id=slot.organization_id,
            slot_id=slot.id,
            piece_id=slot.piece_id,
            task_type=task_type,
            title=title,
            status="todo",
            due_at=due,
        )
        db.add(task)
        tasks.append(task)
    return tasks


def attach_piece_to_slot(
    db: Session,
    slot: CalendarSlot,
    piece: ContentPiece,
    actor: str,
) -> CalendarSlot:
    if piece.format_type not in (slot.format_type, "short_post", "thread") and not (
        slot.format_type == "video_script" and piece.format_type == "video_script"
    ):
        # Permitir match exacto; short/thread solo a linkedin
        if not (slot.format_type == "linkedin" and piece.format_type in ("linkedin", "short_post", "thread")):
            if piece.format_type != slot.format_type:
                raise ValueError(
                    f"Format mismatch: slot={slot.format_type} piece={piece.format_type}"
                )

    assessment = assess_piece_risk(piece)
    from_status = slot.status
    assert_transition(from_status, "assigned")

    slot.piece_id = piece.id
    slot.status = "assigned"
    slot.risk_level = assessment.level
    slot.risk_json = risk_payload(assessment)
    slot.title = piece.title[:512]

    for task in (
        db.query(EditorialTask).filter(EditorialTask.slot_id == slot.id).all()
    ):
        task.piece_id = piece.id

    log_decision(
        db,
        entity_type="calendar_slot",
        entity_id=slot.id,
        action="assign_piece",
        actor=actor,
        from_status=from_status,
        to_status="assigned",
        risk_level=assessment.level,
        reason=f"Attached piece #{piece.id}",
        snapshot_json={"piece_id": piece.id, "risk": risk_payload(assessment)},
        organization_id=slot.organization_id,
    )
    db.commit()
    db.refresh(slot)
    return slot


def advance_slot(
    db: Session,
    slot: CalendarSlot,
    target_status: str,
    actor: str,
    *,
    reason: str | None = None,
    risk_override: bool = False,
) -> CalendarSlot:
    from_status = slot.status
    assert_transition(from_status, target_status)

    piece = None
    assessment = None
    if slot.piece_id:
        piece = db.query(ContentPiece).filter(ContentPiece.id == slot.piece_id).first()
        if piece:
            assessment = assess_piece_risk(piece)
            slot.risk_level = assessment.level
            slot.risk_json = risk_payload(assessment)

    if target_status in ("approved", "scheduled", "published"):
        if assessment is None:
            raise ValueError("Cannot approve/publish slot without content piece")
        ok, code = can_approve_with_risk(
            assessment, override=risk_override, reason=reason
        )
        if not ok:
            raise ValueError(
                f"Blocked by risk semáforo ({assessment.level}): {code}. "
                "Provide risk_override=true and reason (>=10 chars) for red."
            )
        if assessment.level == "red" and risk_override:
            log_decision(
                db,
                entity_type="calendar_slot",
                entity_id=slot.id,
                action="risk_override",
                actor=actor,
                from_status=from_status,
                to_status=target_status,
                risk_level="red",
                reason=reason,
                organization_id=slot.organization_id,
            )

    slot.status = target_status
    log_decision(
        db,
        entity_type="calendar_slot",
        entity_id=slot.id,
        action="status_change",
        actor=actor,
        from_status=from_status,
        to_status=target_status,
        risk_level=slot.risk_level,
        reason=reason,
        organization_id=slot.organization_id,
    )

    if target_status == "approved" and piece and piece.status == "pending_approval":
        piece.status = "approved"
        piece.approved_by = actor
        piece.approved_at = datetime.utcnow()
        log_decision(
            db,
            entity_type="content_piece",
            entity_id=piece.id,
            action="approve",
            actor=actor,
            from_status="pending_approval",
            to_status="approved",
            risk_level=slot.risk_level,
            reason=reason,
            version=piece.version,
            organization_id=slot.organization_id,
        )

    if target_status == "published" and piece:
        piece.status = "approved"  # keep approved; publish tracked on slot
        log_decision(
            db,
            entity_type="calendar_slot",
            entity_id=slot.id,
            action="publish",
            actor=actor,
            from_status=from_status,
            to_status="published",
            risk_level=slot.risk_level,
            reason=reason or "Published",
            organization_id=slot.organization_id,
        )

    db.commit()
    db.refresh(slot)
    return slot


def prepare_slot_for_approval(
    db: Session,
    slot: CalendarSlot,
    actor: str,
    *,
    reason: str | None = None,
) -> CalendarSlot:
    """Atajo operativo: marca tareas no-publish como done y deja el slot en pending_approval."""
    if not slot.piece_id:
        raise ValueError("Adjunta una pieza multi-formato antes de pedir aprobación")
    if slot.status in ("approved", "scheduled", "published", "cancelled"):
        raise ValueError(f"El slot ya está en estado '{slot.status}'")
    if slot.status not in ("assigned", "in_progress", "pending_approval", "planned"):
        raise ValueError(f"No se puede preparar aprobación desde '{slot.status}'")

    from_status = slot.status
    tasks = (
        db.query(EditorialTask)
        .filter(EditorialTask.slot_id == slot.id)
        .order_by(EditorialTask.id.asc())
        .all()
    )
    for task in tasks:
        if task.task_type == "publish":
            continue
        if task.status != "done":
            task.status = "done"
            task.completed_at = datetime.utcnow()
            task.completed_by = actor
            if not task.assignee:
                task.assignee = actor

    piece = db.query(ContentPiece).filter(ContentPiece.id == slot.piece_id).first()
    if piece:
        assessment = assess_piece_risk(piece)
        slot.risk_level = assessment.level
        slot.risk_json = risk_payload(assessment)

    slot.status = "pending_approval"
    log_decision(
        db,
        entity_type="calendar_slot",
        entity_id=slot.id,
        action="prepare_approval",
        actor=actor,
        from_status=from_status,
        to_status="pending_approval",
        risk_level=slot.risk_level,
        reason=reason or "Tareas operativas completadas; listo para aprobación humana",
        snapshot_json={"piece_id": slot.piece_id, "risk": slot.risk_json},
        organization_id=slot.organization_id,
    )
    db.commit()
    db.refresh(slot)
    return slot


def update_task(
    db: Session,
    task: EditorialTask,
    *,
    actor: str,
    status: str | None = None,
    assignee: str | None = None,
    attachment_url: str | None = None,
    attachment_notes: str | None = None,
) -> EditorialTask:
    from_status = task.status
    if status and status != from_status:
        assert_transition(from_status, status, kind="task")
        task.status = status
        if status == "done":
            task.completed_at = datetime.utcnow()
            task.completed_by = actor

    if assignee is not None:
        task.assignee = assignee
    if attachment_url is not None:
        task.attachment_url = attachment_url
    if attachment_notes is not None:
        task.attachment_notes = attachment_notes

    log_decision(
        db,
        entity_type="editorial_task",
        entity_id=task.id,
        action="task_update",
        actor=actor,
        from_status=from_status,
        to_status=task.status,
        reason=attachment_notes or assignee,
        snapshot_json={
            "assignee": task.assignee,
            "attachment_url": task.attachment_url,
            "task_type": task.task_type,
        },
        organization_id=task.organization_id,
    )

    # Si se adjunta guion, avanzar slot a in_progress
    slot = db.query(CalendarSlot).filter(CalendarSlot.id == task.slot_id).first()
    if slot and task.task_type == "attach_script" and task.attachment_url and slot.status == "assigned":
        try:
            assert_transition(slot.status, "in_progress")
            slot.status = "in_progress"
        except ValueError as e:
            import logging
            logging.getLogger(__name__).warning(f"Could not advance slot status: {e}")

    # Todas las tareas done (excepto publish) → pending_approval
    if slot and status == "done":
        siblings = db.query(EditorialTask).filter(EditorialTask.slot_id == slot.id).all()
        non_publish = [t for t in siblings if t.task_type != "publish"]
        if non_publish and all(t.status == "done" for t in non_publish):
            if slot.status == "in_progress":
                slot.status = "pending_approval"
                if slot.piece_id:
                    piece = db.query(ContentPiece).filter(ContentPiece.id == slot.piece_id).first()
                    if piece:
                        assessment = assess_piece_risk(piece)
                        slot.risk_level = assessment.level
                        slot.risk_json = risk_payload(assessment)

    db.commit()
    db.refresh(task)
    return task
