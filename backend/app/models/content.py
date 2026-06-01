import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class GeneratedContent(Base):
    __tablename__ = "generated_content"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    calendar_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("calendar_entries.id"), nullable=True
    )

    # instagram | facebook | xiaohongshu
    platform: Mapped[str] = mapped_column(String(50), nullable=False)

    # image_post | video | carousel | reel | story
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # AIDA-structured copy
    copy_text: Mapped[str | None] = mapped_column(Text)
    copy_attention: Mapped[str | None] = mapped_column(Text)  # [A] hook
    copy_interest: Mapped[str | None] = mapped_column(Text)   # [I] body
    copy_desire: Mapped[str | None] = mapped_column(Text)     # [D] value
    copy_action: Mapped[str | None] = mapped_column(Text)     # [A] CTA
    copy_variants: Mapped[list | None] = mapped_column(JSON)  # 3 AIDA variants from Claude

    hashtags: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Media
    image_url: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    canva_design_id: Mapped[str | None] = mapped_column(String(255))

    # Compliance check results
    platform_compliance: Mapped[dict | None] = mapped_column(JSON)

    # Source research posts that inspired this
    research_post_ids: Mapped[list[str] | None] = mapped_column(ARRAY(String))

    # Generation metadata (prompts, model, cost)
    generation_metadata: Mapped[dict | None] = mapped_column(JSON)

    # draft | generating | pending_review | approved | rejected | exported
    status: Mapped[str] = mapped_column(String(50), default="draft")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    campaign = relationship("Campaign", back_populates="generated_contents")
    calendar_entry = relationship("CalendarEntry", back_populates="generated_contents")
    approval_actions = relationship("ApprovalAction", back_populates="content", cascade="all, delete-orphan")
