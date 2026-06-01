"""add language field to campaigns

Revision ID: 002_add_language
Revises: 001_initial_schema
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "002_add_language"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("campaigns", sa.Column("language", sa.String(20), server_default="english", nullable=False))
    op.add_column("calendar_entries", sa.Column("content_style", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("campaigns", "language")
    op.drop_column("calendar_entries", "content_style")
