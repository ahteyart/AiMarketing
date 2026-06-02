"""
Image generation using OpenAI DALL-E 3.
When a reference image is supplied, GPT-4o vision describes it first
so DALL-E can generate a visually consistent result.
"""

import logging
import re
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"


def _to_ascii_safe(text: str, max_len: int = 120) -> str:
    """Strip non-ASCII characters so DALL-E won't try to render CJK text in the image."""
    ascii_only = re.sub(r"[^\x00-\x7F]+", " ", text).strip()
    ascii_only = re.sub(r"\s+", " ", ascii_only)
    return ascii_only[:max_len] if ascii_only else ""


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


async def _describe_reference_image(image_url: str, headers: dict) -> str:
    """Use GPT-4o vision to get a short description of the reference image."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                OPENAI_CHAT_URL,
                json={
                    "model": "gpt-4o",
                    "max_tokens": 150,
                    "messages": [{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}},
                        {"type": "text", "text": "Describe this product/person/location in 2-3 sentences for marketing use. Focus on visual details, colors, and style."},
                    ]}],
                },
                headers=headers,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning("GPT-4o vision description failed: %s", e)
        return ""


def _build_prompt(request: DesignRequest, reference_description: str = "") -> str:
    colors = ", ".join(request.brand_colors) if request.brand_colors else "vibrant brand colors"
    # Strip non-ASCII to prevent DALL-E from rendering CJK glyphs in the image
    safe_theme = _to_ascii_safe(request.theme, 100)
    safe_attention = _to_ascii_safe(request.copy_attention, 100)
    concept = safe_attention or safe_theme or "lifestyle marketing"
    base = (
        f"Professional {request.platform} marketing photo, clean studio composition. "
        f"Theme: {safe_theme or 'lifestyle product'}. "
        f"Concept: {concept}. "
        f"Style: {request.brand_style}, {colors}. "
        f"High-quality photography, no text, no words, no letters in the image."
    )
    if reference_description:
        base += f" Featured subject: {reference_description}"
    return base


async def generate_design(request: DesignRequest, **_) -> DesignResult:
    placeholder = DesignResult(
        design_id=None, export_url=None, thumbnail_url=None,
        platform=request.platform, content_type=request.content_type,
    )

    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not configured — returning placeholder")
        return placeholder

    headers = {"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}
    size = PLATFORM_SIZE.get((request.platform, request.content_type), "1024x1024")

    reference_description = ""
    if request.product_image_url:
        reference_description = await _describe_reference_image(request.product_image_url, headers)

    prompt = _build_prompt(request, reference_description)

    logger.info("DALL-E prompt (%s chars): %s", len(prompt), prompt[:200])

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                OPENAI_IMAGE_URL,
                json={"model": "dall-e-3", "prompt": prompt, "n": 1, "size": size, "quality": "standard"},
                headers=headers,
            )
            if not resp.is_success:
                logger.error(
                    "DALL-E %s error — body: %s",
                    resp.status_code,
                    resp.text[:500],
                )
                return placeholder
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
