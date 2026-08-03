from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ProfessionalProfile(Base):
    __tablename__ = "professional_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    services_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    audiences_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    markets_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Tipologías de búsqueda editables (PDF Juan Vásquez / temas custom)
    search_themes_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Notas del agente de tendencias sociales + publicidad orgánica
    ad_trend_notes_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Persona/voz canónica (Juan J. Vásquez y futuros perfiles)
    persona_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    pillars: Mapped[list["ContentPillar"]] = relationship(back_populates="profile")
    editorial_percentages: Mapped[list["EditorialPercentage"]] = relationship(
        back_populates="profile"
    )
    market_percentages: Mapped[list["MarketPercentage"]] = relationship(
        back_populates="profile"
    )


class ContentPillar(Base):
    __tablename__ = "content_pillars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=False
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped["ProfessionalProfile"] = relationship(back_populates="pillars")
    editorial_percentages: Mapped[list["EditorialPercentage"]] = relationship(
        back_populates="pillar"
    )


class EditorialPercentage(Base):
    __tablename__ = "editorial_percentages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=False
    )
    pillar_id: Mapped[int] = mapped_column(
        ForeignKey("content_pillars.id"), nullable=False
    )
    target_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    period: Mapped[str] = mapped_column(String(16), default="monthly")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    profile: Mapped["ProfessionalProfile"] = relationship(
        back_populates="editorial_percentages"
    )
    pillar: Mapped["ContentPillar"] = relationship(back_populates="editorial_percentages")


class MarketPercentage(Base):
    __tablename__ = "market_percentages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=False
    )
    market_code: Mapped[str] = mapped_column(String(8), nullable=False)
    target_pct: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    period: Mapped[str] = mapped_column(String(16), default="monthly")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    profile: Mapped["ProfessionalProfile"] = relationship(
        back_populates="market_percentages"
    )
