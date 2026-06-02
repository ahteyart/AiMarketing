"""
Image generation using Canva Connect API.
Docs: https://www.canva.com/developers/docs/connect/
"""

import asyncio
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

CANVA_API_BASE = "https://api.canva.com/rest/v1"

PLATFORM_DESIGN_TYPE = {
    ("instagram", "image_post"): "instagram_post",
    ("instagram", "carousel"):   "instagram_post",
    ("instagram", "reel"):       "your_story",
    ("instagram", "story"):      "your_story",
    ("facebook",  "image_post"): "facebook_post",
    ("facebook",  "carousel"):   "facebook_post",
    ("xiaohongshu", "image_post"): "poster",
    ("xiaohongshu", "video"):      "your_story",
}

from dataclasses import dataclass


@dataclass
class DesignRequest:
    platform: str
    content_type: str
    theme: str
    copy_attention: str
    brand_style: str = "modern"
    brand_colors: list[str] | None = None
    product_image_url: str | None = None


@dataclass
class DesignResult:
    design_id: str | None
    export_url: str | None
    thumbnail_url: str | None
    platform: str
    content_type: str


async def _get_canva_token() -> str | None:
    """Get Canva access token via client credentials OAuth flow."""
    if not settings.canva_client_id or not settings.canva_client_secret:
        return None
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{CANVA_API_BASE}/oauth/token",
            data={"grant_type": "client_credentials", "scope": "design:content:write design:content:read"},
            auth=(settings.canva_client_id, settings.canva_client_secret),
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


async def generate_design(request: DesignRequest, **_) -> DesignResult:
    """
    Generate a Canva design via the Connect API.
    Falls back to placeholder if credentials are not configured.
    """
    placeholder = DesignResult(
        design_id=None, export_url=None, thumbnail_url=None,
        platform=request.platform, content_type=request.content_type,
    )

    token = await _get_canva_token()
    if not token:
        logger.warning("Canva credentials not configured — returning placeholder")
        return placeholder

    design_type = PLATFORM_DESIGN_TYPE.get(
        (request.platform, request.content_type), "poster"
    )

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 1. Create design
            create_resp = await client.post(
                f"{CANVA_API_BASE}/designs",
                json={"design_type": {"type": "preset", "name": design_type},
                      "title": f"{request.platform} — {request.theme[:50]}"},
                headers=headers,
            )
            create_resp.raise_for_status()
            design_id = create_resp.json()["design"]["id"]

            # 2. Start PNG export
            export_resp = await client.post(
                f"{CANVA_API_BASE}/exports",
                json={"design_id": design_id, "format": {"type": "png", "export_quality": "regular"}},
                headers=headers,
            )
            export_resp.raise_for_status()
            job_id = export_resp.json()["job"]["id"]

            # 3. Poll until done (max 30s)
            export_url = None
            for _ in range(30):
                await asyncio.sleep(1)
                poll = await client.get(f"{CANVA_API_BASE}/exports/{job_id}", headers=headers)
                data = poll.json().get("job", {})
                if data.get("status") == "success":
                    export_url = data.get("urls", [None])[0]
                    break
                if data.get("status") == "failed":
                    logger.error("Canva export failed: %s", data)
                    break

        return DesignResult(
            design_id=design_id,
            export_url=export_url,
            thumbnail_url=export_url,
            platform=request.platform,
            content_type=request.content_type,
        )

    except Exception as e:
        logger.error("Canva design generation failed: %s", e)
        return placeholder
