"""Ajuste automático de porcentajes — solo con evidencia de leads calificados.

Regla rectora: los "me gusta" NO mueven porcentajes.
Solo contactos calificados / convertidos respaldan una recomendación.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from app.models import EditorialPercentage, ProfessionalProfile
from app.models.learning import Lead, PercentageRecommendation
from app.services.audit import log_audit
from app.services.quota import validate_percentages_sum

# Mínimos de evidencia
MIN_QUALIFIED_TOTAL = 3
MIN_DELTA_PCT = 2.0  # no recomendar cambios menores a 2 puntos
MAX_SHIFT_PER_PILLAR = 5.0  # tope de reasignación por ciclo


def build_percentage_recommendation(
    db: Session,
    profile: ProfessionalProfile,
    *,
    days: int = 30,
    organization_id: int | None = None,
) -> PercentageRecommendation | None:
    """
    Calcula recomendación determinística.
    Retorna None si no hay evidencia suficiente.
    """
    since = datetime.utcnow() - timedelta(days=days)
    leads_q = db.query(Lead).filter(
        Lead.profile_id == profile.id,
        Lead.created_at >= since,
    )
    if organization_id is not None:
        leads_q = leads_q.filter(Lead.organization_id == organization_id)
    leads = leads_q.all()

    qualified = [
        l for l in leads if l.is_qualified or l.status in ("qualified", "converted")
    ]
    if len(qualified) < MIN_QUALIFIED_TOTAL:
        return None

    pct_rows = (
        db.query(EditorialPercentage)
        .options(joinedload(EditorialPercentage.pillar))
        .filter(EditorialPercentage.profile_id == profile.id)
        .all()
    )
    if not pct_rows:
        return None

    # Conteo de leads calificados por pilar
    q_by_pillar: dict[int, int] = {ep.pillar_id: 0 for ep in pct_rows}
    for lead in qualified:
        if lead.pillar_id in q_by_pillar:
            q_by_pillar[lead.pillar_id] += 1

    total_q = sum(q_by_pillar.values())
    if total_q < MIN_QUALIFIED_TOTAL:
        return None

    # Share actual vs share por leads calificados
    current = {ep.pillar_id: float(ep.target_pct) for ep in pct_rows}
    lead_share = {
        pid: (count / total_q * 100.0) for pid, count in q_by_pillar.items()
    }

    # Deltas capados
    raw_deltas = {}
    for pid in current:
        delta = lead_share.get(pid, 0.0) - current[pid]
        if abs(delta) < MIN_DELTA_PCT:
            raw_deltas[pid] = 0.0
        else:
            raw_deltas[pid] = max(-MAX_SHIFT_PER_PILLAR, min(MAX_SHIFT_PER_PILLAR, delta))

    # Renormalizar para que la suma de (current+delta) = 100
    proposed = {pid: current[pid] + raw_deltas[pid] for pid in current}
    proposed = _normalize_to_100(proposed)

    changes = []
    for ep in pct_rows:
        to_pct = round(proposed[ep.pillar_id], 2)
        from_pct = round(current[ep.pillar_id], 2)
        delta = round(to_pct - from_pct, 2)
        if abs(delta) < 0.01:
            continue
        changes.append(
            {
                "pillar_id": ep.pillar_id,
                "pillar_slug": ep.pillar.slug if ep.pillar else None,
                "pillar_name": ep.pillar.name if ep.pillar else None,
                "from_pct": from_pct,
                "to_pct": to_pct,
                "delta": delta,
                "qualified_leads": q_by_pillar.get(ep.pillar_id, 0),
                "lead_share_pct": round(lead_share.get(ep.pillar_id, 0.0), 2),
            }
        )

    if not changes:
        return None

    # Evidencia: explícitamente registramos que likes NO se usaron
    evidence = {
        "days": days,
        "qualified_leads_total": len(qualified),
        "leads_total": len(leads),
        "rule": "qualified_leads_only",
        "likes_ignored": True,
        "min_qualified_required": MIN_QUALIFIED_TOTAL,
        "pillar_qualified_counts": {
            str(k): v for k, v in q_by_pillar.items()
        },
    }

    rationale = (
        f"Reasignación basada en {len(qualified)} leads calificados "
        f"(últimos {days} días). Los likes/interacciones no influyen. "
        f"Cambios: "
        + ", ".join(
            f"{c['pillar_slug']} {c['from_pct']}→{c['to_pct']}" for c in changes
        )
    )

    # Invalidar recomendaciones pending previas
    prev = (
        db.query(PercentageRecommendation)
        .filter(
            PercentageRecommendation.profile_id == profile.id,
            PercentageRecommendation.status == "pending",
        )
        .all()
    )
    for p in prev:
        p.status = "superseded"

    rec = PercentageRecommendation(
        organization_id=organization_id or profile.organization_id,
        profile_id=profile.id,
        status="pending",
        rationale=rationale,
        evidence_json=evidence,
        changes_json=changes,
        min_qualified_leads=len(qualified),
    )
    db.add(rec)
    log_audit(
        db,
        entity_type="percentage_recommendation",
        entity_id=0,
        action="recommended",
        actor="system",
        output_summary=rationale[:300],
        metadata_json=evidence,
    )
    db.commit()
    db.refresh(rec)
    return rec


def apply_recommendation(
    db: Session,
    rec: PercentageRecommendation,
    *,
    actor: str,
    accept: bool,
    reason: str | None = None,
) -> PercentageRecommendation:
    if rec.status != "pending":
        raise ValueError(f"Recommendation not pending (status={rec.status})")

    if not accept:
        rec.status = "rejected"
        rec.decided_at = datetime.utcnow()
        rec.decided_by = actor
        rec.decision_reason = reason or "Rejected by human"
        db.commit()
        return rec

    # Aplicar cambios
    changes = rec.changes_json or []
    new_values = []
    for change in changes:
        row = (
            db.query(EditorialPercentage)
            .filter_by(profile_id=rec.profile_id, pillar_id=change["pillar_id"])
            .first()
        )
        if row:
            row.target_pct = change["to_pct"]
            new_values.append(float(change["to_pct"]))

    # Completar con pilares no tocados
    all_rows = (
        db.query(EditorialPercentage)
        .filter(EditorialPercentage.profile_id == rec.profile_id)
        .all()
    )
    validate_percentages_sum([float(r.target_pct) for r in all_rows], "editorial after apply")

    rec.status = "accepted"
    rec.decided_at = datetime.utcnow()
    rec.decided_by = actor
    rec.decision_reason = reason or "Accepted — data-backed reallocation"

    log_audit(
        db,
        entity_type="percentage_recommendation",
        entity_id=rec.id,
        action="accepted",
        actor=actor,
        output_summary=rec.decision_reason,
        metadata_json={"changes": changes},
    )
    db.commit()
    db.refresh(rec)
    return rec


def _normalize_to_100(values: dict[int, float]) -> dict[int, float]:
    total = sum(values.values())
    if total <= 0:
        n = len(values) or 1
        return {k: round(100.0 / n, 2) for k in values}
    scaled = {k: v / total * 100.0 for k, v in values.items()}
    # Ajuste de redondeo en el mayor
    rounded = {k: round(v, 2) for k, v in scaled.items()}
    drift = round(100.0 - sum(rounded.values()), 2)
    if rounded:
        top = max(rounded, key=rounded.get)
        rounded[top] = round(rounded[top] + drift, 2)
    return rounded
