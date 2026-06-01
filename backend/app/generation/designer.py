"""
Design generation using Canva MCP.
Creates platform-specific designs using brand templates.
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


async def generate_design(request: DesignRequest, canva_mcp=None) -> DesignResult:
    """
    Generate a design using Canva MCP tools.
    canva_mcp is the Canva MCP client injected at runtime.
    Falls back to placeholder if MCP not available.
    """
    dims = PLATFORM_DIMENSIONS.get(request.platform, {}).get(request.content_type, {})
    if not dims:
        dims = {"width": 1080, "height": 1080, "label": "Square"}

    if canva_mcp is None:
        logger.warning("Canva MCP not available, returning placeholder design")
        return DesignResult(
            design_id=None,
            export_url=None,
            thumbnail_url=None,
            width=dims["width"],
            height=dims["height"],
            platform=request.platform,
            content_type=request.content_type,
        )

    prompt = _build_design_prompt(request, dims)

    try:
        result = await canva_mcp.generate_design(
            title=f"{request.platform} - {request.theme[:50]}",
            prompt=prompt,
            width=dims["width"],
            height=dims["height"],
        )

        design_id = result.get("design", {}).get("id")

        export_url = None
        if design_id:
            export_result = await canva_mcp.export_design(
                design_id=design_id,
                format="PNG",
            )
            export_url = export_result.get("url")

        return DesignResult(
            design_id=design_id,
            export_url=export_url,
            thumbnail_url=result.get("thumbnail_url"),
            width=dims["width"],
            height=dims["height"],
            platform=request.platform,
            content_type=request.content_type,
        )

    except Exception as e:
        logger.error("Canva design generation failed: %s", e)
        return DesignResult(
            design_id=None,
            export_url=None,
            thumbnail_url=None,
            width=dims["width"],
            height=dims["height"],
            platform=request.platform,
            content_type=request.content_type,
        )


def _build_design_prompt(request: DesignRequest, dims: dict) -> str:
    platform_style = {
        "instagram": "clean, aesthetic, high-contrast, lifestyle photography style",
        "facebook": "professional, trustworthy, clear hierarchy, wide format",
        "xiaohongshu": "soft pastel tones, feminine, cozy, aesthetic flat lay style",
    }.get(request.platform, "modern, clean")

    colors = ", ".join(request.brand_colors) if request.brand_colors else "brand appropriate colors"

    return (
        f"Create a {dims.get('label', 'social media')} graphic for: {request.theme}. "
        f"Style: {platform_style}, {request.brand_style}. "
        f"Colors: {colors}. "
        f"Headline text: '{request.copy_attention[:80]}'. "
        f"Dimensions: {dims['width']}x{dims['height']}px. "
        f"No stock photo watermarks. Marketing-ready quality."
    )
