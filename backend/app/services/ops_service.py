import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.models.news import NewsArticle
from app.models.ops import CalendarSlot, EditorialTask, DecisionLog

logger = logging.getLogger(__name__)

# Sensitive keywords triggering Risk Traffic Light (Semáforo de Riesgo)
SENSITIVE_RED_KEYWORDS = ["lawsuit", "demandas", "litigio", "investigación criminal", "fraude", "scam", "monopolio", "antitrust"]
SENSITIVE_YELLOW_KEYWORDS = ["sec", "fda", "regulacion", "patente", "privacidad", "multa", "meta", "google", "openai", "microsoft"]

def evaluate_risk_level(article: NewsArticle) -> (str, str):
    """
    Evaluates risk level (Verde / Amarillo / Rojo) for a news article:
    - RED: Active lawsuits, criminal fraud, antitrust, unverified claims
    - YELLOW: Regulatory bodies (SEC, FDA), patent disputes, big tech brands
    - GREEN: Standard verified tech trend or educational content
    """
    if article.verification_status != "verified":
        return "red", "Rojo: Artículo sin verificación factual completa. Requiere auditoría estricta."

    text = f"{article.title} {article.content_full or ''}".lower()

    for kw in SENSITIVE_RED_KEYWORDS:
        if kw in text:
            return "red", f"Rojo: Contiene temas sensibles de alto riesgo legal o disputas activas ('{kw}'). Requiere aprobación explícita de Juan Vásquez."

    for kw in SENSITIVE_YELLOW_KEYWORDS:
        if kw in text:
            return "yellow", f"Amarillo: Mención a organismos reguladores o marcas registradas ('{kw}'). Requiere revisión preventiva antes de publicar."

    return "green", "Verde: Bajo riesgo legal y reputacional. Noticia factual verificada lista para flujo estándar."

class EditorialOpsService:
    def __init__(self, db: Session):
        self.db = db

    def generate_default_cadence_slots(self) -> List[CalendarSlot]:
        """Generates regular 2-week editorial calendar for Juan Vásquez based on his cadence."""
        existing_count = self.db.query(CalendarSlot).count()
        if existing_count > 0:
            return self.db.query(CalendarSlot).order_by(CalendarSlot.scheduled_date.asc()).all()

        # Fetch top verified articles to populate initial slots
        verified_articles = self.db.query(NewsArticle).order_by(
            NewsArticle.top10_score.desc(), NewsArticle.published_at.desc()
        ).limit(10).all()

        created_slots = []
        now = datetime.utcnow()

        # Standard Weekly Cadence: 3 LinkedIn (Mon, Wed, Fri), 1 Newsletter (Thu), 1 Video (Tue)
        cadence_schedule = [
            {"day_offset": 1, "format": "linkedin", "title": "Post LinkedIn — Tendencia IA & Transformación", "channel": "LinkedIn"},
            {"day_offset": 2, "format": "video", "title": "Guion Video — Análisis Regulador & Derecho Tech", "channel": "YouTube Shorts / Reels"},
            {"day_offset": 3, "format": "linkedin", "title": "Post LinkedIn — Gobernanza de Datos & Ciberseguridad", "channel": "LinkedIn"},
            {"day_offset": 4, "format": "newsletter", "title": "Edición Newsletter Semanal — Juan Vásquez", "channel": "Substack / Email"},
            {"day_offset": 5, "format": "carousel", "title": "Carrusel LinkedIn — 5 Lecciones para Directivos", "channel": "LinkedIn"}
        ]

        for idx, item in enumerate(cadence_schedule):
            article = verified_articles[idx % len(verified_articles)] if verified_articles else None
            title = article.title if article else item["title"]
            risk_lvl, risk_msg = evaluate_risk_level(article) if article else ("green", "Verde: Contenido estándar")

            scheduled_date = now + timedelta(days=item["day_offset"])

            slot = CalendarSlot(
                article_id=article.id if article else None,
                title=title,
                format_type=item["format"],
                scheduled_date=scheduled_date,
                channel=item["channel"],
                status="planned",
                risk_level=risk_lvl,
                risk_reason=risk_msg
            )
            self.db.add(slot)
            self.db.commit()
            self.db.refresh(slot)

            # Create default tasks for slot
            tasks_list = [
                EditorialTask(slot_id=slot.id, task_name="Borrador y Adaptación de Texto", assignee="Juan Vásquez", status="completed" if idx == 0 else "pending"),
                EditorialTask(slot_id=slot.id, task_name="Revisión de Riesgo Legal / Marcas", assignee="Asesor Legal", status="pending"),
                EditorialTask(slot_id=slot.id, task_name="Publicación y Programación CM", assignee="Community Manager", status="pending")
            ]
            for t in tasks_list:
                self.db.add(t)
            
            self.db.commit()
            created_slots.append(slot)

        return created_slots

    def log_decision(self, entity_type: str, entity_id: int, action: str, actor: str = "Juan Vásquez", reason: str = "") -> DecisionLog:
        """Logs an audited decision into decision_logs table."""
        log = DecisionLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            reason=reason
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
