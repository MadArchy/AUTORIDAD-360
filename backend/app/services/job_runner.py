"""Enqueue + estado de background jobs (Celery)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.models.background_jobs import BackgroundJob

ACTIVE = {"queued", "running", "retrying"}
IDEMPOTENT_OK = ACTIVE | {"completed"}

# Cola explícita por job (evita quedar en colas huérfanas como "generate")
_JOB_QUEUES: dict[str, str] = {
    "collect": "ingest",
    "classify": "llm",
    "report": "llm",
    "analyze_article": "llm",
    "content_package": "llm",
    "blog_draft": "llm",
    "agent_auto_cycle": "llm",
}


def job_to_dict(job: BackgroundJob) -> dict[str, Any]:
    return {
        "id": job.id,
        "organization_id": job.organization_id,
        "job_name": job.job_name,
        "idempotency_key": job.idempotency_key,
        "status": job.status,
        "celery_task_id": job.celery_task_id,
        "attempt": job.attempt,
        "result_json": job.result_json,
        "error_message": job.error_message,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


def enqueue_job(
    db: Session,
    *,
    job_name: str,
    celery_task: Callable,
    idempotency_key: str | None = None,
    task_kwargs: dict[str, Any] | None = None,
    organization_id: int | None = None,
) -> BackgroundJob:
    """
    Encola un job Celery con clave de idempotencia.
    Si ya existe queued/running/retrying/completed con la misma clave → reutiliza.
    Si failed → reencola (nuevo intento sobre el mismo registro).
    """
    key = (idempotency_key or "").strip() or f"{job_name}:{uuid.uuid4().hex}"
    existing = (
        db.query(BackgroundJob)
        .filter(
            BackgroundJob.organization_id == organization_id,
            BackgroundJob.job_name == job_name,
            BackgroundJob.idempotency_key == key,
        )
        .first()
    )
    if existing and existing.status in IDEMPOTENT_OK:
        return existing

    if existing and existing.status == "failed":
        job = existing
        job.status = "queued"
        job.error_message = None
        job.result_json = None
        job.finished_at = None
        job.started_at = None
        job.celery_task_id = None
        job.attempt = (job.attempt or 0) + 1
        job.updated_at = datetime.utcnow()
    else:
        job = BackgroundJob(
            organization_id=organization_id,
            job_name=job_name,
            idempotency_key=key,
            status="queued",
            attempt=0,
        )
        db.add(job)

    db.commit()
    db.refresh(job)
    celery_kwargs = {**(task_kwargs or {}), "job_id": job.id}

    try:
        # ignore_result: estado canónico en background_jobs
        apply_kwargs: dict[str, Any] = {
            "kwargs": celery_kwargs,
            "ignore_result": True,
        }
        queue = _JOB_QUEUES.get(job_name)
        if queue:
            apply_kwargs["queue"] = queue
        async_result = celery_task.apply_async(**apply_kwargs)
        job.celery_task_id = async_result.id
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
    except Exception as exc:
        # Fallback piloto (Redis RESP3/HELLO roto en algunos hosts Windows)
        import threading

        def _local_run():
            try:
                celery_task.apply(kwargs=celery_kwargs)
            except Exception:
                pass

        threading.Thread(
            target=_local_run, daemon=True, name=f"a360-job-{job.id}"
        ).start()
        job.celery_task_id = f"local:{job.id}"
        job.error_message = f"celery_broker_fallback: {exc}"[:500]
        job.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(job)
    return job


def _get_job(db: Session, job_id: int | None) -> BackgroundJob | None:
    if not job_id:
        return None
    return db.query(BackgroundJob).filter(BackgroundJob.id == job_id).first()


def mark_running(job_id: int | None) -> None:
    from app.models import SessionLocal

    if not job_id:
        return
    db = SessionLocal()
    try:
        job = _get_job(db, job_id)
        if not job:
            return
        job.status = "running"
        job.started_at = job.started_at or datetime.utcnow()
        job.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def mark_completed(job_id: int | None, result: Any = None) -> None:
    from app.models import SessionLocal

    if not job_id:
        return
    db = SessionLocal()
    try:
        job = _get_job(db, job_id)
        if not job:
            return
        job.status = "completed"
        job.finished_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.error_message = None
        if result is not None:
            job.result_json = result if isinstance(result, dict) else {"result": result}
        db.commit()
    finally:
        db.close()


def mark_failed(job_id: int | None, error: str) -> None:
    from app.models import SessionLocal

    if not job_id:
        return
    db = SessionLocal()
    try:
        job = _get_job(db, job_id)
        if not job:
            return
        job.status = "failed"
        job.finished_at = datetime.utcnow()
        job.updated_at = datetime.utcnow()
        job.error_message = (error or "")[:2000]
        db.commit()
    finally:
        db.close()


def mark_retrying(job_id: int | None, error: str) -> None:
    from app.models import SessionLocal

    if not job_id:
        return
    db = SessionLocal()
    try:
        job = _get_job(db, job_id)
        if not job:
            return
        job.status = "retrying"
        job.attempt = (job.attempt or 0) + 1
        job.error_message = (error or "")[:2000]
        job.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
