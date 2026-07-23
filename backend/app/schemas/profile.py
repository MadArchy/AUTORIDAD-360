from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PillarSchema(BaseModel):
    id: Optional[int] = None
    name: str
    category_key: str
    target_percentage: float
    description: Optional[str] = None
    current_month_count: Optional[int] = 0
    current_month_pct: Optional[float] = 0.0
    quota_status: Optional[str] = "balanced" # 'below_quota', 'balanced', 'above_quota'

class MarketPctSchema(BaseModel):
    id: Optional[int] = None
    market_code: str
    market_name: str
    target_percentage: float
    current_month_pct: Optional[float] = 0.0

class ProfileBase(BaseModel):
    full_name: str
    title: str
    bio: Optional[str] = None
    target_audiences: List[str]
    services: List[str]

class ProfileCreate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    pillars: List[PillarSchema]
    markets: List[MarketPctSchema]
    updated_at: datetime

    class Config:
        from_attributes = True
