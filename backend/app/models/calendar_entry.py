import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class CalendarEntry(Base):
    __tablename__ = "calendar_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)

    day_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-30
    scheduled_date: Mapped[date | None] = mapped_column(Date)

    # instagram | facebook | xiaohongshu
    platform: Mapped[str] = mapped_column(String(50), nullable=False)

    # image_post | video | carousel | reel | story
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)

    theme: Mapped[str | None] = mapped_column(Text)
    aida_brief: Mapped[str | None] = mapped_column(Text)  # AI-generated AIDA outline for this entry
    suggested_hooks: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    suggested_hashtags: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    content_format: Mapped[str | None] = mapped_column(String(100))  # e.g. "9:16 Reel", "3:4 图文笔记"

    # planning | generating | pending_review | approved | exported
    status: Mapped[str] = mapped_column(String(50), default="planned")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", back_populates="calendar_entries")
    generated_contents = relationship("GeneratedContent", back_populates="calendar_entry")
