"""Seed y lookup del catálogo ai_models."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.ai_models import AIModel


def _defaults() -> list[dict]:
    return [
        {
            "provider_type": "ollama",
            "model_key": settings.ollama_model,
            "display_name": f"Ollama · {settings.ollama_model}",
            "capability": "chat",
            "is_default": True,
        },
        {
            "provider_type": "ollama",
            "model_key": settings.vector_embedding_model.replace("ollama/", ""),
            "display_name": "Ollama · nomic-embed-text",
            "capability": "embed",
            "is_default": True,
        },
        {
            "provider_type": "openai",
            "model_key": "gpt-4o",
            "display_name": "OpenAI · GPT-4o",
            "capability": "chat",
            "is_default": True,
        },
        {
            "provider_type": "anthropic",
            "model_key": "claude-3-5-sonnet-20240620",
            "display_name": "Anthropic · Claude 3.5 Sonnet",
            "capability": "chat",
            "is_default": True,
        },
    ]


def seed_ai_models(db: Session) -> list[AIModel]:
    created: list[AIModel] = []
    for row in _defaults():
        existing = (
            db.query(AIModel)
            .filter(
                AIModel.provider_type == row["provider_type"],
                AIModel.model_key == row["model_key"],
                AIModel.capability == row["capability"],
            )
            .first()
        )
        if existing:
            created.append(existing)
            continue
        model = AIModel(
            provider_type=row["provider_type"],
            model_key=row["model_key"],
            display_name=row["display_name"],
            capability=row["capability"],
            is_active=True,
            is_default=row["is_default"],
        )
        db.add(model)
        created.append(model)
    db.commit()
    for m in created:
        db.refresh(m)
    return created


def get_default_model(
    db: Session,
    provider_type: str,
    capability: str = "chat",
) -> AIModel | None:
    return (
        db.query(AIModel)
        .filter(
            AIModel.provider_type == provider_type,
            AIModel.capability == capability,
            AIModel.is_active.is_(True),
            AIModel.is_default.is_(True),
        )
        .order_by(AIModel.id.asc())
        .first()
    )


def resolve_chat_model(db: Session, provider_type: str, fallback: str) -> str:
    row = get_default_model(db, provider_type, "chat")
    return row.model_key if row else fallback


def list_ai_models(
    db: Session,
    provider_type: str | None = None,
    capability: str | None = None,
) -> list[dict]:
    q = db.query(AIModel).filter(AIModel.is_active.is_(True))
    if provider_type:
        q = q.filter(AIModel.provider_type == provider_type)
    if capability:
        q = q.filter(AIModel.capability == capability)
    rows = q.order_by(AIModel.provider_type.asc(), AIModel.capability.asc(), AIModel.id.asc()).all()
    return [
        {
            "id": m.id,
            "provider_type": m.provider_type,
            "model_key": m.model_key,
            "display_name": m.display_name,
            "capability": m.capability,
            "is_default": m.is_default,
            "is_active": m.is_active,
        }
        for m in rows
    ]
