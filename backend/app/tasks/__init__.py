from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Redis publicado en Windows a veces no acepta RESP3/HELLO; forzar protocol=2 (redis>=5)
try:
    import redis as _redis_mod
    import redis.connection as _redis_conn

    _redis_major = int(getattr(_redis_mod, "__version__", "0").split(".")[0] or 0)
    if _redis_major >= 5 and not getattr(_redis_conn.Connection, "_a360_proto2", False):
        _orig_conn_init = _redis_conn.Connection.__init__

        def _conn_init_protocol2(self, *args, **kwargs):
            kwargs.setdefault("protocol", 2)
            if "maint_notifications_config" not in kwargs:
                kwargs["maint_notifications_config"] = None
            return _orig_conn_init(self, *args, **kwargs)

        _redis_conn.Connection.__init__ = _conn_init_protocol2  # type: ignore[method-assign]
        _redis_conn.Connection._a360_proto2 = True  # type: ignore[attr-defined]
except Exception:
    pass

celery_app = Celery(
    "autoridad360",
    broker=settings.celery_broker_url,
    # Result backend desactivado: el estado vive en background_jobs (Etapa 2)
    backend=None,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Mexico_City",
    enable_utc=True,
    task_ignore_result=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
    task_time_limit=1800,
    task_soft_time_limit=1740,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.collect_rss_feeds": {"queue": "ingest"},
        "app.tasks.classify_and_verify": {"queue": "llm"},
        "app.tasks.analyze_article": {"queue": "llm"},
        "app.tasks.generate_weekly_report": {"queue": "llm"},
        # Misma cola llm que el worker editorial (-Q editorial,llm)
        "app.tasks.generate_content_package_task": {"queue": "llm"},
        "app.tasks.generate_blog_draft_task": {"queue": "llm"},
    },
    beat_schedule={
        "collect-rss-every-6-hours": {
            "task": "app.tasks.collect_rss_feeds",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "classify-and-verify-hourly": {
            "task": "app.tasks.classify_and_verify",
            "schedule": crontab(minute=15),
        },
        "weekly-report-monday-8am": {
            "task": "app.tasks.generate_weekly_report",
            "schedule": crontab(minute=0, hour=8, day_of_week=1),
        },
    },
)


def _run_tracked(job_id, self, work):
    from app.services.job_runner import mark_completed, mark_failed, mark_retrying, mark_running

    mark_running(job_id)
    try:
        result = work()
        mark_completed(job_id, result if isinstance(result, dict) else {"ok": True, "data": result})
        return result
    except Exception as exc:
        max_retries = getattr(self, "max_retries", 0) or 0
        retries = getattr(getattr(self, "request", None), "retries", 0) or 0
        if retries < max_retries:
            mark_retrying(job_id, str(exc))
            raise self.retry(exc=exc, countdown=30)
        mark_failed(job_id, str(exc))
        raise


@celery_app.task(bind=True, name="app.tasks.collect_rss_feeds", max_retries=2)
def collect_rss_feeds(
    self,
    organization_id: int | None = None,
    job_id: int | None = None,
):
    def work():
        from app.models import SessionLocal
        from app.rss.collector import collect_all_feeds

        db = SessionLocal()
        if organization_id is not None:
            db.info["organization_id"] = organization_id
        try:
            return collect_all_feeds(db, organization_id=organization_id)
        finally:
            db.close()

    return _run_tracked(job_id, self, work)


@celery_app.task(bind=True, name="app.tasks.classify_and_verify", max_retries=2)
def classify_and_verify(
    self,
    organization_id: int | None = None,
    job_id: int | None = None,
):
    def work():
        from app.models import SessionLocal
        from app.services.llm import process_unclassified
        from app.services.scoring import score_verified_articles

        db = SessionLocal()
        if organization_id is not None:
            db.info["organization_id"] = organization_id
        try:
            result = process_unclassified(db, limit=25, organization_id=organization_id)
            score_verified_articles(db, organization_id=organization_id)
            return result
        finally:
            db.close()

    return _run_tracked(job_id, self, work)


