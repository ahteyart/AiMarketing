"""
TikTok research via Apify TikTok scraper.
Uses the clockworks/tiktok-scraper actor (~$2-5 per 1000 videos).
"""

import logging

from apify_client import ApifyClient

from app.config import settings
from app.research.base import RawPost, ResearchProvider

logger = logging.getLogger(__name__)

TIKTOK_SCRAPER_ACTOR = "clockworks/tiktok-scraper"


class TikTokResearch(ResearchProvider):
    platform = "tiktok"

    def __init__(self):
        self.client = ApifyClient(settings.apify_api_token) if settings.apify_api_token else None

    async def health_check(self) -> bool:
        return self.client is not None and bool(settings.apify_api_token)

    async def fetch_trending(self, keywords: list[str], limit: int = 20) -> list[RawPost]:
        if not self.client:
            logger.warning("TikTok research unavailable: APIFY_API_TOKEN not set")
            return []

        posts = []
        for keyword in keywords[:3]:
            try:
                results = await self._run_scraper(keyword, limit)
                posts.extend(results)
            except Exception as e:
                logger.warning("TikTok scraper failed for '%s': %s", keyword, e)
        return posts

    async def _run_scraper(self, keyword: str, limit: int) -> list[RawPost]:
        run_input = {
            "hashtags": [keyword.lstrip("#")],
            "resultsPerPage": min(limit, 100),
            "shouldDownloadVideos": False,
            "shouldDownloadCovers": False,
        }

        run = self.client.actor(TIKTOK_SCRAPER_ACTOR).call(run_input=run_input)
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return []

        items = self.client.dataset(dataset_id).iterate_items()
        posts = []
        for item in items:
            stats = item.get("stats", {}) or item.get("statsV2", {})
            caption = item.get("desc", "")
            hashtags = [ch.get("hashtagName", "") for ch in item.get("challenges", [])]

            posts.append(
                RawPost(
                    platform="tiktok",
                    external_id=item.get("id"),
                    content_url=item.get("webVideoUrl"),
                    author_handle=item.get("authorMeta", {}).get("name"),
                    caption=caption,
                    hashtags=hashtags,
                    likes=int(stats.get("diggCount", 0)),
                    comments=int(stats.get("commentCount", 0)),
                    shares=int(stats.get("shareCount", 0)),
                    saves=int(stats.get("collectCount", 0)),
                    views=int(stats.get("playCount", 0)),
                    followers=int(item.get("authorMeta", {}).get("fans", 0)),
                    raw_metadata={"id": item.get("id"), "stats": stats},
                )
            )
        return posts
