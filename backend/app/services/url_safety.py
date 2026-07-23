"""Validación de URLs de proveedores para reducir riesgo SSRF."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# Dominios permitidos para proveedores comerciales (host exacto o subdominio).
ALLOWED_PROVIDER_HOST_SUFFIXES = (
    "openai.com",
    "api.openai.com",
    "anthropic.com",
    "api.anthropic.com",
    "googleapis.com",
    "generativelanguage.googleapis.com",
    "openrouter.ai",
    "api.openrouter.ai",
)

# Hosts locales explícitos solo para Ollama / desarrollo.
LOCAL_PROVIDER_HOSTS = {
    "127.0.0.1",
    "localhost",
    "::1",
    "host.docker.internal",
}


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return bool(
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _host_allowed_for_paid(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    for suffix in ALLOWED_PROVIDER_HOST_SUFFIXES:
        if host == suffix or host.endswith("." + suffix):
            return True
    return False


def validate_provider_base_url(
    base_url: str | None,
    *,
    is_local: bool,
) -> str | None:
    """Valida base_url. Devuelve URL normalizada o None si no aplica.

    Raises:
        ValueError: URL inválida o potencialmente SSRF.
    """
    if not base_url or not str(base_url).strip():
        if is_local:
            return None
        raise ValueError("Paid providers require an explicit https base_url")

    raw = str(base_url).strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("base_url must use http or https")
    if not parsed.hostname:
        raise ValueError("base_url must include a hostname")
    if parsed.username or parsed.password:
        raise ValueError("base_url must not include credentials")
    if parsed.scheme == "http" and not is_local:
        raise ValueError("Paid provider base_url must use https")

    host = parsed.hostname.lower()
    if is_local:
        if host not in LOCAL_PROVIDER_HOSTS and not _host_allowed_for_paid(host):
            # Permitir hostname de LAN solo si resuelve a loopback/privada
            # explícitamente marcada como local provider — bloquear metadata clouds.
            try:
                infos = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
            except socket.gaierror as exc:
                raise ValueError(f"Cannot resolve base_url host: {host}") from exc
            for info in infos:
                ip = info[4][0]
                if ip.startswith("169.254.169.254") or ip == "metadata":
                    raise ValueError("base_url resolves to blocked metadata address")
                if not _is_private_ip(ip) and host not in LOCAL_PROVIDER_HOSTS:
                    raise ValueError(
                        "Local provider base_url must resolve to a private/loopback address"
                    )
        return raw.rstrip("/")

    if not _host_allowed_for_paid(host):
        raise ValueError(
            f"base_url host '{host}' is not in the allowlist of AI provider domains"
        )

    try:
        infos = socket.getaddrinfo(host, parsed.port or 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f"Cannot resolve base_url host: {host}") from exc
    for info in infos:
        ip = info[4][0]
        if _is_private_ip(ip) or ip.startswith("169.254."):
            raise ValueError("base_url must not resolve to a private or link-local address")

    return raw.rstrip("/")
