"""Fase 5 — Configuración de proveedores de IA y métricas de uso."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ai_providers import AIProvider
from app.services.fase5_ai import (
    create_provider,
    mask_provider,
    seed_default_ollama,
    test_provider,
    usage_summary,
)
from app.services.crypto_keys import encrypt_secret, key_hint
from app.services.tenant import TenantContext, get_tenant_context, require_roles
from app.services.url_safety import validate_provider_base_url

router = APIRouter(prefix="/api/v1", tags=["fase5-ai"])

_AI_STAFF = (
    "agency_admin",
    "strategist",
    "writer",
    "editor",
    "legal_reviewer",
    "analyst",
    "community_manager",
)
_AI_ADMINS = ("agency_admin",)
_AI_USAGE_ROLES = ("agency_admin", "strategist", "analyst")


def _visible_providers(db: Session, ctx: TenantContext):
    return db.query(AIProvider).filter(
        or_(
            AIProvider.organization_id == ctx.org_id,
            (
                AIProvider.organization_id.is_(None)
                & AIProvider.is_local.is_(True)
            ),
        )
    )


def _editable_provider(
    db: Session,
    ctx: TenantContext,
    provider_id: int,
) -> AIProvider:
    provider = db.query(AIProvider).filter(AIProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    if provider.organization_id != ctx.org_id and not (
        provider.organization_id is None and ctx.is_superadmin
    ):
        raise HTTPException(404, "Provider not found")
    return provider


class ProviderCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    provider_type: str
    model_name: str
    api_key: str | None = None
    base_url: str | None = None
    monthly_budget_usd: float | None = Field(default=None, ge=0)
    daily_limit_requests: int | None = Field(default=None, ge=1)
    priority: int = 100


class ProviderUpdate(BaseModel):
    name: str | None = None
    model_name: str | None = None
    api_key: str | None = None
    base_url: str | None = None
    monthly_budget_usd: float | None = Field(default=None, ge=0)
    daily_limit_requests: int | None = Field(default=None, ge=1)
    priority: int | None = None
    is_active: bool | None = None


class ProviderTestRequest(BaseModel):
    prompt: str | None = Field(default=None, max_length=4000)


@router.get("/ai/providers")
def list_providers(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_AI_STAFF)
    from app.api.deps_env import allow_auto_seed

    if allow_auto_seed():
        seed_default_ollama(db)
    rows = _visible_providers(db, ctx).order_by(
        AIProvider.priority.asc(),
        AIProvider.id.asc(),
    ).all()
    return [mask_provider(p) for p in rows]


@router.get("/ai/models")
def list_models(
    provider_type: str | None = None,
    capability: str | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_AI_STAFF)
    from app.api.deps_env import allow_auto_seed
    from app.services.ai_model_catalog import list_ai_models, seed_ai_models

    if allow_auto_seed():
        seed_ai_models(db)
    return list_ai_models(db, provider_type=provider_type, capability=capability)


@router.post("/ai/providers")
def add_provider(
    body: ProviderCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_AI_ADMINS)
    try:
        provider = create_provider(
            db,
            name=body.name,
            provider_type=body.provider_type,
            model_name=body.model_name,
            api_key=body.api_key,
            base_url=body.base_url,
            monthly_budget_usd=body.monthly_budget_usd,
            daily_limit_requests=body.daily_limit_requests,
            priority=body.priority,
            organization_id=ctx.org_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return mask_provider(provider)


@router.patch("/ai/providers/{provider_id}")
def update_provider(
    provider_id: int,
    body: ProviderUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_AI_ADMINS)
    provider = _editable_provider(db, ctx, provider_id)

    if body.name is not None:
        provider.name = body.name
    if body.model_name is not None:
        provider.model_name = body.model_name
    if body.base_url is not None:
        try:
            provider.base_url = validate_provider_base_url(
                body.base_url,
                is_local=provider.is_local,
            ) or body.base_url
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
    if body.monthly_budget_usd is not None:
        provider.monthly_budget_usd = body.monthly_budget_usd
    if body.daily_limit_requests is not None:
        provider.daily_limit_requests = body.daily_limit_requests
    if body.priority is not None:
        provider.priority = body.priority
    if body.is_active is not None:
        provider.is_active = body.is_active
    if body.api_key:
        if provider.is_local:
            raise HTTPException(400, "Local providers do not use API keys")
        provider.encrypted_api_key = encrypt_secret(body.api_key)
        provider.key_hint = key_hint(body.api_key)

    db.commit()
    db.refresh(provider)
    return mask_provider(provider)


@router.delete("/ai/providers/{provider_id}")
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_AI_ADMINS)
    provider = _editable_provider(db, ctx, provider_id)
    if provider.is_local and provider.provider_type == "ollama":
        raise HTTPException(400, "Cannot delete default local Ollama provider — deactivate instead")
    db.delete(provider)
    db.commit()
    return {"deleted": provider_id}


@router.post("/ai/providers/{provider_id}/test")
def test_ai_provider(
    provider_id: int,
    body: ProviderTestRequest | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_AI_ADMINS)
    provider = _visible_providers(db, ctx).filter(AIProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")
    prompt = body.prompt if body else None
    return test_provider(db, provider, prompt=prompt)


@router.get("/ai/usage")
def get_usage(
    days: int = 30,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    require_roles(ctx, *_AI_USAGE_ROLES)
    return usage_summary(db, days=days, organization_id=ctx.org_id)


@router.get("/ai/ollama/status")
def ollama_status(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(get_tenant_context),
):
    """Estado en vivo de Ollama: conectado, modelo y latencia."""
    require_roles(ctx, *_AI_STAFF)
    import time
    import urllib.error
    import urllib.request

    from app.config import settings
    from app.api.deps_env import allow_auto_seed

    if allow_auto_seed():
        seed_default_ollama(db)
    local = (
        _visible_providers(db, ctx)
        .filter(AIProvider.is_local.is_(True), AIProvider.is_active.is_(True))
        .order_by(AIProvider.priority.asc())
        .first()
    )
    base = (local.base_url if local and local.base_url else settings.ollama_base_url).rstrip("/")
    model = (local.model_name if local else None) or settings.ollama_model
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(f"{base}/api/tags", timeout=3) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
        latency_ms = int((time.perf_counter() - started) * 1000)
        import json

        payload = json.loads(raw) if raw else {}
        models = [m.get("name") for m in (payload.get("models") or []) if m.get("name")]
        model_ready = any(
            m == model or m.startswith(f"{model}:") or model.startswith(m.split(":")[0])
            for m in models
        )
        return {
            "connected": True,
            "base_url": base,
            "model": model,
            "model_ready": model_ready or model in models,
            "available_models": models[:20],
            "latency_ms": latency_ms,
            "provider_id": local.id if local else None,
            "error": None
            if (model_ready or model in models)
            else f"Conectado, pero el modelo '{model}' no aparece en Ollama",
        }
    except Exception as exc:  # noqa: BLE001
        latency_ms = int((time.perf_counter() - started) * 1000)
        return {
            "connected": False,
            "base_url": base,
            "model": model,
            "model_ready": False,
            "available_models": [],
            "latency_ms": latency_ms,
            "provider_id": local.id if local else None,
            "error": str(exc)[:240],
        }
