"""Exports canónicos Autoridad 360 (Fases 1–7)."""

from app.db.database import Base, SessionLocal, engine, get_db
from app.models.ai_providers import AIProvider, AIUsageLog
from app.models.ai_models import AIModel
from app.models.background_jobs import BackgroundJob
from app.models.content import ContentPackage, ContentPiece

try:
    from app.models.content import MultiFormatContent
except Exception:  # pragma: no cover
    MultiFormatContent = ContentPackage

from app.models.editorial import (
    ArticleStatus,
    AuditLog,
    BlogPost,
    BlogStatus,
    NewsArticle,
    NewsCategory,
    WeeklyReport,
)
from app.models.learning import (
    ContentEngagement,
    Lead,
    MetricSnapshot,
    PercentageRecommendation,
)
from app.models.operations import (
    CadenceRule,
    CalendarSlot,
    DecisionLog,
    EditorialTask,
)
from app.models.org import ROLES, AppUser, Organization, OrgMembership
from app.models.auth_sessions import AuthSession
from app.models.publishing import (
    ChannelAccount,
    ChannelVariant,
    MediaAsset,
    PublishJob,
    PublishPackage,
)
from app.models.legal_seo import (
    ContentBrief,
    LegalClaim,
    LegalEvidence,
    PromptTemplate,
    SeoKeywordCluster,
)
from app.models.marketing import CampaignLink, NewsletterSubscriber, ServiceOffer
from app.models.saas import ContentRefreshItem, CustomDomain
from app.models.profile import (
    ContentPillar,
    EditorialPercentage,
    MarketPercentage,
    ProfessionalProfile,
)

__all__ = [
    "AIModel",
    "AIProvider",
    "AIUsageLog",
    "AppUser",
    "ArticleStatus",
    "AuditLog",
    "AuthSession",
    "BackgroundJob",
    "Base",
    "BlogPost",
    "BlogStatus",
    "CadenceRule",
    "CalendarSlot",
    "CampaignLink",
    "ChannelAccount",
    "ChannelVariant",
    "ContentBrief",
    "ContentEngagement",
    "ContentPackage",
    "ContentPiece",
    "ContentPillar",
    "ContentRefreshItem",
    "CustomDomain",
    "DecisionLog",
    "EditorialPercentage",
    "EditorialTask",
    "Lead",
    "LegalClaim",
    "LegalEvidence",
    "MarketPercentage",
    "MediaAsset",
    "MetricSnapshot",
    "MultiFormatContent",
    "NewsArticle",
    "NewsCategory",
    "NewsletterSubscriber",
    "Organization",
    "OrgMembership",
    "PercentageRecommendation",
    "ProfessionalProfile",
    "PromptTemplate",
    "PublishJob",
    "PublishPackage",
    "ROLES",
    "SeoKeywordCluster",
    "ServiceOffer",
    "SessionLocal",
    "WeeklyReport",
    "engine",
    "get_db",
]
