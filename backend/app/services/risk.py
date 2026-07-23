"""Semáforo de riesgo y reglas de transición — determinístico (Cursor).

Verde  → publicable con flujo normal
Amarillo → requiere revisión humana consciente
Rojo   → bloquea publicación salvo override explícito con motivo
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models import ContentPiece

LEGAL_RISK_KEYWORDS = {
    "asesoría legal personalizada",
    "garantizamos el resultado",
    "consejo legal vinculante",
    "sin riesgo legal",
    "elude impuestos",
    "evade",
    "garantizado ante la ley",
}

TRANSITION_MATRIX: dict[str, set[str]] = {
    # slot statuses
    "planned": {"assigned", "cancelled"},
    "assigned": {"in_progress", "cancelled"},
    "in_progress": {"pending_approval", "cancelled"},
    "pending_approval": {"approved", "rejected", "in_progress"},
    "approved": {"scheduled", "rejected"},
    "scheduled": {"published", "approved", "cancelled"},
    "published": set(),
    "rejected": {"in_progress", "cancelled"},
    "cancelled": set(),
}

TASK_TRANSITIONS: dict[str, set[str]] = {
    "todo": {"in_progress", "cancelled"},
    "in_progress": {"done", "blocked", "cancelled"},
    "blocked": {"in_progress", "cancelled"},
    "done": set(),
    "cancelled": set(),
}


@dataclass
class RiskAssessment:
    level: str  # green | yellow | red
    reasons: list[str]
    blockers: list[str]
    can_publish: bool
    requires_human: bool


def assess_piece_risk(piece: ContentPiece) -> RiskAssessment:
    reasons: list[str] = []
    blockers: list[str] = []
    factual = piece.factual_review_json or {}
    brand = piece.brand_review_json or {}
    text = (piece.body_text or "").lower()

    if not piece.source_url:
        blockers.append("missing_source_url")
    if not factual.get("passed", False):
        blockers.append("factual_review_failed")
        reasons.extend([f"unsupported:{c[:80]}" for c in (factual.get("unsupported_claims") or [])[:5]])
    if not brand.get("passed", False):
        reasons.extend([f"brand:{i}" for i in (brand.get("issues") or [])])

    for kw in LEGAL_RISK_KEYWORDS:
        if kw in text:
            blockers.append(f"legal_keyword:{kw}")

    if piece.status in ("factual_failed", "brand_failed", "rejected"):
        if piece.status == "factual_failed":
            blockers.append("status_factual_failed")
        else:
            reasons.append(f"status:{piece.status}")

    if blockers:
        level = "red"
    elif reasons or piece.status == "draft":
        level = "yellow"
    elif piece.status in ("pending_approval", "approved"):
        level = "green"
    else:
        level = "yellow"

    can_publish = level == "green"
    requires_human = level in ("yellow", "red") or piece.status == "pending_approval"

    return RiskAssessment(
        level=level,
        reasons=reasons,
        blockers=blockers,
        can_publish=can_publish,
        requires_human=requires_human,
    )


def can_transition(current: str, target: str, *, kind: str = "slot") -> bool:
    matrix = TASK_TRANSITIONS if kind == "task" else TRANSITION_MATRIX
    return target in matrix.get(current, set())


def assert_transition(current: str, target: str, *, kind: str = "slot") -> None:
    if not can_transition(current, target, kind=kind):
        raise ValueError(f"Invalid {kind} transition: {current} → {target}")


def can_approve_with_risk(
    assessment: RiskAssessment,
    *,
    override: bool = False,
    reason: str | None = None,
) -> tuple[bool, str]:
    if assessment.level == "green":
        return True, "ok_green"
    if assessment.level == "yellow":
        return True, "ok_yellow_human"
    # red
    if override and reason and len(reason.strip()) >= 10:
        return True, "ok_red_override"
    return False, "blocked_red_needs_override"


def risk_payload(assessment: RiskAssessment) -> dict[str, Any]:
    return {
        "level": assessment.level,
        "reasons": assessment.reasons,
        "blockers": assessment.blockers,
        "can_publish": assessment.can_publish,
        "requires_human": assessment.requires_human,
    }
