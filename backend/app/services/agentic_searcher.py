"""Búsqueda agentica alineada a Tipos_de_Noticias_IA_Juan_Vasquez.pdf.

Prioriza noticias del día (Tavily/SerpAPI/Bing → GNews RSS → DDG) y rechaza piezas antiguas.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import trafilatura
from sqlalchemy.orm import Session

from app.models.editorial import ArticleStatus, NewsArticle, NewsCategory
from app.services.ai_gateway import AIGatewayService
from app.services.news_freshness import (
    DEFAULT_MAX_AGE_HOURS,
    extract_explicit_publish_date,
    is_stale,
    parse_result_date,
    resolve_publish_date,
    utc_now_naive,
)
from app.services.news_search_providers import configured_providers, search_news
from app.services.news_typologies import (
    SEARCH_QUERIES,
    build_eval_prompt,
    queries_for_priorities,
    typologies_from_profile,
    typology_by_id,
)
from app.services.vector_engine import vector_engine

logger = logging.getLogger(__name__)

# Re-export para compatibilidad
__all__ = ["AgenticSearcherService", "SEARCH_QUERIES", "generate_article_hash"]

NEWS_TIMELIMIT_PRIMARY = "d"  # day
NEWS_TIMELIMIT_FALLBACK = "w"  # week si el día no trae suficientes candidatos

# Alias legacy usados por tests / imports externos
_parse_result_date = parse_result_date


def generate_article_hash(url: str, title: str) -> str:
    normalized = f"{url.strip().lower()}|{title.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _freshness_query(query: str, *, now: datetime | None = None) -> str:
    """Añade anclas de frescura sin duplicar el año si ya está en la query."""
    now = now or utc_now_naive()
    year = str(now.year)
    month = now.strftime("%B")
    q = query.strip()
    extras: list[str] = []
    if year not in q:
        extras.append(year)
    # Sesgo editorial: noticias / breaking, no evergreen
    low = q.lower()
    if "news" not in low and "noticia" not in low:
        extras.append("news")
    if month.lower() not in low:
        extras.append(month)
    if not extras:
        return q
    return f"{q} {' '.join(extras)}"


class AgenticSearcherService:
    def __init__(self, db: Session, organization_id: int | None = None):
        self.db = db
        self.organization_id = organization_id
        self.ai_gateway = AIGatewayService(db)
        self._typologies: list[dict[str, Any]] | None = None
        categories_query = self.db.query(NewsCategory)
        articles_query = self.db.query(NewsArticle)
        if organization_id is not None:
            categories_query = categories_query.filter(
                NewsCategory.organization_id == organization_id
            )
            articles_query = articles_query.filter(
                NewsArticle.organization_id == organization_id
            )
        category = categories_query.first()
        if not category:
            raise ValueError("No hay categorías para la organización; recolecta RSS primero")
        self.default_category_id = category.id
        # Mapa slug categoría → id (si existen categorías alineadas)
        self._category_by_slug = {
            c.slug: c.id
            for c in categories_query.all()
            if getattr(c, "slug", None)
        }
        existing = articles_query.with_entities(NewsArticle.content_hash).all()
        self.seen_hashes = {r[0] for r in existing if r[0]}

    def _load_typologies(self) -> list[dict[str, Any]]:
        if self._typologies is not None:
            return self._typologies
        profile = None
        try:
            from app.services.quota import get_active_profile

            profile = get_active_profile(self.db, organization_id=self.organization_id)
            if profile and not profile.search_themes_json:
                from app.services.news_typologies import default_search_themes

                profile.search_themes_json = default_search_themes()
                self.db.commit()
        except Exception as exc:  # noqa: BLE001
            logger.debug("No se pudo cargar perfil para tipologías: %s", exc)
        self._typologies = typologies_from_profile(profile)
        return self._typologies

    def _category_for_typology(self, type_id: int | None) -> int:
        typo = typology_by_id(type_id, self._load_typologies())
        if not typo:
            return self.default_category_id
        # Preferir categoría RSS cuyo slug/name encaje con la tipología
        slug = typo["slug"]
        if slug in self._category_by_slug:
            return self._category_by_slug[slug]
        # Fallbacks por afinidad
        aliases = {
            "politica-regulacion-ia": ["tecnologia-ia", "finanzas-regulacion", "compliance"],
            "casos-legales-ia": ["derecho-corporativo", "compliance", "legal-tech"],
            "patentes-pi-ia": ["propiedad-intelectual", "tecnologia-ia"],
            "privacidad-ciberseguridad-ia": ["compliance", "tecnologia-ia"],
            "ia-abogados-legal": ["legal-tech", "derecho-corporativo"],
            "mexico-estados-unidos-ia": ["comercio-mx-us", "mexico-negocios"],
            "inversiones-ia": ["tecnologia-ia", "finanzas-regulacion"],
            "empleo-transformacion-ia": ["tecnologia-ia"],
            "ia-mal-implementada": ["tecnologia-ia", "compliance"],
            "ia-exito-empresarial": ["tecnologia-ia"],
            "empresas-rezagadas-ia": ["tecnologia-ia"],
        }
        for candidate in aliases.get(slug, ["tecnologia-ia"]):
            if candidate in self._category_by_slug:
                return self._category_by_slug[candidate]
        return self.default_category_id

    def _extract_text(self, url: str) -> tuple[str | None, datetime | None]:
        """Extrae cuerpo y fecha de publicación si trafilatura / HTML la detectan."""
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None, None
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )
            published = None
            try:
                meta = trafilatura.extract(
                    downloaded,
                    output_format="json",
                    include_comments=False,
                    include_tables=False,
                    no_fallback=False,
                )
                if meta:
                    payload = json.loads(meta) if isinstance(meta, str) else meta
                    if isinstance(payload, dict):
                        published = parse_result_date(
                            payload.get("date") or payload.get("date_publish")
                        )
            except Exception:  # noqa: BLE001
                published = None
            if published is None:
                published = extract_explicit_publish_date(downloaded)
            if published is None and text:
                published = extract_explicit_publish_date(text)
            return text, published
        except Exception as e:  # noqa: BLE001
            logger.warning("Error extrayendo %s: %s", url, e)
            return None, None

    def _evaluate_with_ollama(self, text: str, title: str = "") -> dict[str, Any]:
        """Evalúa relevancia + tipología editorial según temas del perfil."""
        try:
            blob = f"TÍTULO: {title}\n\n{text}" if title else text
            prompt_tmpl = build_eval_prompt(self._load_typologies())
            prompt = prompt_tmpl.format(text=blob[:7500])
            res = self.ai_gateway.generate_text(
                prompt=prompt,
                system_prompt=(
                    "Curador estricto Juan Vásquez. Prioriza noticias de las últimas 24–48 h. "
                    "Devuelve SOLO JSON."
                ),
            )
            raw_text = res.get("text", "") or ""
            start = raw_text.find("{")
            end = raw_text.rfind("}") + 1
            if start == -1 or end <= 0:
                return {"relevance_score": 0, "reason": "Fallo en parseo JSON de IA", "editorial_fit": False}
            data = json.loads(raw_text[start:end])
            score = float(data.get("relevance_score") or 0)
            # Penalizar si no encaja en tipología o no responde las 4 preguntas
            if data.get("editorial_fit") is False:
                score = min(score, 45)
            if data.get("four_questions_ok") is False:
                score = min(score, 50)
            if not data.get("news_type_id"):
                score = min(score, 40)
            data["relevance_score"] = score
            return data
        except Exception as e:  # noqa: BLE001
            logger.error("Fallo en evaluación IA: %s", e)
            return {
                "relevance_score": 0,
                "reason": f"Error en LLM: {e}",
                "editorial_fit": False,
            }

    def _search_news(
        self,
        query: str,
        *,
        max_results: int,
        timelimit: str,
    ) -> list[dict[str, Any]]:
        """Busca noticias con failover multi-motor (APIs → GNews RSS → DDG)."""
        fresh_q = _freshness_query(query)
        rows = search_news(
            fresh_q,
            max_results=max_results,
            timelimit=timelimit,
            prefer_fresh_days=7 if timelimit == "w" else 1,
        )
        normalized: list[dict[str, Any]] = []
        for r in rows or []:
            url = (r.get("url") or "").strip()
            title = (r.get("title") or "").strip()
            if not url or not title:
                continue
            normalized.append(
                {
                    "url": url,
                    "title": title,
                    "body": r.get("body") or "",
                    "source": r.get("source") or "Web News",
                    "date": r.get("date"),
                    "provider": r.get("provider") or "unknown",
                }
            )
        return normalized

    def run_search_cycle(
        self,
        max_results_per_query: int = 4,
        extra_queries: list[str] | None = None,
        max_queries: int | None = None,
        max_priority: int = 11,
        max_age_hours: int = DEFAULT_MAX_AGE_HOURS,
    ) -> dict[str, Any]:
        """Ciclo de búsqueda priorizando tipologías del perfil (PDF + temas custom)."""
        typologies = self._load_typologies()
        # Prioridad: tipologías altas primero
        base = queries_for_priorities(max_priority=max_priority, typologies=typologies) or list(
            SEARCH_QUERIES
        )
        queries = list(extra_queries or []) + base

        seen_q: set[str] = set()
        ordered: list[str] = []
        for q in queries:
            key = q.strip().lower()
            if not key or key in seen_q:
                continue
            seen_q.add(key)
            ordered.append(q.strip())
        # Por defecto cubrir más tipologías (antes 12 dejaba fuera PI/empleo/MX-US)
        cap = max(1, int(max_queries)) if max_queries else 18
        queries = ordered[:cap]
        age_limit = max(6, int(max_age_hours or DEFAULT_MAX_AGE_HOURS))
        now = utc_now_naive()
        cutoff = now - timedelta(hours=age_limit)

        stats: dict[str, Any] = {
            "queries_run": len(queries),
            "urls_found": 0,
            "already_seen": 0,
            "extraction_failed": 0,
            "evaluated_by_ai": 0,
            "rejected_low_relevance": 0,
            "rejected_stale": 0,
            "saved_to_db": 0,
            "by_news_type": {},
            "queries": queries,
            "freshness": {
                "mode": "news",
                "timelimit": NEWS_TIMELIMIT_PRIMARY,
                "max_age_hours": age_limit,
                "cutoff_utc": cutoff.isoformat() + "Z",
                "providers": configured_providers(),
            },
            "typologies": [
                t["slug"] for t in typologies if int(t.get("id") or 99) <= max_priority
            ],
        }

        per_query = max(3, int(max_results_per_query or 4))

        for query in queries:
            logger.info(
                "Buscando noticias frescas (%s): %s",
                ",".join(configured_providers()),
                query,
            )
            try:
                results = self._search_news(
                    query,
                    max_results=per_query,
                    timelimit=NEWS_TIMELIMIT_PRIMARY,
                )
                # Si el día viene seco, ampliar a la semana (luego se filtra por edad).
                if len(results) < max(2, per_query // 2):
                    more = self._search_news(
                        query,
                        max_results=per_query,
                        timelimit=NEWS_TIMELIMIT_FALLBACK,
                    )
                    seen_urls = {r["url"] for r in results}
                    for row in more:
                        if row["url"] not in seen_urls:
                            results.append(row)
                            seen_urls.add(row["url"])

                stats["urls_found"] += len(results)

                for r in results:
                    url = r["url"]
                    title = r["title"]
                    engine_date = parse_result_date(r.get("date"))

                    # Descarte temprano si el motor ya trae fecha vieja
                    if engine_date and is_stale(engine_date, max_age_hours=age_limit, now=now):
                        stats["rejected_stale"] += 1
                        logger.info(
                            "Descartada por antigüedad motor (%s): %s",
                            engine_date.date(),
                            url,
                        )
                        continue

                    content_hash = generate_article_hash(url, title)
                    if content_hash in self.seen_hashes:
                        stats["already_seen"] += 1
                        continue
                    # También dedupe por URL exacta en BD
                    if (
                        self.db.query(NewsArticle.id)
                        .filter(NewsArticle.source_url == url[:1024])
                        .first()
                    ):
                        stats["already_seen"] += 1
                        self.seen_hashes.add(content_hash)
                        continue

                    full_text, extracted_published = self._extract_text(url)
                    # La fecha de la PÁGINA manda (evita aceptar 2023 con date "hoy" del motor)
                    published_at = resolve_publish_date(
                        engine_date=engine_date,
                        extracted_date=extracted_published,
                        html_or_text=f"{title}\n{r.get('body') or ''}\n{(full_text or '')[:2000]}",
                    )
                    if published_at and is_stale(published_at, max_age_hours=age_limit, now=now):
                        stats["rejected_stale"] += 1
                        logger.info(
                            "Descartada por fecha real de página (%s): %s",
                            published_at.date(),
                            url,
                        )
                        continue

                    if not full_text or len(full_text) < 400:
                        snippet = (r.get("body") or "").strip()
                        if (
                            published_at
                            and not is_stale(published_at, max_age_hours=age_limit, now=now)
                            and len(snippet) >= 80
                        ):
                            full_text = f"{title}\n\n{snippet}"
                        else:
                            stats["extraction_failed"] += 1
                            continue

                    # Sin fecha confiable → no inventar "hoy" (así entraban evergreen de 2023)
                    if not published_at:
                        stats["rejected_stale"] += 1
                        logger.info("Descartada sin fecha de publicación confiable: %s", url)
                        continue

                    if vector_engine.is_active:
                        if vector_engine.check_is_duplicate(
                            title + " " + full_text[:1000], threshold=0.15
                        ):
                            stats["already_seen"] += 1
                            continue

                    stats["evaluated_by_ai"] += 1
                    eval_data = self._evaluate_with_ollama(full_text, title=title)
                    relevance = float(eval_data.get("relevance_score") or 0)
                    type_id = eval_data.get("news_type_id")
                    typo = typology_by_id(type_id, typologies) if type_id else None

                    logger.info(
                        "URL: %s | score=%s | type=%s | published=%s | %s",
                        url,
                        relevance,
                        typo["slug"] if typo else None,
                        published_at.isoformat() if published_at else None,
                        eval_data.get("reason"),
                    )

                    # Umbral más estricto: tipología + relevancia
                    if relevance < 60 or not typo:
                        stats["rejected_low_relevance"] += 1
                        continue

                    slug = typo["slug"]
                    stats["by_news_type"][slug] = stats["by_news_type"].get(slug, 0) + 1
                    age_hours = max(0.0, (now - published_at).total_seconds() / 3600.0)
                    freshness_bonus = (
                        15.0 if age_hours <= 24 else (8.0 if age_hours <= age_limit else 0.0)
                    )

                    article = NewsArticle(
                        organization_id=self.organization_id,
                        category_id=self._category_for_typology(typo["id"]),
                        title=title[:512],
                        source_url=url[:1024],
                        source_name=(r.get("source") or f"Web News · {typo['name']}")[:128],
                        full_text=full_text,
                        excerpt=(eval_data.get("reason") or r.get("body") or "")[:500],
                        content_hash=content_hash,
                        status=ArticleStatus.COLLECTED.value,
                        published_at=published_at,
                        classification_json={
                            "scout": {
                                "news_type_id": typo["id"],
                                "news_type_slug": slug,
                                "news_type_name": typo["name"],
                                "pillar_slug": typo.get("pillar_slug"),
                                "relevance_score": relevance,
                                "reason": eval_data.get("reason"),
                                "editorial_fit": eval_data.get("editorial_fit"),
                                "four_questions_ok": eval_data.get("four_questions_ok"),
                                "query": query,
                                "search_mode": "news",
                                "provider": r.get("provider"),
                                "published_at": published_at.isoformat() + "Z",
                                "age_hours": round(age_hours, 2),
                            },
                            "pillar_slug": typo.get("pillar_slug"),
                        },
                        score_relevance=min(100.0, relevance + freshness_bonus),
                        score_freshness=100.0 if age_hours <= 24 else max(40.0, 100.0 - age_hours),
                    )
                    self.db.add(article)
                    self.seen_hashes.add(content_hash)
                    stats["saved_to_db"] += 1
                    self.db.commit()
                    self.db.refresh(article)

                    if vector_engine.is_active:
                        vector_engine.index_article(article.id, title, full_text[:2000])

            except Exception as e:  # noqa: BLE001
                logger.error("Error procesando query '%s': %s", query, e)

        return stats
