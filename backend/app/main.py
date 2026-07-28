from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.agent_routes import router as agent_router
from app.api.ai_routes import router as ai_router
from app.api.metrics_routes import router as metrics_router
from app.api.ops_routes import router as ops_router
from app.api.org_routes import router as org_router
from app.api.routes import router
from app.api.job_routes import router as job_router
from app.api.auth_routes import router as auth_router
from app.api.publish_routes import router as publish_router
from app.api.legal_seo_routes import router as legal_seo_router
from app.api.marketing_routes import router as marketing_router
from app.api.saas_routes import router as saas_router
from app.api.public_routes import router as public_router
from app.config import settings
from app.models import Base, SessionLocal, engine

logger = logging.getLogger("autoridad360.http")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    import app.models.org  # noqa: F401
    import app.models.editorial  # noqa: F401
    import app.models.profile  # noqa: F401
    import app.models.content  # noqa: F401
    import app.models.operations  # noqa: F401
    import app.models.ai_providers  # noqa: F401
    import app.models.ai_models  # noqa: F401
    import app.models.background_jobs  # noqa: F401
    import app.models.learning  # noqa: F401
    import app.models.auth_sessions  # noqa: F401
    import app.models.publishing  # noqa: F401
    import app.models.legal_seo  # noqa: F401
    import app.models.marketing  # noqa: F401
    import app.models.saas  # noqa: F401

    settings.assert_secure_production()
    if settings.is_production:
        # Producción exige `alembic upgrade head`; nunca modifica esquema al arrancar.
        yield
        return
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        from app.services.fase5_ai import seed_default_ollama
        from app.services.calendar_ops import seed_cadence
        from app.services.tenant_seed import seed_tenants

        seed_tenants(db)
        seed_cadence(db)
        seed_default_ollama(db)
    except Exception as exc:
        db.rollback()
        print(f"[lifespan] seed warning: {exc!r}")
    finally:
        db.close()
    yield


app = FastAPI(
    title="Autoridad 360 — Inteligencia Editorial",
    description="Fase 1–7: ciclo completo con métricas, leads y aprendizaje editorial",
    version="0.7.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            round((time.perf_counter() - started) * 1000),
        )
        raise
    duration_ms = round((time.perf_counter() - started) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["Server-Timing"] = f"app;dur={duration_ms}"
    logger.info(
        "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response

app.include_router(router)
app.include_router(job_router)
app.include_router(ops_router)
app.include_router(ai_router)
app.include_router(agent_router)
app.include_router(org_router)
app.include_router(metrics_router)
app.include_router(publish_router)
app.include_router(legal_seo_router)
app.include_router(marketing_router)
app.include_router(saas_router)
app.include_router(public_router)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])

# Creatividades generadas (PNG) — desarrollo / piloto local
_media_dir = Path(__file__).resolve().parent.parent / "media"
_media_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_dir)), name="media")


@app.get("/")
def root():
    return {
        "status": "online",
        "service": "Autoridad 360",
        "phase": "1-7",
        "app_env": settings.app_env,
        "client": settings.client_name,
        "docs_url": "/docs",
        "allow_header_auth": settings.allow_header_auth,
    }

