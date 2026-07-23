import hashlib
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import feedparser
import httpx
import trafilatura
from sqlalchemy.orm import Session

from app.config import settings
from app.models import NewsArticle, NewsCategory
from app.models.org import Organization
from app.rss.categories import RSS_CATEGORIES
from app.services.audit import log_audit
from app.services.editorial_filters import is_editorial_noise

logger = logging.getLogger(__name__)


def seed_categories(db: Session, organization_id: int | None = None) -> None:
    for cat in RSS_CATEGORIES:
        existing = (
            db.query(NewsCategory)
            .filter(
                NewsCategory.organization_id == organization_id,
                NewsCategory.slug == cat["slug"],
            )
            .first()
        )
        if not existing:
            db.add(
                NewsCategory(
                    organization_id=organization_id,
                    slug=cat["slug"],
                    name=cat["name"],
                    rss_url=cat["rss_url"],
                    is_active=True,
                )
            )
        else:
            # Mantener feeds alineados al piloto (sin duplicar filas)
            existing.name = cat["name"]
            existing.rss_url = cat["rss_url"]
            existing.is_active = True
    db.commit()


def _content_hash(title: str, url: str, text: str) -> str:
    payload = f"{title}|{url}|{text[:5000]}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_date(entry) -> datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, field, None)
        if parsed:
            try:
                return datetime(*parsed[:6])
            except (TypeError, ValueError):
                pass
    for field in ("published", "updated"):
        raw = entry.get(field)
        if raw:
            try:
                return parsedate_to_datetime(raw).replace(tzinfo=None)
            except (TypeError, ValueError, IndexError):
                pass
    return None


def _extract_text(
    url: str,
    fallback: str = "",
    client: httpx.Client | None = None,
) -> str:
    try:
        if client is None:
            with httpx.Client(
                timeout=settings.rss_request_timeout_seconds,
                follow_redirects=True,
            ) as owned_client:
                return _extract_text(url, fallback=fallback, client=owned_client)
        response = client.get(url, headers={"User-Agent": "Autoridad360Bot/1.0"})
        response.raise_for_status()
        extracted = trafilatura.extract(response.text, include_comments=False)
        if extracted and len(extracted.strip()) > 100:
            return extracted.strip()
    except Exception:
        pass
    return fallback.strip()


def _source_name(url: str, feed_title: str | None) -> str:
    if feed_title:
        return feed_title[:256]
    domain = urlparse(url).netloc.replace("www.", "")
    return domain[:256] if domain else "Unknown"


def collect_from_category(db: Session, category: NewsCategory, limit: int = 15) -> dict:
    started = time.perf_counter()
    feed = feedparser.parse(category.rss_url)
    inserted = 0
    skipped = 0
    errors = 0

    candidates = []
    for entry in feed.entries[:limit]:
        url = entry.get("link") or entry.get("id")
        if not url:
            errors += 1
            continue

        title = (entry.get("title") or "Sin título").strip()
        summary = entry.get("summary") or entry.get("description") or ""
        summary = re.sub(r"<[^>]+>", " ", summary)
        if is_editorial_noise(title, summary[:400]):
            skipped += 1
            continue
        candidates.append((entry, url, title, summary))

    candidate_urls = [row[1] for row in candidates]
    existing_urls = set()
    if candidate_urls:
        existing_urls = {
            row[0]
            for row in db.query(NewsArticle.source_url)
            .filter(
                NewsArticle.organization_id == category.organization_id,
                NewsArticle.source_url.in_(candidate_urls),
            )
            .all()
        }
    pending = [row for row in candidates if row[1] not in existing_urls]
    skipped += len(candidates) - len(pending)

    workers = max(1, min(settings.rss_extract_concurrency, len(pending) or 1))
    with httpx.Client(
        timeout=settings.rss_request_timeout_seconds,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=workers, max_keepalive_connections=workers),
    ) as client:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="a360-rss") as pool:
            full_texts = list(
                pool.map(
                    lambda row: _extract_text(row[1], fallback=row[3], client=client),
                    pending,
                )
            )

    prepared = []
    for (entry, url, title, _summary), full_text in zip(pending, full_texts):
        if len(full_text) < 80:
            errors += 1
            continue
        digest = _content_hash(title, url, full_text)
        prepared.append((entry, url, title, full_text, digest))

    digests = [row[4] for row in prepared]
    existing_hashes = set()
    if digests:
        existing_hashes = {
            row[0]
            for row in db.query(NewsArticle.content_hash)
            .filter(
                NewsArticle.organization_id == category.organization_id,
                NewsArticle.content_hash.in_(digests),
            )
            .all()
        }

    seen_hashes: set[str] = set()
    seen_urls: set[str] = set()
    for entry, url, title, full_text, digest in prepared:
        if digest in existing_hashes or digest in seen_hashes or url in seen_urls:
            skipped += 1
            continue
        seen_hashes.add(digest)
        seen_urls.add(url)

        article = NewsArticle(
            organization_id=category.organization_id,
            category_id=category.id,
            title=title[:512],
            source_url=url[:1024],
            source_name=_source_name(url, feed.feed.get("title")),
            published_at=_parse_date(entry),
            full_text=full_text,
            excerpt=full_text[:500],
            content_hash=digest,
            status="collected",
        )
        db.add(article)
        db.flush()
        log_audit(
            db,
            entity_type="news_article",
            entity_id=article.id,
            action="collected",
            source_url=url,
            output_summary=f"Collected: {title[:120]}",
        )
        inserted += 1

    db.commit()
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        "rss_category_complete category=%s inserted=%s skipped=%s errors=%s duration_ms=%s",
        category.slug,
        inserted,
        skipped,
        errors,
        elapsed_ms,
    )
    return {
        "category": category.slug,
        "inserted": inserted,
        "skipped": skipped,
        "errors": errors,
        "duration_ms": elapsed_ms,
    }


def collect_all_feeds(
    db: Session,
    per_category_limit: int = 15,
    organization_id: int | None = None,
) -> dict:
    started = time.perf_counter()
    results = []
    totals = {"inserted": 0, "skipped": 0, "errors": 0}

    org_ids = [organization_id] if organization_id is not None else [
        row[0]
        for row in db.query(Organization.id)
        .filter(Organization.is_active.is_(True))
        .all()
    ]
    # Compatibilidad con instalaciones legacy sin organizaciones sembradas.
    if not org_ids:
        org_ids = [None]
    for org_id in org_ids:
        seed_categories(db, organization_id=org_id)

    categories = (
        db.query(NewsCategory)
        .filter(
            NewsCategory.is_active.is_(True),
            NewsCategory.organization_id.in_(org_ids)
            if org_ids != [None]
            else NewsCategory.organization_id.is_(None),
        )
        .all()
    )
    for category in categories:
        result = collect_from_category(db, category, limit=per_category_limit)
        results.append(result)
        totals["inserted"] += result["inserted"]
        totals["skipped"] += result["skipped"]
        totals["errors"] += result["errors"]

    duration_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        "rss_collection_complete inserted=%s skipped=%s errors=%s duration_ms=%s",
        totals["inserted"],
        totals["skipped"],
        totals["errors"],
        duration_ms,
    )
    return {"totals": totals, "categories": results, "duration_ms": duration_ms}
