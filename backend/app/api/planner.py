from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.calendar_entry import CalendarEntry
from app.models.campaign import Campaign
from app.planner.calendar_generator import generate_calendar

router = APIRouter(prefix="/planner", tags=["planner"])

# In-memory generation status tracker {campaign_id: {"status": "generating|done|error", "message": ""}}
_generation_status: dict[str, dict] = {}


class GenerateCalendarRequest(BaseModel):
    campaign_id: UUID
    start_date: date | None = None
    platforms: list[str] | None = None
    days: int = 30
    language: str | None = None


class CalendarEntryResponse(BaseModel):
    id: UUID
    day_number: int
    scheduled_date: date | None
    platform: str
    content_type: str
    theme: str | None
    aida_brief: str | None
    suggested_hooks: list[str] | None
    suggested_hashtags: list[str] | None
    content_format: str | None
    content_style: str | None = None
    status: str

    class Config:
        from_attributes = True


@router.get("/{campaign_id}/calendar", response_model=list[CalendarEntryResponse])
async def get_calendar(
    campaign_id: UUID,
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(CalendarEntry).where(CalendarEntry.campaign_id == campaign_id)
    if platform:
        query = query.where(CalendarEntry.platform == platform)
    query = query.order_by(CalendarEntry.day_number, CalendarEntry.platform)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/generate")
async def generate_calendar_endpoint(
    body: GenerateCalendarRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, body.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    platforms = body.platforms or campaign.target_platforms or ["instagram", "facebook", "xiaohongshu"]
    start_date = body.start_date or date.today()
    language = body.language or getattr(campaign, "language", "english") or "english"
    days = max(1, min(body.days, 30))

    _generation_status[str(body.campaign_id)] = {"status": "generating", "message": ""}
    background_tasks.add_task(
        _generate_calendar_task,
        body.campaign_id,
        campaign.name,
        campaign.brand_voice or "",
        campaign.target_audience or "",
        list(campaign.keywords or []),
        platforms,
        start_date,
        language,
        days,
    )
    return {
        "message": f"Generating {days}-day calendar in {language}. Check /planner/{body.campaign_id}/calendar shortly.",
        "days": days,
        "language": language,
        "platforms": platforms,
    }


@router.get("/{campaign_id}/generation-status")
async def get_generation_status(campaign_id: UUID):
    status = _generation_status.get(str(campaign_id))
    if not status:
        return {"status": "idle"}
    return status


@router.patch("/entry/{entry_id}", response_model=CalendarEntryResponse)
async def update_calendar_entry(
    entry_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(CalendarEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Calendar entry not found")
    allowed = {"theme", "content_type", "suggested_hooks", "suggested_hashtags", "scheduled_date", "content_format"}
    for key, value in body.items():
        if key in allowed:
            setattr(entry, key, value)
    await db.flush()
    return entry


async def _generate_calendar_task(
    campaign_id: UUID,
    campaign_name: str,
    brand_voice: str,
    target_audience: str,
    keywords: list[str],
    platforms: list[str],
    start_date: date,
    language: str,
    days: int,
):
    import json
    import logging
    from app.database import AsyncSessionLocal

    logger = logging.getLogger(__name__)

    async with AsyncSessionLocal() as db:
        try:
            entries = await generate_calendar(
                campaign_name=campaign_name,
                brand_voice=brand_voice,
                target_audience=target_audience,
                keywords=keywords,
                language=language,
                days=days,
                platforms=platforms,
                start_date=start_date,
            )

            # Clear existing entries for this campaign
            existing = await db.execute(
                select(CalendarEntry).where(CalendarEntry.campaign_id == campaign_id)
            )
            for entry in existing.scalars().all():
                await db.delete(entry)

            for entry_data in entries:
                aida = entry_data.get("aida_brief")
                aida_str = json.dumps(aida, ensure_ascii=False) if isinstance(aida, dict) else (aida or "")
                raw_date = entry_data.get("scheduled_date")
                try:
                    from datetime import date as date_type
                    parsed_date = date_type.fromisoformat(raw_date) if isinstance(raw_date, str) else raw_date
                except (ValueError, TypeError):
                    parsed_date = None
                db.add(CalendarEntry(
                    campaign_id=campaign_id,
                    day_number=entry_data.get("day_number", 1),
                    scheduled_date=parsed_date,
                    platform=entry_data.get("platform", "instagram"),
                    content_type=entry_data.get("content_type", "image_post"),
                    theme=entry_data.get("theme"),
                    aida_brief=aida_str,
                    suggested_hooks=entry_data.get("suggested_hooks", []),
                    suggested_hashtags=entry_data.get("suggested_hashtags", []),
                    content_format=entry_data.get("content_format"),
                    content_style=entry_data.get("content_style"),
                ))

            await db.commit()
            logger.info("Calendar done: %d entries, campaign %s (%s, %dd)", len(entries), campaign_id, language, days)

            _generation_status[str(campaign_id)] = {"status": "done", "message": f"{len(entries)} entries"}

        except Exception as e:
            logger.error("Calendar generation failed for %s: %s", campaign_id, e, exc_info=True)
            _generation_status[str(campaign_id)] = {"status": "error", "message": str(e)}
            await db.rollback()
