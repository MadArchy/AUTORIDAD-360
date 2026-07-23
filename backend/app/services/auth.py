"""Servicio de autenticación, hashing y generación de JWT."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.models.auth_sessions import AuthSession

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
REFRESH_COOKIE_NAME = "a360_refresh"


def _jwt_secret() -> str:
    secret = settings.effective_jwt_secret
    if not secret and settings.is_production:
        raise RuntimeError("JWT_SECRET_KEY is required in production")
    return secret or "autoridad360-dev-only-change-me"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_minutes)
    to_encode.update(
        {
            "exp": expire,
            "type": "access",
            "jti": str(uuid4()),
        }
    )
    return jwt.encode(to_encode, _jwt_secret(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, _jwt_secret(), algorithms=[ALGORITHM])
        if payload.get("type") not in {None, "access"}:
            return {}
        return payload
    except JWTError:
        return {}


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_refresh_session(
    db: Session,
    *,
    user_id: int,
    user_agent: str | None = None,
) -> tuple[str, AuthSession]:
    raw = secrets.token_urlsafe(48)
    jti = str(uuid4())
    expires = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_days)
    row = AuthSession(
        user_id=user_id,
        jti=jti,
        token_hash=_hash_token(raw),
        expires_at=expires,
        user_agent=(user_agent or "")[:512] or None,
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return raw, row


def rotate_refresh_session(
    db: Session,
    *,
    raw_token: str,
    user_agent: str | None = None,
) -> tuple[str, AuthSession, int]:
    token_hash = _hash_token(raw_token)
    row = (
        db.query(AuthSession)
        .filter(
            AuthSession.token_hash == token_hash,
            AuthSession.is_active.is_(True),
            AuthSession.revoked_at.is_(None),
        )
        .first()
    )
    if not row or row.expires_at < datetime.utcnow():
        raise ValueError("Refresh token inválido o expirado")
    row.revoked_at = datetime.utcnow()
    row.is_active = False
    db.flush()
    new_raw, new_row = create_refresh_session(
        db, user_id=row.user_id, user_agent=user_agent
    )
    return new_raw, new_row, row.user_id


def revoke_refresh_session(db: Session, *, raw_token: str | None) -> None:
    if not raw_token:
        return
    token_hash = _hash_token(raw_token)
    row = (
        db.query(AuthSession)
        .filter(AuthSession.token_hash == token_hash, AuthSession.is_active.is_(True))
        .first()
    )
    if not row:
        return
    row.revoked_at = datetime.utcnow()
    row.is_active = False
    db.commit()


def revoke_all_user_sessions(db: Session, *, user_id: int) -> int:
    rows = (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user_id, AuthSession.is_active.is_(True))
        .all()
    )
    now = datetime.utcnow()
    for row in rows:
        row.revoked_at = now
        row.is_active = False
    db.commit()
    return len(rows)
