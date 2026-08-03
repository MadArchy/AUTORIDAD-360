"""Ciclo automático de agentes por prioridad editorial."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.agents.langgraph_runner import run_agent, run_pipeline
from app.agents.runtime import (
    release_cycle_lock,
    set_agent_status,
    set_cycle_state,
    try_acquire_cycle_lock,
)
from app.models.content import ContentPackage
from app.models.editorial import NewsArticle


def _pick_verified_article(db: Session, organization_id: int | None) -> int | None:
    q = db.query(NewsArticle).filter(NewsArticle.status == "verified")
    if organization_id is not None:
        q = q.filter(NewsArticle.organization_id == organization_id)
    article = q.order_by(NewsArticle.id.desc()).first()
    if article:
        return int(article.id)
    # fallback: classified
    q2 = db.query(NewsArticle).filter(NewsArticle.status.in_(["classified", "collected"]))
    if organization_id is not None:
        q2 = q2.filter(NewsArticle.organization_id == organization_id)
    article = q2.order_by(NewsArticle.id.desc()).first()
    return int(article.id) if article else None


def _pick_article_for_write(db: Session, organization_id: int | None) -> int | None:
    """Artículo verificado sin paquete reciente."""
    q = db.query(NewsArticle).filter(NewsArticle.status == "verified")
    if organization_id is not None:
        q = q.filter(NewsArticle.organization_id == organization_id)
    candidates = q.order_by(NewsArticle.id.desc()).limit(12).all()
    for art in candidates:
        exists = (
            db.query(ContentPackage.id)
            .filter(ContentPackage.article_id == art.id)
            .first()
        )
        if not exists:
            return int(art.id)
    return int(candidates[0].id) if candidates else None


def _mark_running(
    name: str,
    organization_id: int | None,
    *,
    step: str,
    article_id: int | None = None,
) -> None:
    set_agent_status(
        name,
        organization_id=organization_id,
        status="running",
        current_step=step,
        current_tool=None,
        article_id=article_id,
        error=None,
    )


def _mark_done(
    name: str,
    organization_id: int | None,
    result: dict[str, Any],
) -> None:
    set_agent_status(
        name,
        organization_id=organization_id,
        status="completed" if result.get("ok") else "failed",
        current_step=None,
        current_tool=None,
        run_id=result.get("run_id"),
        article_id=result.get("article_id")
        or (result.get("artifacts") or {}).get("article_id"),
        summary=(result.get("summary") or "")[:400],
        ok=bool(result.get("ok")),
        error=None if result.get("ok") else (result.get("summary") or "error")[:400],
    )


def run_priority_cycle(
    db: Session,
    *,
    organization_id: int | None = None,
    limit: int = 5,
    include_juan: bool = True,
    reason: bool = False,
    job_id: int | None = None,
) -> dict[str, Any]:
    """Ejecuta agentes en orden de prioridad: discover → ingest → produce → trends → juan."""
    if organization_id is not None:
        db.info["organization_id"] = organization_id

    if not try_acquire_cycle_lock(organization_id):
        return {
            "ok": False,
            "skipped": True,
            "summary": "Ya hay un ciclo de agentes en curso",
        }

    steps_done: list[str] = []
    results: dict[str, Any] = {}
    article_id: int | None = None

    try:
        set_cycle_state(
            organization_id,
            status="running",
            phase="discover",
            current_agent="scout",
            job_id=job_id,
            steps_done=[],
            ok=None,
            summary="Ciclo automático iniciado",
        )

        # 1) Scout
        _mark_running("scout", organization_id, step="scout_web")
        set_cycle_state(
            organization_id, status="running", phase="discover", current_agent="scout",
            steps_done=steps_done, job_id=job_id,
        )
        scout_res = run_agent(
            db, "scout", limit=limit, reason=reason, query=None
        )
        _mark_done("scout", organization_id, scout_res)
        results["scout"] = {
            "ok": scout_res.get("ok"),
            "summary": scout_res.get("summary"),
            "duration_ms": scout_res.get("duration_ms"),
        }
        steps_done.append("scout")

        # 2) Classifier (lote)
        _mark_running("classifier", organization_id, step="classify_batch")
        set_cycle_state(
            organization_id, status="running", phase="ingest", current_agent="classifier",
            steps_done=steps_done, job_id=job_id,
        )
        cls_res = run_agent(db, "classifier", limit=limit, reason=reason)
        _mark_done("classifier", organization_id, cls_res)
        results["classifier"] = {
            "ok": cls_res.get("ok"),
            "summary": cls_res.get("summary"),
            "duration_ms": cls_res.get("duration_ms"),
        }
        steps_done.append("classifier")

        # 3–5) Article pipeline si hay candidato
        article_id = _pick_article_for_write(db, organization_id)
        if article_id:
            for name in ("verifier", "writer", "reviewer"):
                _mark_running(
                    name, organization_id, step=f"pipeline:{name}", article_id=article_id
                )
            set_cycle_state(
                organization_id,
                status="running",
                phase="produce",
                current_agent="writer",
                steps_done=steps_done,
                job_id=job_id,
                summary=f"Pipeline article_id={article_id}",
            )
            try:
                art_res = run_pipeline(
                    db,
                    "article",
                    article_id=article_id,
                    limit=limit,
                    prefer_llm=True,
                    reason=reason,
                )
                results["article_pipeline"] = {
                    "ok": art_res.get("ok"),
                    "summary": art_res.get("summary"),
                    "article_id": article_id,
                    "package_id": (art_res.get("artifacts") or {}).get("package_id"),
                    "duration_ms": art_res.get("duration_ms"),
                }
                for name in ("verifier", "writer", "reviewer"):
                    _mark_done(
                        name,
                        organization_id,
                        {
                            "ok": art_res.get("ok"),
                            "run_id": art_res.get("run_id"),
                            "article_id": article_id,
                            "summary": art_res.get("summary"),
                        },
                    )
                steps_done.extend(["verifier", "writer", "reviewer"])
            except Exception as exc:  # noqa: BLE001
                results["article_pipeline"] = {"ok": False, "error": str(exc)[:400]}
                for name in ("verifier", "writer", "reviewer"):
                    set_agent_status(
                        name,
                        organization_id=organization_id,
                        status="failed",
                        article_id=article_id,
                        error=str(exc)[:400],
                        ok=False,
                    )
        else:
            results["article_pipeline"] = {
                "ok": True,
                "skipped": True,
                "summary": "Sin artículos verificados para producir",
            }
            for name in ("verifier", "writer", "reviewer"):
                set_agent_status(
                    name,
                    organization_id=organization_id,
                    status="idle",
                    summary="Sin artículo candidato en este ciclo",
                )

        # 6) Trends
        _mark_running("trend_ad_advisor", organization_id, step="trend_ad_notes")
        set_cycle_state(
            organization_id, status="running", phase="trends",
            current_agent="trend_ad_advisor", steps_done=steps_done, job_id=job_id,
        )
        trend_res = run_agent(db, "trend_ad_advisor", limit=limit, reason=reason)
        _mark_done("trend_ad_advisor", organization_id, trend_res)
        results["trend_ad_advisor"] = {
            "ok": trend_res.get("ok"),
            "summary": trend_res.get("summary"),
            "duration_ms": trend_res.get("duration_ms"),
        }
        steps_done.append("trend_ad_advisor")

        # 7–9) Juan practice (misma voz, frentes de práctica)
        if include_juan:
            juan_article = article_id or _pick_verified_article(db, organization_id)
            if juan_article:
                for name in ("juan_editorial", "juan_ai_governance", "juan_ip_patents"):
                    _mark_running(
                        name,
                        organization_id,
                        step=f"juan:{name}",
                        article_id=juan_article,
                    )
                set_cycle_state(
                    organization_id,
                    status="running",
                    phase="juan",
                    current_agent="juan_editorial",
                    steps_done=steps_done,
                    job_id=job_id,
                    summary=f"juan_practice article_id={juan_article}",
                )
                try:
                    juan_res = run_pipeline(
                        db,
                        "juan_practice",
                        article_id=juan_article,
                        limit=limit,
                        prefer_llm=True,
                        reason=reason,
                    )
                    results["juan_practice"] = {
                        "ok": juan_res.get("ok"),
                        "summary": juan_res.get("summary"),
                        "article_id": juan_article,
                        "duration_ms": juan_res.get("duration_ms"),
                    }
                    for name in ("juan_editorial", "juan_ai_governance", "juan_ip_patents"):
                        _mark_done(
                            name,
                            organization_id,
                            {
                                "ok": juan_res.get("ok"),
                                "run_id": juan_res.get("run_id"),
                                "article_id": juan_article,
                                "summary": juan_res.get("summary"),
                            },
                        )
                    steps_done.extend(
                        ["juan_editorial", "juan_ai_governance", "juan_ip_patents"]
                    )
                except Exception as exc:  # noqa: BLE001
                    results["juan_practice"] = {"ok": False, "error": str(exc)[:400]}
                    for name in ("juan_editorial", "juan_ai_governance", "juan_ip_patents"):
                        set_agent_status(
                            name,
                            organization_id=organization_id,
                            status="failed",
                            article_id=juan_article,
                            error=str(exc)[:400],
                            ok=False,
                        )
            else:
                results["juan_practice"] = {
                    "ok": True,
                    "skipped": True,
                    "summary": "Sin artículo para briefs Juan",
                }

        ok = all(
            (v.get("ok") is not False)
            for v in results.values()
            if isinstance(v, dict) and not v.get("skipped")
        )
        summary = (
            f"Ciclo auto OK · pasos: {', '.join(steps_done)}"
            if ok
            else f"Ciclo auto con fallos · pasos: {', '.join(steps_done)}"
        )
        set_cycle_state(
            organization_id,
            status="completed" if ok else "failed",
            phase="done",
            current_agent=None,
            steps_done=steps_done,
            job_id=job_id,
            ok=ok,
            summary=summary,
        )
        return {
            "ok": ok,
            "summary": summary,
            "steps_done": steps_done,
            "article_id": article_id,
            "results": results,
        }
    except Exception as exc:  # noqa: BLE001
        set_cycle_state(
            organization_id,
            status="failed",
            phase="error",
            current_agent=None,
            steps_done=steps_done,
            job_id=job_id,
            ok=False,
            summary=str(exc)[:400],
        )
        return {"ok": False, "summary": str(exc)[:400], "steps_done": steps_done, "results": results}
    finally:
        release_cycle_lock(organization_id)
