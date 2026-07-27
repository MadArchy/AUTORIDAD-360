"""Frescura editorial: fechas reales de publicación, no de importación."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any

# Ventana operativa: noticias del día + margen de husos/cron.
DEFAULT_MAX_AGE_HOURS = 36
# RSS a veces trae backlog; no aceptar más de 72 h.
RSS_MAX_AGE_HOURS = 72
# UI / Top10: no mostrar piezas con publicación más vieja que esto.
DISPLAY_MAX_AGE_HOURS = 72

_MONTHS = {
    "jan": 1,
    "january": 1,
    "ene": 1,
    "enero": 1,
    "feb": 2,
    "february": 2,
    "febrero": 2,
    "mar": 3,
    "march": 3,
    "marzo": 3,
    "apr": 4,
    "april": 4,
    "abr": 4,
    "abril": 4,
    "may": 5,
    "mayo": 5,
    "jun": 6,
    "june": 6,
    "junio": 6,
    "jul": 7,
    "july": 7,
    "julio": 7,
    "aug": 8,
    "august": 8,
    "ago": 8,
    "agosto": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "septiembre": 9,
    "oct": 10,
    "october": 10,
    "octubre": 10,
    "nov": 11,
    "november": 11,
    "noviembre": 11,
    "dec": 12,
    "december": 12,
    "dic": 12,
    "diciembre": 12,
}


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_result_date(value: Any) -> datetime | None:
    """Normaliza fechas de motores / meta a UTC naive."""
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        try:
            dt = datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        text = str(value).strip()
        if not text:
            return None
        dt = None
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(text)
            except (TypeError, ValueError, IndexError):
                m = re.search(
                    r"(\d+)\s*(minute|minutes|min|hour|hours|hr|hrs|day|days|"
                    r"minuto|minutos|hora|horas|día|dias|días)\b",
                    text,
                    re.I,
                )
                if m:
                    n = int(m.group(1))
                    unit = m.group(2).lower()
                    now = datetime.now(timezone.utc)
                    if unit.startswith(("min", "minuto")):
                        dt = now - timedelta(minutes=n)
                    elif unit.startswith(("hour", "hr", "hora")):
                        dt = now - timedelta(hours=n)
                    else:
                        dt = now - timedelta(days=n)
                else:
                    dt = extract_explicit_publish_date(text)
        if dt is None:
            return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def extract_explicit_publish_date(text: str) -> datetime | None:
    """Busca fechas explícitas en HTML/texto (p. ej. 'Fecha de publicación: 6 nov 2023')."""
    if not text:
        return None
    sample = text[:12000]
    labeled = re.search(
        r"(?:fecha\s+de\s+publicaci[oó]n|published(?:\s+on)?|publication\s+date|"
        r"date\s+published|publicado(?:\s+el)?)\s*[:\-]?\s*"
        r"(\d{1,2})\s+(?:de\s+)?([A-Za-zÁÉÍÓÚáéíóúüñ\.]+)\s+(?:de\s+)?(\d{4})"
        r"|"
        r"(?:fecha\s+de\s+publicaci[oó]n|published(?:\s+on)?|publication\s+date|"
        r"date\s+published|publicado(?:\s+el)?)\s*[:\-]?\s*"
        r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})",
        sample,
        re.I,
    )
    if labeled:
        if labeled.group(1):
            return _ymd_from_parts(labeled.group(3), labeled.group(2), labeled.group(1))
        return _ymd_from_parts(labeled.group(4), labeled.group(5), labeled.group(6))

    # ISO / SQL date cerca del inicio
    iso = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})(?:[T\s]\d{2}:\d{2})?", sample[:2500])
    if iso:
        return _ymd_from_parts(iso.group(1), iso.group(2), iso.group(3))

    # "6 nov 2023" / "6 de noviembre de 2023"
    human = re.search(
        r"\b(\d{1,2})\s+(?:de\s+)?([A-Za-zÁÉÍÓÚáéíóúüñ\.]+)\s+(?:de\s+)?(20\d{2})\b",
        sample[:4000],
        re.I,
    )
    if human:
        return _ymd_from_parts(human.group(3), human.group(2), human.group(1))

    return None


def _ymd_from_parts(year: Any, month: Any, day: Any) -> datetime | None:
    try:
        y = int(str(year).strip())
        d = int(str(day).strip())
        m_raw = str(month).strip().lower().rstrip(".")
        if m_raw.isdigit():
            m = int(m_raw)
        else:
            m = _MONTHS.get(m_raw)
            if m is None:
                return None
        if not (1 <= m <= 12 and 1 <= d <= 31 and 2000 <= y <= 2100):
            return None
        return datetime(y, m, d)
    except (TypeError, ValueError):
        return None


def resolve_publish_date(
    *,
    engine_date: Any = None,
    extracted_date: Any = None,
    html_or_text: str | None = None,
) -> datetime | None:
    """La fecha de la página manda sobre la del motor de búsqueda."""
    page = parse_result_date(extracted_date) if not isinstance(extracted_date, datetime) else extracted_date
    if page is None and html_or_text:
        page = extract_explicit_publish_date(html_or_text)
    engine = parse_result_date(engine_date)
    if page is not None:
        return page
    return engine


def is_stale(published_at: datetime | None, *, max_age_hours: int = DEFAULT_MAX_AGE_HOURS, now: datetime | None = None) -> bool:
    if published_at is None:
        return True
    now = now or utc_now_naive()
    cutoff = now - timedelta(hours=max(1, int(max_age_hours)))
    pub = published_at.replace(tzinfo=None) if published_at.tzinfo else published_at
    return pub < cutoff


def effective_publish_at(article) -> datetime | None:
    """Fecha editorial: published_at real; sin inventar frescura con created_at si hay pub vieja."""
    pub = getattr(article, "published_at", None)
    if pub is not None:
        return pub.replace(tzinfo=None) if getattr(pub, "tzinfo", None) else pub
    created = getattr(article, "created_at", None)
    if created is not None:
        return created.replace(tzinfo=None) if getattr(created, "tzinfo", None) else created
    return None
