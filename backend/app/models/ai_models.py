"""Catálogo de modelos IA (Etapa 2) — evita hardcodear solo en código."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AIModel(Base):
    __tablename__ = "ai_models"
    __table_args__ = (
        UniqueConstraint(
            "provider_type", "model_key", "capability", name="uq_ai_models_provider_key_cap"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # ollama | openai | anthropic | gemini
    model_key: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    capability: Mapped[str] = mapped_column(String(32), nullable=False, default="chat")
    # chat | embed
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
