import re
import json
import logging
from datetime import datetime
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.news import NewsArticle
from app.schemas.news import AISummaryOutput, VerificationResult

logger = logging.getLogger(__name__)

def extract_keywords(text: str) -> set:
    """Extracts normalized word tokens (excluding short stopwords)."""
    words = re.findall(r'\b[a-zA-ZáéíóúÁÉÍÓÚñÑ0-9]{3,}\b', text.lower())
    stopwords = {"para", "como", "esta", "este", "entre", "sobre", "tras", "desde", "hasta", "hacia", "según", "tienen", "tiene", "donde", "quien", "pero", "para", "por", "con", "sin", "las", "los", "una", "uno", "unos", "unas", "del", "que"}
    return {w for w in words if w not in stopwords}

def calculate_grounding_score(claim: str, source_text: str) -> float:
    """
    Calculates word token overlap between a claim and the source text.
    Returns a float score between 0.0 and 1.0 representing grounding confidence.
    """
    claim_tokens = extract_keywords(claim)
    if not claim_tokens:
        return 1.0

    source_tokens = extract_keywords(source_text)
    match_count = sum(1 for t in claim_tokens if t in source_tokens)
    return match_count / len(claim_tokens)

class FactVerifierService:
    def __init__(self, db: Session):
        self.db = db

    def verify_and_save_summary(self, article: NewsArticle, ai_output: AISummaryOutput) -> VerificationResult:
        """
        Performs strict factual verification pass against article.content_full.
        If all key claims are grounded, marks article as 'verified' and saves summary.
        If any claim fails grounding, marks article as 'rejected' with reason.
        """
        source_text = article.content_full or ""
        grounded_claims: List[str] = []
        rejected_claims: List[str] = []

        # Check each key claim
        for claim in ai_output.key_claims:
            score = calculate_grounding_score(claim, source_text)
            if score >= 0.35: # Threshold for factual grounding overlap
                grounded_claims.append(claim)
            else:
                rejected_claims.append(f"Claim unsupported (Grounding score: {score:.2f}): '{claim}'")

        # Also check executive summary
        exec_score = calculate_grounding_score(ai_output.executive_summary, source_text)
        if exec_score < 0.30:
            rejected_claims.append(f"Executive summary contains unsupported statements (Grounding score: {exec_score:.2f})")

        is_verified = (len(rejected_claims) == 0)
        
        # Prepare summary payload JSON
        summary_payload = {
            "key_claims": ai_output.key_claims,
            "executive_summary": ai_output.executive_summary,
            "editorial_angle": ai_output.editorial_angle,
            "grounded_claims_count": len(grounded_claims),
            "rejected_claims_count": len(rejected_claims)
        }

        article.summary = json.dumps(summary_payload, ensure_ascii=False)
        article.verified_at = datetime.utcnow()

        if is_verified:
            article.verification_status = "verified"
            article.verification_reason = f"Verificación exitosa. 100% de las afirmaciones ({len(grounded_claims)}) están respaldadas en el texto original."
            reason_msg = article.verification_reason
        else:
            article.verification_status = "rejected"
            article.verification_reason = f"Rechazado por posible alucinación o falta de respaldo en el texto fuente. {len(rejected_claims)} afirmaciones no verificadas."
            reason_msg = article.verification_reason

        self.db.commit()
        self.db.refresh(article)

        return VerificationResult(
            article_id=article.id,
            is_verified=is_verified,
            grounded_claims=grounded_claims,
            rejected_claims=rejected_claims,
            reason=reason_msg
        )
