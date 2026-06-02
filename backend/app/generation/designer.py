"""
Image generation using OpenAI DALL-E 3.
"""

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"

PLATFORM_SIZE = {
    ("instagram", "image_post"):   "1024x1024",
    ("instagram", "carousel"):     "1024x1024",
    ("instagram", "reel"):         "1024x1792",
    ("instagram", "story"):        "1024x1792",
    ("facebook",  "image_post"):   "1792x1024",
    ("facebook",  "carousel"):     "1024x1024",
    ("xiaohongshu", "image_post"): "1024x1024",
    ("xiaohongshu", "video"):      "1024x1792",
}


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


def _build_prompt(request: DesignRequest) -> str:
    colors = ", ".join(request.brand_colors) if request.brand_colors else "vibrant brand colors"
    return (
        f"Professional {request.platform} marketing image. "
        f"Theme: {request.theme}. "
        f"Headline concept: {request.copy_attention[:120]}. "
        f"Style: {request.brand_style}, {colors}. "
        f"High quality, clean composition, no text overlays."
    )


async def generate_design(request: DesignRequest, **_) -> DesignResult:
    placeholder = DesignResult(
        design_id=None, export_url=None, thumbnail_url=None,
        platform=request.platform, content_type=request.content_type,
    )

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not configured — returning placeholder")
        return placeholder

    size = PLATFORM_SIZE.get((request.platform, request.content_type), "1024x1024")
    prompt = _build_prompt(request)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                OPENAI_IMAGE_URL,
                json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size, "quality": "standard"},
                headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"},
            )
            resp.raise_for_status()
            image_url = resp.json()["data"][0]["url"]

        return DesignResult(
            design_id=None,
            export_url=image_url,
            thumbnail_url=image_url,
            platform=request.platform,
            content_type=request.content_type,
        )

    except Exception as e:
        logger.error("DALL-E image generation failed: %s", e)
        return placeholder
