"""Fase 6 — multiempresa / multicliente."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

ROLES = (
    "superadmin",
    "agency_admin",
    "strategist",
    "writer",
    "professional",  # cliente
    "editor",
    "legal_reviewer",
    "community_manager",
    "analyst",
)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    org_type: Mapped[str] = mapped_column(String(32), default="agency")
    # agency | client_workspace
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    plan_code: Mapped[str | None] = mapped_column(String(32), default="pilot")
    plan_limits_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    branding_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["OrgMembership"]] = relationship(back_populates="organization")


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(256), nullable=True)
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["OrgMembership"]] = relationship(back_populates="user")


class OrgMembership(Base):
    __tablename__ = "org_memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("professional_profiles.id"), nullable=True
    )
    # Si role=professional, puede ligarse a un perfil cliente
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="memberships")
    user: Mapped["AppUser"] = relationship(back_populates="memberships")
