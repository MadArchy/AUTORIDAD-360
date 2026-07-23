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
    "generate_content": "paid_preferred",
    "translate": "paid_preferred",
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


def estimate_cost(provider_type: str, prompt_tokens: int, completion_tokens: int) -> float:
    rate = COST_PER_1K.get(provider_type, 0.005)
    total = (prompt_tokens or 0) + (completion_tokens or 0)
    return round((total / 1000.0) * rate, 6)
