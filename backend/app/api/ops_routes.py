"""Fase 4 — calendario, tareas, semáforo e historial de decisiones."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models import (
    CadenceRule,
    CalendarSlot,
    ContentPiece,
    DecisionLog,
    EditorialTask,
    get_db,
)
from app.services.calendar_ops import (
    advance_slot,
    attach_piece_to_slot,
    generate_calendar,
    prepare_slot_for_approval,
    seed_cadence,
    update_task,
)
from app.services.quota import get_active_profile, seed_juan_profile
from app.services.risk import assess_piece_risk, risk_payload
from app.services.tenant import TenantContext, get_tenant_context, require_roles

router = APIRouter(prefix="/api/v1", tags=["fase4-ops"])

_OPS_STAFF = (
    "agency_admin",
    "strategist",
    "writer",
    "editor",
    "legal_reviewer",
    "analyst",
    "community_manager",
)
_OPS_MANAGERS = ("agency_admin", "strategist", "editor")
_OPS_SEARCH_ROLES = ("agency_admin", "strategist", "analyst")


class ActorRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=128)


class AdvanceSlotRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    target_status: str
    reason: str | None = None
    risk_override: bool = False


class AttachPieceRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    piece_id: int


class TaskUpdateRequest(BaseModel):
    actor: str = Field(min_length=2, max_length=128)
    status: str | None = None
    assignee: str | None = None
    attachment_url: str | None = None
    attachment_notes: str | None = None


class GenerateCalendarRequest(BaseModel):
    weeks: int = Field(default=2, ge=1, le=8)


class AgenticSearchRequest(BaseModel):
    queries: list[str] | None = None
    max_results_per_query: int = Field(default=5, ge=1, le=10)
    max_queries: int | None = Field(default=14, ge=1, le=40)
    max_priority: int = Field(default=11, ge=1, le=11)
    # Solo noticias recientes (horas). Default: hoy + margen de 36h.
    max_age_hours: int = Field(default=36, ge=6, le=168)


@router.get("/ops/news-typologies")
def list_news_typologies(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Catálogo editorial del perfil (PDF Tipos_de_Noticias + temas custom)."""
    require_roles(ctx, *_OPS_STAFF)
    from app.services.news_typologies import (
        SEARCH_QUERIES,
        describe_typologies,
        queries_for_priorities,
        typologies_from_profile,
    )
    from app.services.quota import get_active_profile

    profile = get_active_profile(db, organization_id=ctx.org_id)
    typologies = typologies_from_profile(profile)
    queries = queries_for_priorities(typologies=typologies) or list(SEARCH_QUERIES)
    return {
        "source": "profile.search_themes / Tipos_de_Noticias_IA_Juan_Vasquez.pdf",
        "typologies": describe_typologies(typologies),
        "query_count": len(queries),
        "quality_filter": (
            "Priorizar noticias que respondan: qué ocurrió, por qué importa, "
            "qué riesgo/oportunidad y qué debería revisar una empresa."
        ),
    }


@router.post("/ops/cadence/seed")
def seed_ops_cadence(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, "agency_admin")
    from app.api.deps_env import require_non_production

    require_non_production("Cadence seed")
    profile = get_active_profile(db, organization_id=ctx.org_id)
    if not profile and ctx.organization.slug == "agencia-piloto":
        profile = seed_juan_profile(db)
    if not profile:
        raise HTTPException(404, "Profile not found")
    rules = seed_cadence(db, profile)
    return {
        "profile_id": profile.id,
        "rules": [
            {
                "id": r.id,
                "format_type": r.format_type,
                "frequency": r.frequency,
                "target_count": r.target_count,
            }
            for r in rules
        ],
    }


@router.get("/ops/cadence")
def get_cadence(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_STAFF)
    from app.api.deps_env import allow_auto_seed

    profile = get_active_profile(db, organization_id=ctx.org_id)
    if not profile:
        raise HTTPException(404, "Profile not found")
    rules = db.query(CadenceRule).filter(CadenceRule.profile_id == profile.id).all()
    if not rules and allow_auto_seed():
        rules = seed_cadence(db, profile)
    return [
        {
            "id": r.id,
            "format_type": r.format_type,
            "frequency": r.frequency,
            "target_count": r.target_count,
            "is_active": r.is_active,
        }
        for r in rules
    ]

