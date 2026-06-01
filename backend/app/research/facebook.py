"""
Facebook research via Meta Graph API.
Reads posts from managed pages and hashtag search.
"""

import logging

import httpx

from app.config import settings
from app.research.base import RawPost, ResearchProvider

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.facebook.com/v21.0"


class FacebookResearch(ResearchProvider):
    platform = "facebook"

    def __init__(self):
        self.access_token = settings.meta_page_access_token

    async def health_check(self) -> bool:
        if not self.access_token:
            return False
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{GRAPH_BASE}/me",
                params={"access_token": self.access_token, "fields": "id,name"},
            )
            return r.status_code == 200

    async def fetch_trending(self, keywords: list[str], limit: int = 20) -> list[RawPost]:
        """Fetch public posts via keyword search."""
        posts: list[RawPost] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for keyword in keywords[:3]:
                try:
                    results = await self._search_posts(client, keyword, limit)
                    posts.extend(results)
                except Exception as e:
                    logger.warning("Facebook search for '%s' failed: %s", keyword, e)
        return posts

    async def _search_posts(self, client: httpx.AsyncClient, keyword: str, limit: int) -> list[RawPost]:
        r = await client.get(
            f"{GRAPH_BASE}/search",
            params={
                "q": keyword,
                "type": "post",
                "fields": "id,message,created_time,permalink_url,reactions.summary(true),comments.summary(true),shares",
                "limit": min(limit, 100),
                "access_token": self.access_token,
            },
        )
        data = r.json()
        posts = []
        for item in data.get("data", []):
            message = item.get("message", "")
            hashtags = [w.lstrip("#") for w in message.split() if w.startswith("#")] if message else []
            reactions = item.get("reactions", {}).get("summary", {}).get("total_count", 0)
            comments = item.get("comments", {}).get("summary", {}).get("total_count", 0)
            shares = item.get("shares", {}).get("count", 0)
            posts.append(
                RawPost(
                    platform="facebook",
                    external_id=item.get("id"),
                    content_url=item.get("permalink_url"),
                    author_handle=None,
                    caption=message,
                    hashtags=hashtags,
                    likes=reactions,
                    comments=comments,
                    shares=shares,
                    raw_metadata=item,
                )
            )
        return posts
