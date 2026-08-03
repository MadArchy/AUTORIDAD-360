from datetime import datetime
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

class MultiNewsSynthesis(Base):
    __tablename__ = "multi_news_syntheses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id"), nullable=True, index=True
    )
    pillar_id: Mapped[int | None] = mapped_column(
        ForeignKey("content_pillars.id"), nullable=True, index=True
    )
    central_focus: Mapped[str] = mapped_column(Text, nullable=False)
    source_article_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    blog_post_id: Mapped[int | None] = mapped_column(
        ForeignKey("blog_posts.id"), nullable=True, index=True
    )
    synthesis_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    blog_post: Mapped["BlogPost"] = relationship("BlogPost")