@router.post("/ops/search/run")
def run_agentic_search(
    body: AgenticSearchRequest | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_SEARCH_ROLES)
    from app.services.agentic_searcher import AgenticSearcherService

    req = body or AgenticSearchRequest()
    searcher = AgenticSearcherService(db, organization_id=ctx.org_id)
    stats = searcher.run_search_cycle(
        max_results_per_query=req.max_results_per_query,
        extra_queries=req.queries,
        max_queries=req.max_queries,
        max_priority=req.max_priority,
        max_age_hours=req.max_age_hours,
    )
    return {
        "message": "Búsqueda agentica de noticias del día completada",
        "stats": stats,
    }


@router.post("/ops/calendar/generate")
def generate_ops_calendar(
    body: GenerateCalendarRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_MANAGERS)
    try:
        profile = get_active_profile(db, organization_id=ctx.org_id)
        if not profile:
            raise HTTPException(404, "Profile not found")
        slots = generate_calendar(db, weeks=body.weeks, profile=profile)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"created": len(slots), "slots": [_slot_response(s, db) for s in slots]}


@router.get("/ops/calendar")
def list_calendar(
    days: int = 30,
    status: str | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_STAFF)
    query = (
        db.query(CalendarSlot)
        .filter(CalendarSlot.organization_id == ctx.org_id)
        .order_by(CalendarSlot.scheduled_at.asc())
    )
    if status:
        query = query.filter(CalendarSlot.status == status)
    slots = query.limit(200).all()
    cutoff = datetime.utcnow() - timedelta(days=7)
    horizon = datetime.utcnow() + timedelta(days=days)
    filtered = [s for s in slots if s.scheduled_at and cutoff <= s.scheduled_at <= horizon]
    return [_slot_response(s, db, include_tasks=True) for s in filtered]


@router.get("/ops/calendar/{slot_id}")
def get_slot(
    slot_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_STAFF)
    slot = db.query(CalendarSlot).filter(
        CalendarSlot.id == slot_id,
        CalendarSlot.organization_id == ctx.org_id,
    ).first()
    if not slot:
        raise HTTPException(404, "Slot not found")
    return _slot_response(slot, db, include_tasks=True)


@router.post("/ops/calendar/{slot_id}/attach")
def attach_piece(
    slot_id: int,
    body: AttachPieceRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_MANAGERS)
    slot = db.query(CalendarSlot).filter(
        CalendarSlot.id == slot_id,
        CalendarSlot.organization_id == ctx.org_id,
    ).first()
    if not slot:
        raise HTTPException(404, "Slot not found")
    piece = db.query(ContentPiece).filter(
        ContentPiece.id == body.piece_id,
        ContentPiece.organization_id == ctx.org_id,
    ).first()
    if not piece:
        raise HTTPException(404, "Piece not found")
    try:
        slot = attach_piece_to_slot(db, slot, piece, body.actor)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _slot_response(slot, db, include_tasks=True)


