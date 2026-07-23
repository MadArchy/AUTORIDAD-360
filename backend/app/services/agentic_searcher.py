"""Búsqueda agentica alineada a Tipos_de_Noticias_IA_Juan_Vasquez.pdf."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from ddgs import DDGS
import trafilatura
from sqlalchemy.orm import Session

from app.models.editorial import ArticleStatus, NewsArticle, NewsCategory
from app.services.ai_gateway import AIGatewayService
from app.services.news_typologies import (
    NEWS_TYPOLOGIES,
    SEARCH_QUERIES,
    TYPOLOGY_EVAL_PROMPT,
    queries_for_priorities,
    typology_by_id,
)
from app.services.vector_engine import vector_engine

logger = logging.getLogger(__name__)

# Re-export para compatibilidad
__all__ = ["AgenticSearcherService", "SEARCH_QUERIES", "generate_article_hash"]


def generate_article_hash(url: str, title: str) -> str:
    normalized = f"{url.strip().lower()}|{title.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class AgenticSearcherService:
    def __init__(self, db: Session, organization_id: int | None = None):
        self.db = db
        self.organization_id = organization_id
        self.ai_gateway = AIGatewayService(db)
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

    def _category_for_typology(self, type_id: int | None) -> int:
        typo = typology_by_id(type_id)
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

    def _extract_text(self, url: str) -> str | None:
        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                return None
            return trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("Error extrayendo %s: %s", url, e)
            return None

    def _evaluate_with_ollama(self, text: str, title: str = "") -> dict[str, Any]:
        """Evalúa relevancia + tipología editorial (1–11)."""
        try:
            blob = f"TÍTULO: {title}\n\n{text}" if title else text
            prompt = TYPOLOGY_EVAL_PROMPT.format(text=blob[:7500])
            res = self.ai_gateway.generate_text(
                prompt=prompt,
                system_prompt="Curador estricto Juan Vásquez. Devuelve SOLO JSON.",
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

    def run_search_cycle(
        self,
        max_results_per_query: int = 2,
        extra_queries: list[str] | None = None,
        max_queries: int | None = None,
        max_priority: int = 11,
    ) -> dict[str, Any]:
        """Ciclo de búsqueda priorizando tipologías 1–11 del PDF."""
        # Prioridad: tipologías altas primero
        base = queries_for_priorities(max_priority=max_priority) or list(SEARCH_QUERIES)
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

        stats: dict[str, Any] = {
            "queries_run": len(queries),
            "urls_found": 0,
            "already_seen": 0,
            "extraction_failed": 0,
            "evaluated_by_ai": 0,
            "rejected_low_relevance": 0,
            "saved_to_db": 0,
            "by_news_type": {},
            "queries": queries,
            "typologies": [t["slug"] for t in NEWS_TYPOLOGIES if t["id"] <= max_priority],
        }

        with DDGS() as ddgs:
            for query in queries:
                logger.info("Buscando tipología (DDG): %s", query)
                try:
                    results = list(ddgs.text(query, max_results=max_results_per_query))
                    stats["urls_found"] += len(results)

                    for r in results:
                        url = r.get("href") or ""
                        title = r.get("title") or ""
                        if not url:
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

                        full_text = self._extract_text(url)
                        if not full_text or len(full_text) < 500:
                            stats["extraction_failed"] += 1
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
                        typo = typology_by_id(type_id) if type_id else None

                        logger.info(
                            "URL: %s | score=%s | type=%s | %s",
                            url,
                            relevance,
                            typo["slug"] if typo else None,
                            eval_data.get("reason"),
                        )

                        # Umbral más estricto: tipología + relevancia
                        if relevance < 60 or not typo:
                            stats["rejected_low_relevance"] += 1
                            continue

                        slug = typo["slug"]
                        stats["by_news_type"][slug] = stats["by_news_type"].get(slug, 0) + 1

                        article = NewsArticle(
                            organization_id=self.organization_id,
                            category_id=self._category_for_typology(typo["id"]),
                            title=title[:512],
                            source_url=url[:1024],
                            source_name=f"Web Search · {typo['name']}",
                            full_text=full_text,
                            excerpt=(eval_data.get("reason") or "")[:500],
                            content_hash=content_hash,
                            status=ArticleStatus.COLLECTED.value,
                            classification_json={
                                "scout": {
                                    "news_type_id": typo["id"],
                                    "news_type_slug": slug,
                                    "news_type_name": typo["name"],
                                    "relevance_score": relevance,
                                    "reason": eval_data.get("reason"),
                                    "editorial_fit": eval_data.get("editorial_fit"),
                                    "four_questions_ok": eval_data.get("four_questions_ok"),
                                    "query": query,
                                }
                            },
                            score_relevance=relevance,
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
