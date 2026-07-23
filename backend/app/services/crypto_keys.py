"""Cifrado de API keys — Fernet. Nunca se persisten en texto plano."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings


def _fernet() -> Fernet:
    raw = (settings.effective_encryption_key or settings.encryption_key or "").strip()
    if not raw:
        # Fallback determinístico SOLO para desarrollo local
        raw = "autoridad360-dev-only-change-me"
    # Derivar clave Fernet de 32 bytes urlsafe
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plain: str) -> str:
    if not plain:
        raise ValueError("Empty secret")
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Cannot decrypt API key — check ENCRYPTION_KEY") from exc


def key_hint(plain: str) -> str:
    plain = plain.strip()
    if len(plain) <= 4:
        return "••••"
    return f"••••{plain[-4:]}"
