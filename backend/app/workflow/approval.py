"""
Approval workflow state machine for generated content.
States: draft → pending_review → approved | rejected → exported
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import ApprovalAction
from app.models.content import GeneratedContent

VALID_TRANSITIONS = {
    "draft": ["pending_review"],
    "generating": ["pending_review", "draft"],
    "pending_review": ["approved", "rejected"],
    "rejected": ["pending_review"],
    "approved": ["exported"],
    "exported": [],
}


async def submit_for_review(content_id: UUID, db: AsyncSession) -> GeneratedContent:
    content = await db.get(GeneratedContent, content_id)
    _assert_transition(content.status, "pending_review")
    content.status = "pending_review"
    await db.flush()
    return content


async def approve(
    content_id: UUID,
    db: AsyncSession,
    edited_copy: str | None = None,
    notes: str | None = None,
) -> GeneratedContent:
    content = await db.get(GeneratedContent, content_id)
    _assert_transition(content.status, "approved")

    if edited_copy:
        content.copy_text = edited_copy

    content.status = "approved"
    content.approved_at = datetime.now(timezone.utc)

    action = ApprovalAction(
        content_id=content_id,
        action="approve",
        edited_copy=edited_copy,
        notes=notes,
    )
    db.add(action)
    await db.flush()
    return content


async def reject(
    content_id: UUID,
    db: AsyncSession,
    reason: str,
    notes: str | None = None,
) -> GeneratedContent:
    content = await db.get(GeneratedContent, content_id)
    _assert_transition(content.status, "rejected")
    content.status = "rejected"

    action = ApprovalAction(
        content_id=content_id,
        action="reject",
        rejection_reason=reason,
        notes=notes,
    )
    db.add(action)
    await db.flush()
    return content


async def mark_exported(content_id: UUID, db: AsyncSession) -> GeneratedContent:
    content = await db.get(GeneratedContent, content_id)
    _assert_transition(content.status, "exported")
    content.status = "exported"
    await db.flush()
    return content


def _assert_transition(current: str, target: str) -> None:
    allowed = VALID_TRANSITIONS.get(current, [])
    if target not in allowed:
        raise ValueError(f"Invalid status transition: {current} → {target}. Allowed: {allowed}")
