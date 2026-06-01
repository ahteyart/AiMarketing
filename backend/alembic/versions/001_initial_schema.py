"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campaigns",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("brand_context", postgresql.JSONB()),
        sa.Column("brand_voice", sa.Text()),
        sa.Column("target_audience", sa.Text()),
        sa.Column("target_platforms", postgresql.ARRAY(sa.String())),
        sa.Column("keywords", postgresql.ARRAY(sa.String())),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "calendar_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date()),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("theme", sa.Text()),
        sa.Column("aida_brief", sa.Text()),
        sa.Column("suggested_hooks", postgresql.ARRAY(sa.String())),
        sa.Column("suggested_hashtags", postgresql.ARRAY(sa.String())),
        sa.Column("content_format", sa.String(100)),
        sa.Column("status", sa.String(50), server_default="planned"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "generated_content",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("calendar_entry_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("calendar_entries.id")),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("copy_text", sa.Text()),
        sa.Column("copy_attention", sa.Text()),
        sa.Column("copy_interest", sa.Text()),
        sa.Column("copy_desire", sa.Text()),
        sa.Column("copy_action", sa.Text()),
        sa.Column("copy_variants", postgresql.JSONB()),
        sa.Column("hashtags", postgresql.ARRAY(sa.String())),
        sa.Column("image_url", sa.Text()),
        sa.Column("video_url", sa.Text()),
        sa.Column("thumbnail_url", sa.Text()),
        sa.Column("canva_design_id", sa.String(255)),
        sa.Column("platform_compliance", postgresql.JSONB()),
        sa.Column("research_post_ids", postgresql.ARRAY(sa.String())),
        sa.Column("generation_metadata", postgresql.JSONB()),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "approval_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("generated_content.id"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("edited_copy", sa.Text()),
        sa.Column("rejection_reason", sa.Text()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sheet_exports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("campaigns.id"), nullable=False),
        sa.Column("spreadsheet_id", sa.String(255)),
        sa.Column("spreadsheet_url", sa.Text()),
        sa.Column("spreadsheet_title", sa.String(255)),
        sa.Column("entry_count", sa.Integer(), server_default="0"),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("error_message", sa.Text()),
        sa.Column("exported_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sheet_exports")
    op.drop_table("approval_actions")
    op.drop_table("generated_content")
    op.drop_table("calendar_entries")
    op.drop_table("campaigns")
