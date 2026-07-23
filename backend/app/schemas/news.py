from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional, List

class NewsArticleBase(BaseModel):
    title: str
    url: str
    source_name: str
    category: str
    published_at: Optional[datetime] = None
    content_full: Optional[str] = None
    summary: Optional[str] = None
    verification_status: Optional[str] = "pending"
    verification_reason: Optional[str] = None
    verified_at: Optional[datetime] = None
    top10_score: Optional[float] = 0.0

class NewsArticleCreate(NewsArticleBase):
    content_hash: str

class NewsArticleResponse(NewsArticleBase):
    id: int
    content_hash: str
    created_at: datetime

    class Config:
        from_attributes = True

class NewsIngestResult(BaseModel):
    total_fetched: int
    total_inserted: int
    duplicates_skipped: int
    categories_processed: List[str]

class AISummaryOutput(BaseModel):
    article_id: int
    source_url: str
    key_claims: List[str]
    executive_summary: str
    editorial_angle: str

class VerificationResult(BaseModel):
    article_id: int
    is_verified: bool
    grounded_claims: List[str]
    rejected_claims: List[str]
    reason: str

