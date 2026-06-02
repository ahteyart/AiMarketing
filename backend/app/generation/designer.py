"""
Image generation using Higgsfield MCP.
Generates AI-powered marketing images for social media platforms.
"""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PLATFORM_DIMENSIONS = {
    "instagram": {
        "image_post": {"width": 1080, "height": 1350, "label": "Instagram Feed 4:5"},
        "carousel": {"width": 1080, "height": 1080, "label": "Instagram Carousel 1:1"},
        "reel": {"width": 1080, "height": 1920, "label": "Instagram Reel 9:16"},
        "story": {"width": 1080, "height": 1920, "label": "Instagram Story 9:16"},
    },
    "facebook": {
        "image_post": {"width": 1200, "height": 630, "label": "Facebook Post 1.91:1"},
        "video": {"width": 1280, "height": 720, "label": "Facebook Video 16:9"},
        "carousel": {"width": 1080, "height": 1080, "label": "Facebook Carousel 1:1"},
    },
    "xiaohongshu": {
        "image_post": {"width": 1080, "height": 1440, "label": "小红书图文 3:4"},
        "video": {"width": 1080, "height": 1920, "label": "小红书视频 9:16"},
    },
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
    width: int
    height: int
    platform: str
    content_type: str


async def generate_design(request: DesignRequest, higgsfield_mcp=None) -> DesignResult:
    """
    Generate an image using Higgsfield MCP.
    higgsfield_mcp is the Higgsfield MCP client injected at runtime.
    Falls back to placeholder if MCP not available.
    """
    dims = PLATFORM_DIMENSIONS.get(request.platform, {}).get(request.content_type, {})
    if not dims:
        dims = {"width": 1080, "height": 1080, "label": "Square"}

    if higgsfield_mcp is None:
        logger.warning("Higgsfield MCP not available, returning placeholder design")
        return DesignResult(
            design_id=None,
            export_url=None,
            thumbnail_url=None,
            width=dims["width"],
            height=dims["height"],
            platform=request.platform,
            content_type=request.content_type,
        )

    prompt = _build_image_prompt(request, dims)

    try:
        result = await higgsfield_mcp.generate_image(
            prompt=prompt,
            width=dims["width"],
            height=dims["height"],
        )

        image_url = result.get("image_url")

        return DesignResult(
            design_id=result.get("image_id"),
            export_url=image_url,
            thumbnail_url=image_url,
            width=dims["width"],
            height=dims["height"],
            platform=request.platform,
            content_type=request.content_type,
        )

    except Exception as e:
        logger.error("Higgsfield image generation failed: %s", e)
        return DesignResult(
            design_id=None,
            export_url=None,
            thumbnail_url=None,
            width=dims["width"],
            height=dims["height"],
            platform=request.platform,
            content_type=request.content_type,
        )


def _build_image_prompt(request: DesignRequest, dims: dict) -> str:
    platform_style = {
        "instagram": "clean aesthetic, high-contrast, lifestyle photography, vibrant colors",
        "facebook": "professional trustworthy design, clear visual hierarchy, engaging",
        "xiaohongshu": "soft pastel tones, feminine aesthetic, cozy flat lay style, beautiful lighting",
    }.get(request.platform, "modern clean aesthetic")

    colors = ", ".join(request.brand_colors) if request.brand_colors else "natural brand colors"

    return (
        f"Generate a {dims.get('label', 'social media')} marketing image. "
        f"Theme: {request.theme}. "
        f"Headline: '{request.copy_attention[:60]}'. "
        f"Style: {platform_style}, {request.brand_style}. "
        f"Colors: {colors}. "
        f"Professional, marketing-ready quality. No text overlays, no watermarks. "
        f"Aspect ratio: {dims['width']}x{dims['height']}px."
    )
