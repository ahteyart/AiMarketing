"""
Instagram research via Meta Graph API.
Uses hashtag search endpoint to find trending content.
Rate limit: 200 calls/hour. Max 30 unique hashtags per 7 days per account.
"""

import logging

import httpx

from app.config import settings
from app.research.base import RawPost, ResearchProvider

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"


class InstagramResearch(ResearchProvider):
    platform = "instagram"

    def __init__(self):
        self.access_token = settings.meta_page_access_token
        self.ig_account_id = settings.meta_instagram_business_account_id

    async def health_check(self) -> bool:
        if not self.access_token or not self.ig_account_id:
            return False
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{GRAPH_BASE}/{self.ig_account_id}",
                params={"access_token": self.access_token, "fields": "id,name"},
            )
            return r.status_code == 200

    async def fetch_trending(self, keywords: list[str], limit: int = 20) -> list[RawPost]:
        posts: list[RawPost] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for keyword in keywords[:5]:  # Cap at 5 hashtags per run to conserve quota
                hashtag = keyword.lstrip("#").replace(" ", "")
                try:
                    hashtag_id = await self._get_hashtag_id(client, hashtag)
                    if not hashtag_id:
                        continue
                    media = await self._get_top_media(client, hashtag_id, limit)
                    posts.extend(media)
                except Exception as e:
                    logger.warning("Instagram hashtag '%s' failed: %s", hashtag, e)
        return posts

    async def _get_hashtag_id(self, client: httpx.AsyncClient, hashtag: str) -> str | None:
        r = await client.get(
            f"{GRAPH_BASE}/ig_hashtag_search",
            params={
                "user_id": self.ig_account_id,
                "q": hashtag,
                "access_token": self.access_token,
            },
        )
        data = r.json()
        if "data" in data and data["data"]:
            return data["data"][0]["id"]
        logger.warning("No hashtag ID found for #%s: %s", hashtag, data.get("error"))
        return None

    async def _get_top_media(self, client: httpx.AsyncClient, hashtag_id: str, limit: int) -> list[RawPost]:
        r = await client.get(
            f"{GRAPH_BASE}/{hashtag_id}/top_media",
            params={
                "user_id": self.ig_account_id,
                "fields": "id,caption,media_type,permalink,like_count,comments_count,timestamp",
                "limit": min(limit, 50),
                "access_token": self.access_token,
            },
        )
        data = r.json()
        posts = []
        for item in data.get("data", []):
            caption = item.get("caption", "")
            hashtags = [w.lstrip("#") for w in caption.split() if w.startswith("#")] if caption else []
            posts.append(
                RawPost(
                    platform="instagram",
                    external_id=item.get("id"),
                    content_url=item.get("permalink"),
                    author_handle=None,
                    caption=caption,
                    hashtags=hashtags,
                    likes=item.get("like_count", 0),
                    comments=item.get("comments_count", 0),
                    raw_metadata=item,
                )
            )
        return posts