@router.post("/ops/calendar/{slot_id}/advance")
def advance_calendar_slot(
    slot_id: int,
    body: AdvanceSlotRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_MANAGERS)
    slot = db.query(CalendarSlot).filter(
        CalendarSlot.id == slot_id,
        CalendarSlot.organization_id == ctx.org_id,
    ).first()
    if not slot:
        raise HTTPException(404, "Slot not found")
    try:
        slot = advance_slot(
            db,
            slot,
            body.target_status,
            body.actor,
            reason=body.reason,
            risk_override=body.risk_override,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _slot_response(slot, db, include_tasks=True)


@router.post("/ops/calendar/{slot_id}/prepare-approval")
def prepare_calendar_slot(
    slot_id: int,
    body: ActorRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_MANAGERS)
    slot = db.query(CalendarSlot).filter(
        CalendarSlot.id == slot_id,
        CalendarSlot.organization_id == ctx.org_id,
    ).first()
    if not slot:
        raise HTTPException(404, "Slot not found")
    try:
        slot = prepare_slot_for_approval(
            db,
            slot,
            body.actor,
            reason=getattr(body, "reason", None),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _slot_response(slot, db, include_tasks=True)


@router.get("/ops/tasks")
def list_tasks(
    status: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_STAFF)
    query = (
        db.query(EditorialTask)
        .filter(EditorialTask.organization_id == ctx.org_id)
        .order_by(EditorialTask.due_at.asc())
    )
    if status:
        query = query.filter(EditorialTask.status == status)
    tasks = query.limit(limit).all()
    return [_task_response(t) for t in tasks]


@router.patch("/ops/tasks/{task_id}")
def patch_task(
    task_id: int,
    body: TaskUpdateRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_STAFF)
    task = db.query(EditorialTask).filter(
        EditorialTask.id == task_id,
        EditorialTask.organization_id == ctx.org_id,
    ).first()
    if not task:
        raise HTTPException(404, "Task not found")
    try:
        task = update_task(
            db,
            task,
            actor=body.actor,
            status=body.status,
            assignee=body.assignee,
            attachment_url=body.attachment_url,
            attachment_notes=body.attachment_notes,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return _task_response(task)


@router.get("/ops/risk/piece/{piece_id}")
def get_piece_risk(
    piece_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_STAFF)
    piece = db.query(ContentPiece).filter(
        ContentPiece.id == piece_id,
        ContentPiece.organization_id == ctx.org_id,
    ).first()
    if not piece:
        raise HTTPException(404, "Piece not found")
    return risk_payload(assess_piece_risk(piece))


@router.get("/ops/decisions")
def list_decisions(
    entity_type: str | None = None,
    entity_id: int | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_OPS_STAFF)
    query = (
        db.query(DecisionLog)
        .filter(DecisionLog.organization_id == ctx.org_id)
        .order_by(DecisionLog.created_at.desc())
    )
    if entity_type:
        query = query.filter(DecisionLog.entity_type == entity_type)
    if entity_id is not None:
        query = query.filter(DecisionLog.entity_id == entity_id)
    logs = query.limit(limit).all()
    return [
        {
            "id": d.id,
            "entity_type": d.entity_type,
            "entity_id": d.entity_id,
            "action": d.action,
            "from_status": d.from_status,
            "to_status": d.to_status,
            "risk_level": d.risk_level,
            "actor": d.actor,
            "reason": d.reason,
            "version": d.version,
            "snapshot": d.snapshot_json,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in logs
    ]


def _task_response(task: EditorialTask) -> dict:
    title = task.title or task.task_type or "Tarea"
    return {
        "id": task.id,
        "slot_id": task.slot_id,
        "piece_id": task.piece_id,
        "task_type": task.task_type,
        "title": title,
        "task_name": title,  # alias UI
        "assignee": task.assignee or "Sin asignar",
        "status": task.status,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "attachment_url": task.attachment_url,
        "attachment_notes": task.attachment_notes,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "completed_by": task.completed_by,
    }


def _risk_reason(slot: CalendarSlot) -> str:
    risk = slot.risk_json or {}
    reasons = risk.get("reasons") or []
    if isinstance(reasons, list) and reasons:
        return "; ".join(str(r) for r in reasons)
    if slot.piece_id is None:
        return "Pieza no adjunta — riesgo preventivo (amarillo) hasta asignar contenido verificado."
    return risk.get("summary") or slot.notes or "Sin detalle de riesgo."


def _slot_response(slot: CalendarSlot, db: Session, include_tasks: bool = False) -> dict:
    scheduled = slot.scheduled_at.isoformat() if slot.scheduled_at else None
    data = {
        "id": slot.id,
        "profile_id": slot.profile_id,
        "piece_id": slot.piece_id,
        "format_type": slot.format_type,
        "title": slot.title,
        "scheduled_at": scheduled,
        "scheduled_date": scheduled,  # alias UI
        "status": slot.status,
        "risk_level": slot.risk_level or "yellow",
        "risk": slot.risk_json,
        "risk_reason": _risk_reason(slot),  # alias UI
        "channel": slot.channel,
        "notes": slot.notes,
        "tasks": [],
    }
    if include_tasks:
        tasks = (
            db.query(EditorialTask)
            .filter(EditorialTask.slot_id == slot.id)
            .order_by(EditorialTask.id.asc())
            .all()
        )
        data["tasks"] = [_task_response(t) for t in tasks]
    return data
