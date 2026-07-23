"""Enrutador de modelos — tareas simples → local; complejas → comercial."""

from __future__ import annotations

# Preferencia de enrutamiento por tipo de tarea
# local_first: intenta Ollama, fallback a pago si falla y hay proveedor
# local_only: solo local
# paid_preferred: intenta pago activo, fallback local
# paid_only: solo comercial

TASK_ROUTING: dict[str, str] = {
    "classify": "local_first",
    "verify": "local_first",
    # Solo hay Ollama local activo; paid_preferred solo añadía latencia inútil
    "generate_content": "local_first",
    "generate_content_batch": "local_first",
    "translate": "local_first",
    "brand_rewrite": "local_first",
    "complex_analysis": "paid_only",
    "test_connection": "local_first",
    # Agentes reales — razonamiento / crítica (local preferido)
    "agent_plan": "local_first",
    "agent_critique": "local_first",
    "blog_article": "local_first",
}

# Estimación de costo USD por 1K tokens (aprox.) para dashboard
COST_PER_1K: dict[str, float] = {
    "ollama": 0.0,
    "openai": 0.005,
    "anthropic": 0.008,
    "gemini": 0.002,
}


def routing_mode(task_type: str) -> str:
    return TASK_ROUTING.get(task_type, "local_first")


def resolve_routing_mode(
    task_type: str,
    provider_mode: str | None = None,
) -> str:
    """Convierte preferencia de UI (local/cloud/auto) a modo de enrutamiento."""
    mode = (provider_mode or "auto").strip().lower()
    if mode in {"local", "local_only", "ollama"}:
        return "local_only"
    if mode in {"cloud", "api", "paid", "paid_only", "web"}:
        return "paid_only"
    if mode in {"cloud_first", "paid_preferred"}:
        return "paid_preferred"
    return routing_mode(task_type)


def estimate_cost(provider_type: str, prompt_tokens: int, completion_tokens: int) -> float:
    rate = COST_PER_1K.get(provider_type, 0.005)
    total = (prompt_tokens or 0) + (completion_tokens or 0)
    return round((total / 1000.0) * rate, 6)
