"""Fase 5 — Gateway de IA canónico (aislado de sobrescrituras paralelas)."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.config import settings
from app.models.ai_providers import AIProvider, AIUsageLog
from app.services.crypto_keys import (
    can_decrypt_secret,
    decrypt_secret,
    decrypt_secret_with_rotation,
    encrypt_secret,
    key_hint,
)
from app.services.model_router import estimate_cost, resolve_routing_mode, routing_mode
from app.services.url_safety import validate_provider_base_url

SUPPORTED_TYPES = {"ollama", "openai", "anthropic", "gemini"}
logger = logging.getLogger(__name__)


def seed_default_ollama(db: Session) -> AIProvider:
    from app.services.ai_model_catalog import seed_ai_models, resolve_chat_model

    seed_ai_models(db)
    model_name = resolve_chat_model(db, "ollama", settings.ollama_model)

    existing = (
        db.query(AIProvider)
        .filter(
            AIProvider.provider_type == "ollama",
            AIProvider.is_local.is_(True),
            AIProvider.organization_id.is_(None),
        )
        .first()
    )
    if existing:
        desired = (settings.ollama_base_url or "").rstrip("/")
        changed = False
        if existing.model_name != model_name and not existing.meta_json:
            existing.model_name = model_name
            changed = True
        # Corrige URLs loopback guardadas cuando el runtime está en Docker.
        current = (existing.base_url or "").rstrip("/")
        if desired and current and (
            "127.0.0.1" in current or "localhost" in current.lower()
        ) and current != desired:
            existing.base_url = desired
            changed = True
        if changed:
            db.commit()
            db.refresh(existing)
        return existing

    provider = AIProvider(
        name="Ollama local",
        provider_type="ollama",
        model_name=model_name,
        base_url=settings.ollama_base_url,
        is_local=True,
        is_active=True,
        priority=1,
        monthly_budget_usd=0,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def mask_provider(provider: AIProvider) -> dict[str, Any]:
    has_key = bool(provider.encrypted_api_key)
    key_ok = True if provider.is_local or not has_key else can_decrypt_secret(
        provider.encrypted_api_key
    )
    return {
        "id": provider.id,
        "organization_id": provider.organization_id,
        "name": provider.name,
        "provider_type": provider.provider_type,
        "model_name": provider.model_name,
        "base_url": provider.base_url,
        "key_hint": provider.key_hint,
        "has_api_key": has_key,
        "key_ok": key_ok,
        "is_local": provider.is_local,
        "is_active": provider.is_active,
        "monthly_budget_usd": float(provider.monthly_budget_usd)
        if provider.monthly_budget_usd is not None
        else None,
        "daily_limit_requests": provider.daily_limit_requests,
        "priority": provider.priority,
        "last_tested_at": provider.last_tested_at.isoformat() if provider.last_tested_at else None,
        "last_test_ok": provider.last_test_ok,
        "created_at": provider.created_at.isoformat() if provider.created_at else None,
    }


def create_provider(
    db: Session,
    *,
    name: str,
    provider_type: str,
    model_name: str,
    api_key: str | None = None,
    base_url: str | None = None,
    monthly_budget_usd: float | None = None,
    daily_limit_requests: int | None = None,
    priority: int = 100,
    organization_id: int | None = None,
) -> AIProvider:
    ptype = provider_type.strip().lower()
    if ptype not in SUPPORTED_TYPES:
        raise ValueError(f"Unsupported provider_type: {ptype}")

    is_local = ptype == "ollama"
    if is_local and api_key:
        raise ValueError("Local providers do not use API keys")
    if not is_local and not api_key:
        raise ValueError("Paid providers require an API key")

    if not is_local and organization_id is not None:
        from app.models.org import Organization
        from app.services.plans import assert_byok_allowed

        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if org:
            assert_byok_allowed(org)

    safe_base = validate_provider_base_url(base_url, is_local=is_local)
    if is_local and safe_base is None:
        safe_base = settings.ollama_base_url.rstrip("/")

    provider = AIProvider(
        organization_id=organization_id,
        name=name.strip(),
        provider_type=ptype,
        model_name=model_name.strip(),
        base_url=safe_base,
        encrypted_api_key=encrypt_secret(api_key) if api_key else None,
        key_hint=key_hint(api_key) if api_key else None,
        is_local=is_local,
        is_active=True,
        monthly_budget_usd=monthly_budget_usd,
        daily_limit_requests=daily_limit_requests,
        priority=priority,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


def _log_usage(
    db: Session,
    *,
    provider: AIProvider | None,
    task_type: str,
    model_used: str,
    is_local: bool,
    success: bool,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    cost = None
    if provider and success:
        cost = estimate_cost(
            provider.provider_type,
            prompt_tokens or 0,
            completion_tokens or 0,
        )
    db.add(
        AIUsageLog(
            organization_id=(
                db.info.get("organization_id")
                or (provider.organization_id if provider else None)
            ),
            provider_id=provider.id if provider else None,
            task_type=task_type,
            model_used=model_used,
            is_local=is_local,
            success=success,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            error_message=error_message,
        )
    )
    db.commit()


def _ollama_base_url(provider: AIProvider) -> str:
    """Resuelve la URL de Ollama usable desde el proceso actual (Docker vs host)."""
    configured = (provider.base_url or "").strip().rstrip("/")
    fallback = (settings.ollama_base_url or "http://127.0.0.1:11434").rstrip("/")
    if not configured:
        return fallback
    # En contenedores, 127.0.0.1/localhost apunta al propio container, no al host.
    lowered = configured.lower()
    if "127.0.0.1" in lowered or "localhost" in lowered:
        if "host.docker.internal" in fallback.lower() or fallback != configured:
            return fallback
    return configured


def _call_ollama(provider: AIProvider, prompt: str) -> str:
    base = _ollama_base_url(provider)
    url = f"{base}/api/chat"
    # gemma4:e2b tiene "thinking": sin think=false gasta tokens en razonar
    # y a menudo deja message.content vacío → fallos/timeouts.
    payload = {
        "model": provider.model_name or settings.ollama_model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 1200,
        },
    }
    with httpx.Client(timeout=settings.llm_request_timeout_seconds) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    message = data.get("message") or {}
    content = (message.get("content") or "").strip()
    if not content:
        # Fallback por si el runtime ignora think=false
        thinking = (message.get("thinking") or "").strip()
        if thinking:
            content = thinking
    if not content:
        raise ValueError("Ollama returned empty content")
    return content


def _call_openai_compatible(provider: AIProvider, prompt: str, api_key: str) -> str:
    base = (provider.base_url or "https://api.openai.com/v1").rstrip("/")
    url = f"{base}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": provider.model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    with httpx.Client(timeout=settings.llm_request_timeout_seconds) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["choices"][0]["message"]["content"]


def _call_anthropic(provider: AIProvider, prompt: str, api_key: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": provider.model_name,
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }
    with httpx.Client(timeout=settings.llm_request_timeout_seconds) as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
    parts = data.get("content") or []
    texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
    return "\n".join(t for t in texts if t)


def _call_gemini(provider: AIProvider, prompt: str, api_key: str) -> str:
    model = provider.model_name
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    with httpx.Client(timeout=settings.llm_request_timeout_seconds) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini returned no candidates")
    parts = candidates[0].get("content", {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts if isinstance(p, dict))


def _invoke(provider: AIProvider, prompt: str, db: Session | None = None) -> str:
    if provider.provider_type == "ollama":
        return _call_ollama(provider, prompt)

    if not provider.encrypted_api_key:
        raise ValueError(f"Provider {provider.name} has no API key")
    api_key, needs_reencrypt = decrypt_secret_with_rotation(provider.encrypted_api_key)
    if needs_reencrypt and db is not None:
        provider.encrypted_api_key = encrypt_secret(api_key)
        db.add(provider)
        db.commit()
        logger.info("Re-encrypted API key for provider_id=%s with current ENCRYPTION_KEY", provider.id)

    if provider.provider_type == "openai":
        return _call_openai_compatible(provider, prompt, api_key)
    if provider.provider_type == "anthropic":
        return _call_anthropic(provider, prompt, api_key)
    if provider.provider_type == "gemini":
        return _call_gemini(provider, prompt, api_key)
    raise ValueError(f"Unsupported provider_type: {provider.provider_type}")


def _providers_for_task(
    db: Session,
    task_type: str,
    provider_mode: str | None = None,
) -> list[AIProvider]:
    if not db.info.get("a360_ai_catalog_ready"):
        seed_default_ollama(db)
        db.info["a360_ai_catalog_ready"] = True
    mode = resolve_routing_mode(task_type, provider_mode)
    query = db.query(AIProvider).filter(AIProvider.is_active.is_(True))
    organization_id = db.info.get("organization_id")
    if organization_id is not None:
        query = query.filter(
            or_(
                AIProvider.organization_id == organization_id,
                (
                    AIProvider.organization_id.is_(None)
                    & AIProvider.is_local.is_(True)
                ),
            )
        )
    rows = query.order_by(AIProvider.priority.asc(), AIProvider.id.asc()).all()
    local = [p for p in rows if p.is_local]
    paid = [p for p in rows if not p.is_local]

    if mode == "local_only":
        return local
    if mode == "paid_only":
        return paid
    if mode == "paid_preferred":
        return paid + local
    return local + paid


def _provider_within_budget(db: Session, provider: AIProvider) -> tuple[bool, str | None]:
    """True si el proveedor puede recibir una nueva llamada."""
    if provider.is_local:
        return True, None

    now = datetime.utcnow()
    if provider.daily_limit_requests is not None:
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_count = (
            db.query(func.count(AIUsageLog.id))
            .filter(
                AIUsageLog.provider_id == provider.id,
                AIUsageLog.created_at >= day_start,
            )
            .scalar()
            or 0
        )
        if int(day_count) >= int(provider.daily_limit_requests):
            return False, "daily_request_limit_reached"

    if provider.monthly_budget_usd is not None:
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        spent = (
            db.query(func.coalesce(func.sum(AIUsageLog.cost_usd), 0.0))
            .filter(
                AIUsageLog.provider_id == provider.id,
                AIUsageLog.created_at >= month_start,
                AIUsageLog.success.is_(True),
            )
            .scalar()
        )
        if float(spent or 0) >= float(provider.monthly_budget_usd):
            return False, "monthly_budget_exhausted"
    return True, None


def complete(
    db: Session,
    *,
    task_type: str,
    prompt: str,
    provider_mode: str | None = None,
) -> tuple[str, dict[str, Any]]:
    providers = _providers_for_task(db, task_type, provider_mode=provider_mode)
    if not providers:
        mode = (provider_mode or "auto").lower()
        if mode in {"cloud", "api", "paid", "paid_only", "web"}:
            raise RuntimeError(
                "No hay proveedor cloud activo con API key. "
                "Configúralo en Modelos de IA (OpenAI, Anthropic o Gemini)."
            )
        if mode in {"local", "local_only", "ollama"}:
            raise RuntimeError(
                "No hay proveedor local (Ollama) activo. "
                "Inicia Ollama o elige generación por API."
            )
        raise RuntimeError("No active AI providers configured")

    errors: list[str] = []
    for provider in providers:
        ok_budget, budget_reason = _provider_within_budget(db, provider)
        if not ok_budget:
            errors.append(
                f"{provider.provider_type}/{provider.model_name}: skipped ({budget_reason})"
            )
            logger.warning(
                "llm_call_skipped provider=%s reason=%s",
                provider.model_name,
                budget_reason,
            )
            continue
        started = time.perf_counter()
        try:
            text = _invoke(provider, prompt, db=db)
            latency_ms = int((time.perf_counter() - started) * 1000)
            prompt_tokens = max(1, len(prompt) // 4)
            completion_tokens = max(1, len(text) // 4)
            _log_usage(
                db,
                provider=provider,
                task_type=task_type,
                model_used=provider.model_name,
                is_local=provider.is_local,
                success=True,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
            )
            logger.info(
                "llm_call_complete task_type=%s provider=%s model=%s success=true "
                "latency_ms=%s prompt_chars=%s completion_chars=%s",
                task_type,
                provider.provider_type,
                provider.model_name,
                latency_ms,
                len(prompt),
                len(text),
            )
            return text, {
                "provider_id": provider.id,
                "provider_type": provider.provider_type,
                "model_used": provider.model_name,
                "is_local": provider.is_local,
                "latency_ms": latency_ms,
            }
        except Exception as exc:  # noqa: BLE001
            latency_ms = int((time.perf_counter() - started) * 1000)
            errors.append(f"{provider.provider_type}/{provider.model_name}: {exc}")
            _log_usage(
                db,
                provider=provider,
                task_type=task_type,
                model_used=provider.model_name,
                is_local=provider.is_local,
                success=False,
                latency_ms=latency_ms,
                error_message=str(exc)[:500],
            )
            logger.warning(
                "llm_call_complete task_type=%s provider=%s model=%s success=false "
                "latency_ms=%s error=%s",
                task_type,
                provider.provider_type,
                provider.model_name,
                latency_ms,
                str(exc)[:300],
            )

    raise RuntimeError(
        "All AI providers failed: "
        + " | ".join(errors)
        + (
            " Si ves ENCRYPTION_KEY, vuelve a pegar la API key en Inteligencia Artificial."
            if any("ENCRYPTION_KEY" in e or "decrypt" in e.lower() for e in errors)
            else ""
        )
    )


def test_provider(
    db: Session, provider: AIProvider, prompt: str | None = None
) -> dict[str, Any]:
    started = time.perf_counter()
    user_prompt = (prompt or "").strip() or "Responde solo con la palabra OK."
    try:
        text = _invoke(provider, user_prompt, db=db)
        ok = True
        error = None
        latency_ms = int((time.perf_counter() - started) * 1000)
        prompt_tokens = max(8, len(user_prompt) // 4)
        completion_tokens = max(1, len(text or "") // 4)
        _log_usage(
            db,
            provider=provider,
            task_type="test_connection",
            model_used=provider.model_name,
            is_local=provider.is_local,
            success=True,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
        )
    except Exception as exc:  # noqa: BLE001
        ok = False
        error = str(exc)
        text = None
        latency_ms = int((time.perf_counter() - started) * 1000)
        prompt_tokens = max(8, len(user_prompt) // 4)
        completion_tokens = 0
        _log_usage(
            db,
            provider=provider,
            task_type="test_connection",
            model_used=provider.model_name,
            is_local=provider.is_local,
            success=False,
            latency_ms=latency_ms,
            error_message=error[:500],
        )

    provider.last_tested_at = datetime.utcnow()
    provider.last_test_ok = ok
    db.commit()
    return {
        "provider_id": provider.id,
        "ok": ok,
        "latency_ms": latency_ms,
        "response_preview": (text or "")[:500] if text else None,
        "text": text or error or "",
        "model": provider.model_name,
        "fallback_triggered": False,
        "total_tokens": prompt_tokens + completion_tokens,
        "estimated_cost_usd": 0 if provider.is_local else round((prompt_tokens + completion_tokens) * 0.000002, 6),
        "error": error,
    }


def usage_summary(
    db: Session,
    days: int = 30,
    organization_id: int | None = None,
) -> dict[str, Any]:
    since = datetime.utcnow() - timedelta(days=max(1, days))
    query = db.query(AIUsageLog).filter(AIUsageLog.created_at >= since)
    if organization_id is not None:
        query = query.filter(AIUsageLog.organization_id == organization_id)
    rows = query.all()
    by_provider: dict[str, dict[str, Any]] = {}
    total_cost = 0.0
    success = 0
    failed = 0
    for row in rows:
        key = row.model_used or "unknown"
        bucket = by_provider.setdefault(
            key,
            {"model": key, "calls": 0, "success": 0, "failed": 0, "cost_usd": 0.0},
        )
        bucket["calls"] += 1
        if row.success:
            bucket["success"] += 1
            success += 1
        else:
            bucket["failed"] += 1
            failed += 1
        cost = float(row.cost_usd or 0)
        bucket["cost_usd"] = round(bucket["cost_usd"] + cost, 6)
        total_cost += cost

    local_query = db.query(func.count(AIUsageLog.id)).filter(
        AIUsageLog.created_at >= since,
        AIUsageLog.is_local.is_(True),
    )
    if organization_id is not None:
        local_query = local_query.filter(AIUsageLog.organization_id == organization_id)
    local_calls = local_query.scalar() or 0
    return {
        "days": days,
        "total_calls": len(rows),
        "success": success,
        "failed": failed,
        "local_calls": int(local_calls),
        "total_cost_usd": round(total_cost, 6),
        "by_model": list(by_provider.values()),
        "likes_ignored": True,
        "local_pct": round((int(local_calls) / len(rows)) * 100, 1) if rows else 0.0,
        "paid_calls": max(0, len(rows) - int(local_calls)),
    }
