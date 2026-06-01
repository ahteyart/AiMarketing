from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.campaign import Campaign
from app.models.research import ResearchPost
from app.research.facebook import FacebookResearch
from app.research.instagram import InstagramResearch
from app.research.tiktok import TikTokResearch
from app.research.xiaohongshu import XiaohongshuResearch
from app.research.trend_analyzer import deduplicate, extract_trending_topics, score_and_rank

router = APIRouter(prefix="/research", tags=["research"])

PROVIDERS = {
    "instagram": InstagramResearch,
    "facebook": FacebookResearch,
    "tiktok": TikTokResearch,
    "xiaohongshu": XiaohongshuResearch,
}


class ResearchTriggerRequest(BaseModel):
    campaign_id: UUID
    platforms: list[str] | None = None  # None = all campaign platforms
    keywords: list[str] | None = None    # None = use campaign keywords


class ResearchPostResponse(BaseModel):
    id: UUID
    platform: str
    external_id: str | None
    content_url: str | None
    author_handle: str | None
    caption: str | None
    hashtags: list[str] | None
    likes: int
    comments: int
    shares: int
    saves: int
    views: int
    engagement_score: float

    class Config:
        from_attributes = True


@router.get("/{campaign_id}", response_model=list[ResearchPostResponse])
async def get_research_posts(
    campaign_id: UUID,
    platform: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    query = select(ResearchPost).where(ResearchPost.campaign_id == campaign_id)
    if platform:
        query = query.where(ResearchPost.platform == platform)
    query = query.order_by(ResearchPost.engagement_score.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{campaign_id}/topics")
async def get_trending_topics(
    campaign_id: UUID,
    platform: str | None = None,
    top_n: int = 10,
    db: AsyncSession = Depends(get_db),
):
    query = select(ResearchPost).where(ResearchPost.campaign_id == campaign_id)
    if platform:
        query = query.where(ResearchPost.platform == platform)
    result = await db.execute(query)
    posts_db = result.scalars().all()

    from app.research.base import RawPost
    raw_posts = [
        RawPost(
            platform=p.platform,
            external_id=p.external_id,
            content_url=p.content_url,
            author_handle=p.author_handle,
            caption=p.caption,
            hashtags=p.hashtags or [],
            likes=p.likes,
            comments=p.comments,
            shares=p.shares,
            saves=p.saves,
            views=p.views,
        )
        for p in posts_db
    ]
    return {"topics": extract_trending_topics(raw_posts, top_n=top_n)}


@router.post("/trigger")
async def trigger_research(
    body: ResearchTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    campaign = await db.get(Campaign, body.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    platforms = body.platforms or campaign.target_platforms or list(PROVIDERS.keys())
    keywords = body.keywords or campaign.keywords or []

    background_tasks.add_task(_run_research, body.campaign_id, platforms, keywords)
    return {"message": "Research job started", "platforms": platforms, "keywords": keywords}


async def _run_research(campaign_id: UUID, platforms: list[str], keywords: list[str]):
    """Background task: scrape all platforms and save to DB."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        for platform in platforms:
            provider_cls = PROVIDERS.get(platform)
            if not provider_cls:
                continue
            try:
                provider = provider_cls()
                raw_posts = await provider.fetch_trending(keywords, limit=30)
                raw_posts = deduplicate(raw_posts)
                raw_posts = score_and_rank(raw_posts)

                for raw in raw_posts:
                    # Upsert by (platform, external_id)
                    if raw.external_id:
                        existing = await db.execute(
                            select(ResearchPost).where(
                                ResearchPost.platform == raw.platform,
                                ResearchPost.external_id == raw.external_id,
                            )
                        )
                        existing = existing.scalar_one_or_none()
                        if existing:
                            existing.engagement_score = raw.engagement_score()
                            continue

                    post = ResearchPost(
                        campaign_id=campaign_id,
                        platform=raw.platform,
                        external_id=raw.external_id,
                        content_url=raw.content_url,
                        author_handle=raw.author_handle,
                        caption=raw.caption,
                        hashtags=raw.hashtags,
                        likes=raw.likes,
                        comments=raw.comments,
                        shares=raw.shares,
                        saves=raw.saves,
                        views=raw.views,
                        followers=raw.followers,
                        engagement_score=raw.engagement_score(),
                    )
                    db.add(post)

                await db.commit()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error("Research failed for %s: %s", platform, e)
                await db.rollback()
