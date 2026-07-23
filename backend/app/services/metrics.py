"""Motor de métricas operativas, editoriales y comerciales — determinístico."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    BlogPost,
    CalendarSlot,
    ContentPiece,
    DecisionLog,
    EditorialPercentage,
    NewsArticle,
    ProfessionalProfile,
)
from app.models.learning import ContentEngagement, Lead, MetricSnapshot


def compute_dashboard(
    db: Session,
    *,
    profile_id: int | None = None,
    organization_id: int | None = None,
    days: int = 30,
) -> dict:
    since = datetime.utcnow() - timedelta(days=days)

    # --- Operativo (siempre acotado a la organización activa) ---
    decisions = db.query(DecisionLog).filter(DecisionLog.created_at >= since)
    if organization_id is not None:
        decisions = decisions.filter(DecisionLog.organization_id == organization_id)
    approvals = [
        d
        for d in decisions.all()
        if d.action in ("approve", "status_change") and d.to_status == "approved"
    ]

    slots = db.query(CalendarSlot).filter(CalendarSlot.created_at >= since)
    if profile_id is not None:
        slots = slots.filter(CalendarSlot.profile_id == profile_id)
    if organization_id is not None:
        slots = slots.filter(CalendarSlot.organization_id == organization_id)
    slot_rows = slots.all()

    published = [s for s in slot_rows if s.status == "published"]
    pending_approval = [s for s in slot_rows if s.status == "pending_approval"]
    avg_risk = _avg_risk(slot_rows)

    pieces_q = db.query(ContentPiece).filter(ContentPiece.created_at >= since)
    if organization_id is not None:
        pieces_q = pieces_q.filter(ContentPiece.organization_id == organization_id)
    pieces = pieces_q.all()
    pending_pieces = [p for p in pieces if p.status == "pending_approval"]
    approved_pieces = [p for p in pieces if p.status == "approved"]

    blog_q = db.query(BlogPost).filter(BlogPost.created_at >= since)
    if organization_id is not None:
        blog_q = blog_q.filter(BlogPost.organization_id == organization_id)
    blogs = blog_q.all()
    approval_hours = _blog_approval_hours(blogs)

    # --- Comercial / leads ---
    leads_q = db.query(Lead).filter(Lead.created_at >= since)
    if organization_id is not None:
        leads_q = leads_q.filter(Lead.organization_id == organization_id)
    if profile_id is not None:
        leads_q = leads_q.filter(Lead.profile_id == profile_id)
    leads = leads_q.all()

    funnel = {
        "new": sum(1 for l in leads if l.status == "new"),
        "contacted": sum(1 for l in leads if l.status == "contacted"),
        "qualified": sum(1 for l in leads if l.status == "qualified" or l.is_qualified),
        "converted": sum(1 for l in leads if l.status == "converted"),
        "lost": sum(1 for l in leads if l.status == "lost"),
        "total": len(leads),
    }
    qualified_count = funnel["qualified"] + funnel["converted"]
    conversion_rate = round(
        (funnel["converted"] / funnel["total"] * 100) if funnel["total"] else 0.0, 2
    )

    # --- Editorial por pilar ---
    eng_q = db.query(ContentEngagement).filter(ContentEngagement.recorded_at >= since)
    if organization_id is not None:
        eng_q = eng_q.filter(ContentEngagement.organization_id == organization_id)
    if profile_id is not None:
        eng_q = eng_q.filter(ContentEngagement.profile_id == profile_id)
    engagements = eng_q.all()

    by_pillar = _pillar_breakdown(db, leads, engagements, profile_id)

    articles_q = db.query(func.count(NewsArticle.id))
    if organization_id is not None:
        articles_q = articles_q.filter(NewsArticle.organization_id == organization_id)
    articles_total = articles_q.scalar() or 0

    metrics = {
        "period_days": days,
        "profile_id": profile_id,
        "organization_id": organization_id,
        "total_articles": int(articles_total),
        "total_content_pieces": len(pieces),
        "total_leads": funnel["total"],
        "qualified_leads": qualified_count,
        "converted_leads": funnel["converted"],
        "conversion_rate_pct": conversion_rate,
        "operational": {
            "slots_total": len(slot_rows),
            "slots_published": len(published),
            "slots_pending_approval": len(pending_approval),
            "pieces_pending": len(pending_pieces),
            "pieces_approved": len(approved_pieces),
            "avg_approval_hours": approval_hours,
            "avg_risk_score": avg_risk,  # 0 green … 2 red
            "decisions_logged": len(approvals),
        },
        "commercial": {
            "funnel": funnel,
            "qualified_leads": qualified_count,
            "conversion_rate_pct": conversion_rate,
        },
        "editorial": {
            "pillars": by_pillar,
            "total_likes": sum(e.likes for e in engagements),
            "total_comments": sum(e.comments for e in engagements),
        },
        "generated_at": datetime.utcnow().isoformat(),
    }

    snap = MetricSnapshot(
        organization_id=organization_id,
        profile_id=profile_id,
        period_days=days,
        metrics_json=metrics,
    )
    db.add(snap)
    db.commit()
    return metrics


def _blog_approval_hours(blogs: list) -> float | None:
    deltas = []
    for b in blogs:
        if b.approved_at and b.created_at:
            deltas.append((b.approved_at - b.created_at).total_seconds() / 3600.0)
    if not deltas:
        return None
    return round(sum(deltas) / len(deltas), 2)


def _avg_risk(slots: list) -> float | None:
    if not slots:
        return None
    map_ = {"green": 0, "yellow": 1, "red": 2}
    vals = [map_.get(s.risk_level, 1) for s in slots]
    return round(sum(vals) / len(vals), 2)


def _pillar_breakdown(
    db: Session,
    leads: list[Lead],
    engagements: list[ContentEngagement],
    profile_id: int | None,
) -> list[dict]:
    pillars = {}
    if profile_id:
        pcts = (
            db.query(EditorialPercentage)
            .filter(EditorialPercentage.profile_id == profile_id)
            .all()
        )
        for ep in pcts:
            if not ep.pillar:
                continue
            pillars[ep.pillar_id] = {
                "pillar_id": ep.pillar_id,
                "slug": ep.pillar.slug,
                "name": ep.pillar.name,
                "target_pct": float(ep.target_pct),
                "qualified_leads": 0,
                "total_leads": 0,
                "likes": 0,
                "comments": 0,
            }

    for lead in leads:
        if lead.pillar_id is None:
            continue
        if lead.pillar_id not in pillars:
            pillars[lead.pillar_id] = {
                "pillar_id": lead.pillar_id,
                "slug": f"pillar-{lead.pillar_id}",
                "name": f"Pillar {lead.pillar_id}",
                "target_pct": 0.0,
                "qualified_leads": 0,
                "total_leads": 0,
                "likes": 0,
                "comments": 0,
            }
        pillars[lead.pillar_id]["total_leads"] += 1
        if lead.is_qualified or lead.status in ("qualified", "converted"):
            pillars[lead.pillar_id]["qualified_leads"] += 1

    for eng in engagements:
        if eng.pillar_id is None:
            continue
        if eng.pillar_id not in pillars:
            pillars[eng.pillar_id] = {
                "pillar_id": eng.pillar_id,
                "slug": f"pillar-{eng.pillar_id}",
                "name": f"Pillar {eng.pillar_id}",
                "target_pct": 0.0,
                "qualified_leads": 0,
                "total_leads": 0,
                "likes": 0,
                "comments": 0,
            }
        pillars[eng.pillar_id]["likes"] += eng.likes or 0
        pillars[eng.pillar_id]["comments"] += eng.comments or 0

    return list(pillars.values())
