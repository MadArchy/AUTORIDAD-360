"""Guards de entorno para rutas sensibles (seeds)."""
from fastapi import HTTPException

from app.config import settings


def require_non_production(action: str = "This action") -> None:
    """Bloquea en production. Seeds y utilidades de bootstrap solo en development/pilot."""
    if settings.is_production:
        raise HTTPException(
            status_code=403,
            detail=f"{action} is disabled in production.",
        )


def allow_auto_seed() -> bool:
    """Lazy-seed en GET/startup solo fuera de production."""
    return not settings.is_production
