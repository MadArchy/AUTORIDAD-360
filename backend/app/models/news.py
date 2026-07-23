"""Compat shim — el stack canónico vive en editorial.py."""

from app.models.editorial import (  # noqa: F401
    ArticleStatus,
    AuditLog,
    BlogPost,
    BlogStatus,
    NewsArticle,
    NewsCategory,
    WeeklyReport,
)
from app.db.database import Base, SessionLocal, engine, get_db  # noqa: F401
