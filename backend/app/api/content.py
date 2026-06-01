import json
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.generation.copywriter import generate_aida_copy
from app.generation.designer import DesignRequest, generate_design
from app.generation.video_gen import estimate_cost, generate_video_from_image
from app.models.calendar_entry import CalendarEntry
from app.models.campaign import Campaign
from app.models.content import GeneratedContent
from app.planner.platform_rules import check_compliance

router = APIRouter(prefix="/content", tags=["content"])


class GenerateContentRequest(BaseModel):
    calendar_entry_id: UUID
    generate_image: bool = True
    generate_video: bool = False  # Must be explicitly requested due to cost


class ContentResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    platform: str
    content_type: str
    copy_text: str | None
    copy_attention: str | None
    copy_interest: str | None
    copy_desire: str | None
    copy_action: str | None
    copy_variants: list | None
    hashtags: list[str] | None
    image_url: str | None
    video_url: str | None
    thumbnail_url: str | None
    canva_design_id: str | None
    platform_compliance: dict | None
    status: str

    class Config:
        from_attributes = True


@router.get("/{campaign_id}", response_model=list[ContentResponse])
async def list_content(
    campaign_id: UUID,
    status: str | None = None,
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(GeneratedContent).where(GeneratedContent.campaign_id == campaign_id)
    if status:
        query = query.where(GeneratedContent.status == status)
    if platform:
        query = query.where(GeneratedContent.platform == platform)
    query = query.order_by(GeneratedContent.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/item/{content_id}", response_model=ContentResponse)
async def get_content(content_id: UUID, db: AsyncSession = Depends(get_db)):
    content = await db.get(GeneratedContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/generate", status_code=202)
async def generate_content(
    body: GenerateContentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(CalendarEntry, body.calendar_entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Calendar entry not found")

    campaign = await db.get(Campaign, entry.campaign_id)

    # Create placeholder content record
    content = GeneratedContent(
        campaign_id=entry.campaign_id,
        calendar_entry_id=entry.id,
        platform=entry.platform,
        content_type=entry.content_type,
        status="generating",
    )
    db.add(content)
    entry.status = "generating"
    await db.flush()
    content_id = content.id

    background_tasks.add_task(
        _generate_content_task,
        content_id=content_id,
        campaign_name=campaign.name,
        brand_voice=campaign.brand_voice or "",
        target_audience=campaign.target_audience or "",
        language=getattr(campaign, "language", "english") or "english",
        platform=entry.platform,
        content_type=entry.content_type,
        theme=entry.theme or "",
        content_style=entry.content_style or "educational",
        aida_brief=json.loads(entry.aida_brief) if entry.aida_brief else None,
        suggested_hashtags=entry.suggested_hashtags or [],
        generate_image=body.generate_image,
    )

    return {"message": "Content generation started", "content_id": str(content_id)}


@router.patch("/item/{content_id}", response_model=ContentResponse)
async def update_content(content_id: UUID, body: dict, db: AsyncSession = Depends(get_db)):
    content = await db.get(GeneratedContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    allowed = {"copy_text", "copy_attention", "copy_interest", "copy_desire", "copy_action", "hashtags"}
    for key, value in body.items():
        if key in allowed:
            setattr(content, key, value)

    # Re-run compliance check after edit
    if "copy_text" in body or "hashtags" in body:
        compliance = check_compliance(
            content.platform,
            content.copy_text or "",
            content.hashtags or [],
        )
        content.platform_compliance = compliance

    await db.flush()
    return content


@router.post("/item/{content_id}/generate-video")
async def request_video_generation(
    content_id: UUID,
    confirmed: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Trigger video generation for a content item. Shows cost estimate first."""
    content = await db.get(GeneratedContent, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    cost_info = estimate_cost(duration_seconds=5)

    if not confirmed:
        return {"cost_estimate": cost_info, "action": "Pass ?confirmed=true to proceed"}

    if not content.image_url:
        raise HTTPException(status_code=400, detail="No image available to animate. Generate image first.")

    result = await generate_video_from_image(
        image_url=content.image_url,
        motion_prompt=f"Gentle motion, lifestyle feel. {content.copy_attention or ''}",
    )
    content.generation_metadata = {**(content.generation_metadata or {}), "video_job": result}
    await db.flush()

    return {"job_id": result.get("job_id"), "status": result.get("status"), "cost": cost_info}


async def _generate_content_task(
    content_id: UUID,
    campaign_name: str,
    brand_voice: str,
    target_audience: str,
    language: str,
    platform: str,
    content_type: str,
    theme: str,
    content_style: str,
    aida_brief: dict | None,
    suggested_hashtags: list[str],
    generate_image: bool,
):
    import logging
    from app.database import AsyncSessionLocal

    logger = logging.getLogger(__name__)

    async with AsyncSessionLocal() as db:
        content = await db.get(GeneratedContent, content_id)
        try:
            # 1. Generate AIDA copy
            copy_result = await generate_aida_copy(
                platform=platform,
                theme=theme,
                aida_brief=aida_brief or {},
                content_style=content_style,
                language=language,
                brand_voice=brand_voice,
                target_audience=target_audience,
            )

            best_variant = copy_result["variants"][0] if copy_result["variants"] else {}
            content.copy_text = best_variant.get("full_copy")
            content.copy_attention = best_variant.get("copy_attention")
            content.copy_interest = best_variant.get("copy_interest")
            content.copy_desire = best_variant.get("copy_desire")
            content.copy_action = best_variant.get("copy_action")
            content.hashtags = best_variant.get("hashtags") or suggested_hashtags
            content.copy_variants = copy_result["variants"]

            # XHS has title field
            if platform == "xiaohongshu" and best_variant.get("title"):
                meta = content.generation_metadata or {}
                meta["xhs_title"] = best_variant["title"]
                content.generation_metadata = meta

            # Compliance check
            content.platform_compliance = best_variant.get("compliance") or check_compliance(
                platform, content.copy_text or "", content.hashtags or []
            )

            # 2. Generate design via Canva MCP
            if generate_image:
                design_req = DesignRequest(
                    platform=platform,
                    content_type=content_type,
                    theme=theme,
                    copy_attention=content.copy_attention or theme,
                )
                design_result = await generate_design(design_req, canva_mcp=None)
                content.image_url = design_result.export_url
                content.thumbnail_url = design_result.thumbnail_url
                content.canva_design_id = design_result.design_id

            content.status = "pending_review"
            await db.commit()
            logger.info("Content %s generated successfully", content_id)

        except Exception as e:
            logger.error("Content generation failed for %s: %s", content_id, e)
            content.status = "draft"
            content.generation_metadata = {"error": str(e)}
            await db.commit()
