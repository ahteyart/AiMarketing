"""
Burn a headline onto a marketing image.

Downloads the DALL-E temporary URL, composites a dark gradient band
at the bottom with the attention headline in white, then uploads the
result to MinIO (which also gives a permanent URL — DALL-E URLs expire).
"""

import io
import logging
import textwrap
import uuid

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.config import settings

logger = logging.getLogger(__name__)

# System font candidates — first one found wins.
# WQY ZenHei supports CJK (Chinese/Japanese/Korean) + Latin.
_FONT_PATHS = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
]


def _has_cjk(text: str) -> bool:
    return any("一" <= ch <= "鿿" for ch in text)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    # PIL built-in fallback (tiny but always works)
    return ImageFont.load_default()


def _add_headline(image_bytes: bytes, headline: str) -> bytes:
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = img.size

    font_size = max(32, w // 16)
    font = _load_font(font_size)

    # Wrap text — CJK characters are full-width so use narrower limit
    char_width = font_size if _has_cjk(headline) else font_size * 0.55
    max_chars = max(8, int(w * 0.85 / char_width))
    wrapped = textwrap.fill(headline, width=max_chars)

    # Measure wrapped text block
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = probe.multiline_textbbox((0, 0), wrapped, font=font, spacing=8)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad = int(font_size * 0.9)
    band_h = text_h + pad * 2

    # Dark gradient overlay at the bottom
    band = Image.new("RGBA", (w, band_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for y in range(band_h):
        alpha = int(200 * (y / band_h))   # fades from transparent → opaque
        bd.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))

    img.alpha_composite(band, dest=(0, h - band_h))

    # Text: drop shadow then white
    draw = ImageDraw.Draw(img)
    tx = (w - text_w) // 2
    ty = h - band_h + pad

    shadow_offset = max(2, font_size // 20)
    draw.multiline_text(
        (tx + shadow_offset, ty + shadow_offset),
        wrapped, font=font, fill=(0, 0, 0, 180), spacing=8, align="center",
    )
    draw.multiline_text(
        (tx, ty),
        wrapped, font=font, fill=(255, 255, 255, 255), spacing=8, align="center",
    )

    out = io.BytesIO()
    img.convert("RGB").save(out, format="JPEG", quality=90)
    return out.getvalue()


async def overlay_headline_and_upload(image_url: str, headline: str) -> str | None:
    """
    Download image_url → burn headline → upload to MinIO → return permanent URL.
    Returns None on any error so the caller can fall back to the raw DALL-E URL.
    """
    if not settings.minio_endpoint or not settings.minio_access_key:
        logger.warning("MinIO not configured — skipping headline overlay")
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            raw_bytes = resp.content

        result_bytes = _add_headline(raw_bytes, headline)

        import boto3
        from botocore.client import Config

        s3 = boto3.client(
            "s3",
            endpoint_url=settings.minio_endpoint,
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            config=Config(signature_version="s3v4"),
            use_ssl=settings.minio_use_ssl,
        )
        key = f"generated-images/{uuid.uuid4().hex}.jpg"
        s3.put_object(
            Bucket=settings.minio_bucket,
            Key=key,
            Body=io.BytesIO(result_bytes),
            ContentType="image/jpeg",
            ACL="public-read",
        )
        endpoint = settings.minio_endpoint.rstrip("/")
        url = f"{endpoint}/{settings.minio_bucket}/{key}"
        logger.info("Headline overlay uploaded: %s", url)
        return url

    except Exception as e:
        logger.error("Headline overlay failed: %s", e)
        return None