@celery_app.task(bind=True, name="app.tasks.analyze_article", max_retries=1)
def analyze_article_task(
    self,
    article_id: int,
    organization_id: int | None = None,
    job_id: int | None = None,
):
    def work():
        from app.models import NewsArticle, SessionLocal
        from app.services.llm import classify_article, verify_article

        db = SessionLocal()
        if organization_id is not None:
            db.info["organization_id"] = organization_id
        try:
            query = db.query(NewsArticle).filter(NewsArticle.id == article_id)
            if organization_id is not None:
                query = query.filter(NewsArticle.organization_id == organization_id)
            article = query.first()
            if not article:
                raise ValueError("Article not found")
            classify_article(db, article)
            verification = verify_article(db, article)
            return {
                "article_id": article.id,
                "status": article.status,
                "publishable": bool(verification.get("publishable")),
            }
        finally:
            db.close()

    return _run_tracked(job_id, self, work)


@celery_app.task(bind=True, name="app.tasks.generate_weekly_report", max_retries=2)
def generate_weekly_report_task(
    self,
    organization_id: int | None = None,
    job_id: int | None = None,
):
    def work():
        from app.models import SessionLocal
        from app.services.reports import generate_weekly_report

        db = SessionLocal()
        if organization_id is not None:
            db.info["organization_id"] = organization_id
        try:
            report = generate_weekly_report(db, organization_id=organization_id)
            return {"report_id": report.id, "week_start": str(report.week_start.date())}
        finally:
            db.close()

    return _run_tracked(job_id, self, work)


@celery_app.task(bind=True, name="app.tasks.generate_content_package_task", max_retries=1)
def generate_content_package_task(
    self,
    article_id: int,
    languages: list[str] | None = None,
    prefer_llm: bool = True,
    organization_id: int | None = None,
    formats: list[str] | None = None,
    package_id: int | None = None,
    regenerate: bool = False,
    provider_mode: str = "local",
    job_id: int | None = None,
):
    def work():
        from app.models import SessionLocal
        from app.models.news import NewsArticle
        from app.services.content_generation import create_content_package

        db = SessionLocal()
        if organization_id is not None:
            db.info["organization_id"] = organization_id
        try:
            article_query = db.query(NewsArticle).filter(NewsArticle.id == article_id)
            if organization_id is not None:
                article_query = article_query.filter(
                    NewsArticle.organization_id == organization_id
                )
            article = article_query.first()
            if not article:
                return {"error": "Article not found"}

            package = create_content_package(
                db,
                article,
                languages=languages or ["es"],
                prefer_llm=prefer_llm,
                organization_id=organization_id,
                formats=formats,
                package_id=package_id,
                regenerate=regenerate,
                provider_mode=provider_mode or "local",
            )
            return {
                "package_id": package.id,
                "article_id": article_id,
                "languages": languages or ["es"],
                "formats": formats,
                "status": "completed",
            }
        finally:
            db.close()

    return _run_tracked(job_id, self, work)


@celery_app.task(bind=True, name="app.tasks.generate_blog_draft_task", max_retries=1)
def generate_blog_draft_task(
    self,
    article_id: int,
    regenerate: bool = True,
    organization_id: int | None = None,
    job_id: int | None = None,
):
    def work():
        from app.models import NewsArticle, SessionLocal
        from app.services.reports import create_blog_draft_from_article

        db = SessionLocal()
        if organization_id is not None:
            db.info["organization_id"] = organization_id
        try:
            article_query = db.query(NewsArticle).filter(NewsArticle.id == article_id)
            if organization_id is not None:
                article_query = article_query.filter(
                    NewsArticle.organization_id == organization_id
                )
            article = article_query.first()
            if not article:
                raise ValueError("Article not found")
            post = create_blog_draft_from_article(
                db,
                article,
                regenerate=regenerate,
                organization_id=organization_id,
            )
            return {
                "post_id": post.id,
                "article_id": article_id,
                "status": post.status,
            }
        finally:
            db.close()

    return _run_tracked(job_id, self, work)
