"""
Xiaohongshu (小红书) research via Playwright browser automation.
XHS has no official API. Uses cookie-based session with proxy rotation.

Cookie rotation: maintain 3 XHS accounts, rotate on HTTP 461 (account blocked).
Proxy: Chinese residential proxy required (XHS blocks non-CN IPs).
"""

import json
import logging
import random
import time

from app.config import settings
from app.research.base import RawPost, ResearchProvider

logger = logging.getLogger(__name__)


class XiaohongshuResearch(ResearchProvider):
    platform = "xiaohongshu"

    def __init__(self):
        self._cookies = self._load_cookies()

    def _load_cookies(self) -> list[str]:
        cookies = []
        for cookie in [settings.xhs_cookie_1, settings.xhs_cookie_2, settings.xhs_cookie_3]:
            if cookie:
                cookies.append(cookie)
        return cookies

    async def health_check(self) -> bool:
        return len(self._cookies) > 0

    async def fetch_trending(self, keywords: list[str], limit: int = 20) -> list[RawPost]:
        if not self._cookies:
            logger.warning("XHS research unavailable: no XHS cookies configured")
            return []

        posts = []
        for keyword in keywords[:3]:
            try:
                results = await self._search_notes(keyword, limit)
                posts.extend(results)
                # Respectful delay between requests
                time.sleep(random.uniform(2, 5))
            except Exception as e:
                logger.warning("XHS search failed for '%s': %s", keyword, e)
        return posts

    async def _search_notes(self, keyword: str, limit: int) -> list[RawPost]:
        """
        Search XHS notes using Playwright headless browser.
        Falls back to Apify xiaohongshu-scraper if playwright fails.
        """
        try:
            return await self._playwright_search(keyword, limit)
        except Exception as e:
            logger.warning("XHS Playwright search failed, trying Apify fallback: %s", e)
            return await self._apify_fallback(keyword, limit)

    async def _playwright_search(self, keyword: str, limit: int) -> list[RawPost]:
        """Headless browser search on www.xiaohongshu.com/explore."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed")
            return []

        cookie_str = random.choice(self._cookies)
        posts = []

        async with async_playwright() as p:
            browser_args = []
            if settings.xhs_proxy_url:
                proxy = {"server": settings.xhs_proxy_url}
            else:
                proxy = None

            browser = await p.chromium.launch(
                headless=True,
                args=browser_args,
            )
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                ),
                proxy=proxy,
                viewport={"width": 390, "height": 844},
            )

            # Inject cookies
            cookies = self._parse_cookie_string(cookie_str)
            await context.add_cookies(cookies)

            page = await context.new_page()
            search_url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_explore_feed"

            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Extract note data from page
            note_data = await page.evaluate("""
                () => {
                    const notes = [];
                    const items = document.querySelectorAll('.note-item, [class*="note-item"], .search-result-item');
                    items.forEach(item => {
                        const title = item.querySelector('.title, .note-title, h3, a')?.textContent?.trim();
                        const link = item.querySelector('a')?.href;
                        const likes = item.querySelector('.like-count, .count')?.textContent?.trim();
                        if (title || link) {
                            notes.push({ title, link, likes });
                        }
                    });
                    return notes.slice(0, 50);
                }
            """)

            await browser.close()

            for item in note_data[:limit]:
                posts.append(
                    RawPost(
                        platform="xiaohongshu",
                        external_id=None,
                        content_url=item.get("link"),
                        author_handle=None,
                        caption=item.get("title"),
                        hashtags=[keyword],
                        likes=self._parse_count(item.get("likes", "0")),
                        raw_metadata=item,
                    )
                )

        return posts

    async def _apify_fallback(self, keyword: str, limit: int) -> list[RawPost]:
        """Fallback: Apify xiaohongshu-scraper actor."""
        if not settings.apify_api_token:
            return []

        try:
            from apify_client import ApifyClient
            client = ApifyClient(settings.apify_api_token)
            run = client.actor("apify/xiaohongshu-scraper").call(
                run_input={"searchQuery": keyword, "maxResults": limit}
            )
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                return []

            posts = []
            for item in client.dataset(dataset_id).iterate_items():
                posts.append(
                    RawPost(
                        platform="xiaohongshu",
                        external_id=item.get("id"),
                        content_url=item.get("url"),
                        author_handle=item.get("author", {}).get("nickname"),
                        caption=item.get("title") or item.get("desc"),
                        hashtags=item.get("tags", []),
                        likes=item.get("likes", 0),
                        comments=item.get("comments", 0),
                        saves=item.get("collects", 0),
                        raw_metadata={"id": item.get("id")},
                    )
                )
            return posts
        except Exception as e:
            logger.error("XHS Apify fallback also failed: %s", e)
            return []

    def _parse_cookie_string(self, cookie_str: str) -> list[dict]:
        """Parse a cookie string into Playwright cookie format."""
        cookies = []
        for part in cookie_str.split(";"):
            part = part.strip()
            if "=" in part:
                name, _, value = part.partition("=")
                cookies.append({
                    "name": name.strip(),
                    "value": value.strip(),
                    "domain": ".xiaohongshu.com",
                    "path": "/",
                })
        return cookies

    def _parse_count(self, count_str: str) -> int:
        """Parse display counts like '1.2w', '3k' to int."""
        if not count_str:
            return 0
        count_str = str(count_str).strip().lower().replace(",", "")
        try:
            if "w" in count_str:
                return int(float(count_str.replace("w", "")) * 10000)
            if "k" in count_str:
                return int(float(count_str.replace("k", "")) * 1000)
            return int(float(count_str))
        except ValueError:
            return 0
