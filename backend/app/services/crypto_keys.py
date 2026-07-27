"""Cifrado de API keys — Fernet. Nunca se persisten en texto plano."""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

# Claves históricas de desarrollo: si la key se guardó antes de rotar
# API_KEY_ENCRYPTION_KEY / ENCRYPTION_KEY, aún podemos recuperar y re-cifrar.
_LEGACY_DEV_KEYS = (
    "cambia-encryption-key-en-produccion-min-32",
    "autoridad360-dev-only-change-me",
    "dev-api-encrypt-rotate-before-prod-32",
)


def _fernet_from(raw: str) -> Fernet:
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _candidate_raw_keys() -> list[str]:
    primary = (settings.effective_encryption_key or settings.encryption_key or "").strip()
    if not primary:
        primary = "autoridad360-dev-only-change-me"
    seen: set[str] = set()
    out: list[str] = []
    for raw in (primary, settings.api_key_encryption_key, settings.encryption_key, *_LEGACY_DEV_KEYS):
        value = (raw or "").strip()
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _fernet() -> Fernet:
    return _fernet_from(_candidate_raw_keys()[0])


def encrypt_secret(plain: str) -> str:
    if not plain:
        raise ValueError("Empty secret")
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    plain, _rotated = decrypt_secret_with_rotation(token)
    return plain


def decrypt_secret_with_rotation(token: str) -> tuple[str, bool]:
    """
    Descifra con la clave actual; si falla, prueba claves legacy de desarrollo.

    Returns:
        (plaintext, needs_reencrypt) — needs_reencrypt=True si se usó una clave legacy.
    """
    if not token:
        raise ValueError("Empty encrypted token")

    candidates = _candidate_raw_keys()
    primary = candidates[0]
    try:
        return _fernet_from(primary).decrypt(token.encode("utf-8")).decode("utf-8"), False
    except InvalidToken:
        pass

    for raw in candidates[1:]:
        try:
            plain = _fernet_from(raw).decrypt(token.encode("utf-8")).decode("utf-8")
            logger.warning(
                "API key decrypted with legacy ENCRYPTION_KEY; re-encrypt on next successful use"
            )
            return plain, True
        except InvalidToken:
            continue

    raise ValueError(
        "Cannot decrypt API key — check ENCRYPTION_KEY. "
        "Vuelve a pegar la API key en Inteligencia Artificial para re-cifrarla."
    )


def can_decrypt_secret(token: str | None) -> bool:
    if not token:
        return False
    try:
        decrypt_secret(token)
        return True
    except ValueError:
        return False


def key_hint(plain: str) -> str:
    plain = plain.strip()
    if len(plain) <= 4:
        return "••••"
    return f"••••{plain[-4:]}"
