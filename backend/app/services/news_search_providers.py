"""Capa unificada de búsqueda de noticias con failover.

Orden: Tavily → SerpAPI (Google News) → Bing News → Google News RSS → DuckDuckGo.
Las APIs de pago solo se usan si hay clave en Settings; GNews RSS y DDG no requieren key.
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus

import feedparser
import httpx
from ddgs import DDGS

from app.config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "Autoridad360Bot/1.0 (+news-search)"


def _norm_hit(
    *,
    url: str,
    title: str,
    body: str = "",
    source: str = "",
    date: Any = None,
    provider: str,
) -> dict[str, Any] | None:
    url = (url or "").strip()
    title = (title or "").strip()
    if not url or not title:
        return None
    return {
        "url": url[:2048],
        "title": title[:512],
        "body": (body or "")[:800],
        "source": (source or provider)[:128],
        "date": date,
        "provider": provider,
    }


def _dedupe(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for h in hits:
        key = (h.get("url") or "").split("?")[0].lower()
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out


def search_tavily(query: str, *, max_results: int = 5, days: int = 1) -> list[dict[str, Any]]:
    key = (settings.tavily_api_key or "").strip()
    if not key:
        return []
    try:
        with httpx.Client(timeout=20.0) as client:
            res = client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": key,
                    "query": query,
                    "topic": "news",
                    "search_depth": "basic",
                    "max_results": max_results,
                    "days": max(1, days),
                    "include_answer": False,
                },
            )
            res.raise_for_status()
            data = res.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tavily search failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for row in data.get("results") or []:
        hit = _norm_hit(
            url=row.get("url") or "",
            title=row.get("title") or "",
            body=row.get("content") or "",
            source="Tavily",
            date=row.get("published_date"),
            provider="tavily",
        )
        if hit:
            out.append(hit)
    return out


def search_serpapi_news(query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
    key = (settings.serpapi_api_key or "").strip()
    if not key:
        return []
    try:
        with httpx.Client(timeout=20.0) as client:
            res = client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_news",
                    "q": query,
                    "api_key": key,
                    "hl": "es",
                    "gl": "mx",
                },
            )
            res.raise_for_status()
            data = res.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("SerpAPI news failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for row in (data.get("news_results") or [])[:max_results]:
        link = row.get("link") or row.get("url") or ""
        hit = _norm_hit(
            url=link,
            title=row.get("title") or "",
            body=row.get("snippet") or "",
            source=(row.get("source") or {}).get("name")
            if isinstance(row.get("source"), dict)
            else (row.get("source") or "Google News"),
            date=row.get("date") or row.get("published_at"),
            provider="serpapi",
        )
        if hit:
            out.append(hit)
    return out


def search_bing_news(query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
    key = (settings.bing_search_api_key or "").strip()
    if not key:
        return []
    endpoint = (settings.bing_search_endpoint or "").strip().rstrip("/")
    if not endpoint:
        endpoint = "https://api.bing.microsoft.com/v7.0/news/search"
    try:
        with httpx.Client(timeout=20.0) as client:
            res = client.get(
                endpoint,
                params={
                    "q": query,
                    "count": max_results,
                    "mkt": "es-MX",
                    "freshness": "Day",
                    "textDecorations": False,
                    "textFormat": "Raw",
                },
                headers={
                    "Ocp-Apim-Subscription-Key": key,
                    "User-Agent": USER_AGENT,
                },
            )
            res.raise_for_status()
            data = res.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Bing news failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for row in data.get("value") or []:
        hit = _norm_hit(
            url=row.get("url") or "",
            title=row.get("name") or "",
            body=row.get("description") or "",
            source=(row.get("provider") or [{}])[0].get("name")
            if isinstance(row.get("provider"), list) and row.get("provider")
            else "Bing News",
            date=row.get("datePublished"),
            provider="bing",
        )
        if hit:
            out.append(hit)
    return out


def search_google_news_rss(query: str, *, max_results: int = 8) -> list[dict[str, Any]]:
    """Google News RSS — sin API key; buena cobertura LatAm con hl/gl MX."""
    url = (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}&hl=es-419&gl=MX&ceid=MX:es-419"
    )
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            res = client.get(url, headers={"User-Agent": USER_AGENT})
            res.raise_for_status()
            feed = feedparser.parse(res.text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Google News RSS failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for entry in (feed.entries or [])[:max_results]:
        link = (entry.get("link") or "").strip()
        title = (entry.get("title") or "").strip()
        source = ""
        if getattr(entry, "source", None):
            source = getattr(entry.source, "title", "") or ""
        published = entry.get("published") or entry.get("updated")
        hit = _norm_hit(
            url=link,
            title=title,
            body=(entry.get("summary") or "")[:400],
            source=source or "Google News",
            date=published,
            provider="gnews_rss",
        )
        if hit:
            out.append(hit)
    return out


def search_ddg_news(
    query: str,
    *,
    max_results: int = 5,
    timelimit: str = "d",
) -> list[dict[str, Any]]:
    try:
        with DDGS() as ddgs:
            try:
                rows = list(ddgs.news(query, max_results=max_results, timelimit=timelimit))
            except TypeError:
                rows = list(ddgs.news(query, max_results=max_results))
            except Exception as exc:  # noqa: BLE001
                logger.warning("DDG news failed (%s): %s — text fallback", timelimit, exc)
                try:
                    rows = list(ddgs.text(query, max_results=max_results, timelimit=timelimit))
                except Exception as exc2:  # noqa: BLE001
                    logger.warning("DDG text failed: %s", exc2)
                    return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("DDGS init/search failed: %s", exc)
        return []
    out: list[dict[str, Any]] = []
    for r in rows or []:
        hit = _norm_hit(
            url=r.get("url") or r.get("href") or "",
            title=r.get("title") or "",
            body=r.get("body") or r.get("excerpt") or "",
            source=r.get("source") or "DuckDuckGo",
            date=r.get("date"),
            provider="ddg",
        )
        if hit:
            out.append(hit)
    return out


def configured_providers() -> list[str]:
    names: list[str] = []
    if (settings.tavily_api_key or "").strip():
        names.append("tavily")
    if (settings.serpapi_api_key or "").strip():
        names.append("serpapi")
    if (settings.bing_search_api_key or "").strip():
        names.append("bing")
    names.extend(["gnews_rss", "ddg"])
    return names


def search_news(
    query: str,
    *,
    max_results: int = 6,
    timelimit: str = "d",
    prefer_fresh_days: int = 1,
) -> list[dict[str, Any]]:
    """Busca en cascada hasta reunir max_results (dedupe por URL)."""
    q = (query or "").strip()
    if not q:
        return []
    collected: list[dict[str, Any]] = []
    days = 7 if timelimit == "w" else max(1, prefer_fresh_days)

    steps: list[tuple[str, Any]] = [
        ("tavily", lambda: search_tavily(q, max_results=max_results, days=days)),
        ("serpapi", lambda: search_serpapi_news(q, max_results=max_results)),
        ("bing", lambda: search_bing_news(q, max_results=max_results)),
        ("gnews_rss", lambda: search_google_news_rss(q, max_results=max_results + 2)),
        ("ddg", lambda: search_ddg_news(q, max_results=max_results, timelimit=timelimit)),
    ]

    for name, fn in steps:
        if len(collected) >= max_results:
            break
        # Saltar APIs sin key (devuelven [] rápido)
        if name == "tavily" and not (settings.tavily_api_key or "").strip():
            continue
        if name == "serpapi" and not (settings.serpapi_api_key or "").strip():
            continue
        if name == "bing" and not (settings.bing_search_api_key or "").strip():
            continue
        try:
            batch = fn() or []
        except Exception as exc:  # noqa: BLE001
            logger.warning("Provider %s error: %s", name, exc)
            continue
        if batch:
            logger.info("news_search[%s]: %s hits for %r", name, len(batch), q[:60])
        collected.extend(batch)
        collected = _dedupe(collected)

    return collected[: max(1, max_results * 2)]
