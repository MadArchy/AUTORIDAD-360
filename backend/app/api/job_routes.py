from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.models import get_db
from app.models.background_jobs import BackgroundJob
from app.services.tenant import TenantContext, get_tenant_context, require_roles
from app.services.job_runner import enqueue_job, job_to_dict
from app.tasks import collect_rss_feeds, classify_and_verify, generate_weekly_report_task
from app.rss.collector import collect_all_feeds
from app.services.llm import process_unclassified
from app.services.scoring import score_verified_articles
from app.services.reports import generate_weekly_report

router = APIRouter(prefix="/api/v1", tags=["jobs"])

_STAFF = (
    "agency_admin",
    "strategist",
    "writer",
    "editor",
    "legal_reviewer",
    "analyst",
    "community_manager",
)

@router.post("/jobs/collect")
def trigger_collect(
    async_mode: bool = False,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_roles(ctx, *_STAFF)
    if async_mode:
        job = enqueue_job(
            db,
            job_name="collect",
            celery_task=collect_rss_feeds,
            idempotency_key=idempotency_key,
            organization_id=ctx.org_id,
            task_kwargs={"organization_id": ctx.org_id},
        )
        return job_to_dict(job)
    return collect_all_feeds(db, organization_id=ctx.org_id)


@router.post("/jobs/classify")
def trigger_classify(
    async_mode: bool = False,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_roles(ctx, *_STAFF)
    if async_mode:
        job = enqueue_job(
            db,
            job_name="classify",
            celery_task=classify_and_verify,
            idempotency_key=idempotency_key,
            organization_id=ctx.org_id,
            task_kwargs={"organization_id": ctx.org_id},
        )
        return job_to_dict(job)
    result = process_unclassified(db, organization_id=ctx.org_id)
    score_verified_articles(db, organization_id=ctx.org_id)
    return result


@router.post("/jobs/report")
def trigger_report(
    async_mode: bool = False,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_roles(ctx, *_STAFF)
    if async_mode:
        job = enqueue_job(
            db,
            job_name="report",
            celery_task=generate_weekly_report_task,
            idempotency_key=idempotency_key,
            organization_id=ctx.org_id,
            task_kwargs={"organization_id": ctx.org_id},
        )
        return job_to_dict(job)
    report = generate_weekly_report(db, organization_id=ctx.org_id)
    return {"report_id": report.id, "markdown": report.markdown_content}


@router.get("/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)

    job = (
        db.query(BackgroundJob)
        .filter(
            BackgroundJob.id == job_id,
            BackgroundJob.organization_id == ctx.org_id,
        )
        .first()
    )
    if not job:
        raise HTTPException(404, "Job not found")
    return job_to_dict(job)


@router.get("/jobs")
def list_jobs(
    limit: int = 20,
    job_name: str | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_STAFF)

    limit = max(1, min(int(limit or 20), 100))
    q = (
        db.query(BackgroundJob)
        .filter(BackgroundJob.organization_id == ctx.org_id)
        .order_by(BackgroundJob.id.desc())
    )
    if job_name:
        q = q.filter(BackgroundJob.job_name == job_name)
    return [job_to_dict(j) for j in q.limit(limit).all()]
