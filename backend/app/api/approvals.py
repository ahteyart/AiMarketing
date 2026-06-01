from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.content import GeneratedContent
from app.workflow.approval import approve, reject, submit_for_review

router = APIRouter(prefix="/approvals", tags=["approvals"])


class ApproveRequest(BaseModel):
    edited_copy: str | None = None
    notes: str | None = None


class RejectRequest(BaseModel):
    reason: str
    notes: str | None = None


@router.get("/")
async def list_pending_approvals(
    campaign_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(GeneratedContent).where(GeneratedContent.status == "pending_review")
    if campaign_id:
        query = query.where(GeneratedContent.campaign_id == campaign_id)
    query = query.order_by(GeneratedContent.created_at)
    result = await db.execute(query)
    items = result.scalars().all()
    return {
        "count": len(items),
        "items": [
            {
                "id": str(item.id),
                "campaign_id": str(item.campaign_id),
                "platform": item.platform,
                "content_type": item.content_type,
                "copy_text": item.copy_text,
                "copy_attention": item.copy_attention,
                "image_url": item.image_url,
                "thumbnail_url": item.thumbnail_url,
                "platform_compliance": item.platform_compliance,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ],
    }


@router.post("/{content_id}/submit")
async def submit_for_review_endpoint(content_id: UUID, db: AsyncSession = Depends(get_db)):
    try:
        content = await submit_for_review(content_id, db)
        return {"id": str(content.id), "status": content.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{content_id}/approve")
async def approve_content(content_id: UUID, body: ApproveRequest, db: AsyncSession = Depends(get_db)):
    try:
        content = await approve(content_id, db, edited_copy=body.edited_copy, notes=body.notes)
        return {"id": str(content.id), "status": content.status, "approved_at": content.approved_at.isoformat()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{content_id}/reject")
async def reject_content(content_id: UUID, body: RejectRequest, db: AsyncSession = Depends(get_db)):
    try:
        content = await reject(content_id, db, reason=body.reason, notes=body.notes)
        return {"id": str(content.id), "status": content.status}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
