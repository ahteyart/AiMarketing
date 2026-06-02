"""
Image generation using OpenAI DALL-E 3.
When a reference image is supplied, GPT-4o vision describes it first
so DALL-E can generate a visually consistent result.
"""

import logging
import re
import uuid
from dataclasses import dataclass

import httpx

from app.config import settings
from app.generation.text_overlay import overlay_headline_and_upload

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


async def _call_dalle(prompt: str, size: str, headers: dict, model: str = "dall-e-3") -> str | None:
    """Call DALL-E and return the image URL, or None on failure."""
    # DALL-E 2 only supports up to 1024x1024
    if model == "dall-e-2" and size not in ("256x256", "512x512", "1024x1024"):
        size = "1024x1024"
    body: dict = {"model": model, "prompt": prompt, "n": 1, "size": size}
    if model == "dall-e-3":
        body["quality"] = "standard"
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(OPENAI_IMAGE_URL, json=body, headers=headers)
        if not resp.is_success:
            logger.error("DALL-E %s (%s) error — body: %s", model, resp.status_code, resp.text[:500])
            return None
        return resp.json()["data"][0]["url"]
    except Exception as e:
        logger.error("DALL-E %s exception: %s", model, e)
        return None


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

    # Try DALL-E 3 first; fall back to DALL-E 2 if the account doesn't have access
    dalle_url = await _call_dalle(prompt, size, headers, model="dall-e-3")
    if not dalle_url:
        logger.info("DALL-E 3 failed — retrying with dall-e-2")
        dalle_url = await _call_dalle(prompt, size, headers, model="dall-e-2")
    if not dalle_url:
        logger.warning("DALL-E unavailable — using stock photo placeholder for %s/%s", request.platform, request.content_type)
        seed = uuid.uuid4().hex[:10]
        dalle_url = f"https://picsum.photos/seed/{seed}/1024/1024"

    # Use ASCII-safe headline for overlay (CJK text can't render without CJK fonts)
    safe_headline = _to_ascii_safe(request.copy_attention or request.theme, 120)
    if not safe_headline:
        safe_headline = f"{request.platform.title()} Marketing"
    final_url = await overlay_headline_and_upload(dalle_url, safe_headline) or dalle_url

    return DesignResult(
        design_id=None,
        export_url=final_url,
        thumbnail_url=final_url,
        platform=request.platform,
        content_type=request.content_type,
    )
