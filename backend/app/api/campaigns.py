from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.campaign import Campaign

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    brand_voice: str | None = None
    target_audience: str | None = None
    target_platforms: list[str] = ["instagram", "facebook", "xiaohongshu"]
    keywords: list[str] = []
    brand_context: dict | None = None
    language: str = "english"


class CampaignResponse(BaseModel):
    id: UUID
    name: str
    brand_voice: str | None
    target_audience: str | None
    target_platforms: list[str] | None
    keywords: list[str] | None
    brand_context: dict | None
    status: str
    language: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[CampaignResponse])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.status != "archived").order_by(Campaign.created_at.desc()))
    return result.scalars().all()


@router.post("/", response_model=CampaignResponse, status_code=201)
async def create_campaign(body: CampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = Campaign(**body.model_dump())
    db.add(campaign)
    await db.flush()
    return campaign


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(campaign_id: UUID, body: dict, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    allowed_fields = {"name", "brand_voice", "target_audience", "target_platforms", "keywords", "brand_context", "status", "language"}
    for key, value in body.items():
        if key in allowed_fields:
            setattr(campaign, key, value)
    await db.flush()
    return campaign


@router.delete("/{campaign_id}", status_code=204)
async def archive_campaign(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    campaign = await db.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = "archived"
