"""
UGC video generation using Higgsfield AI.
Docs: https://cloud.higgsfield.ai
Only triggered on explicit user request (never automatic).
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

HIGGSFIELD_API_BASE = "https://api.higgsfield.ai/v1"


def _headers() -> dict:
    return {
        "X-API-Key": settings.hf_api_key,
        "X-API-Secret": settings.hf_secret,
        "Content-Type": "application/json",
    }


async def generate_video_from_image(
    image_url: str,
    motion_prompt: str,
    duration_seconds: int = 5,
) -> dict:
    """Generate a UGC-style video from an image using Higgsfield."""
    if not settings.hf_api_key or not settings.hf_secret:
        return {"error": "Higgsfield API credentials not configured", "job_id": None}

    logger.info("Starting Higgsfield video generation: %ds", duration_seconds)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{HIGGSFIELD_API_BASE}/video/generate",
                json={
                    "image_url": image_url,
                    "prompt": motion_prompt,
                    "duration": duration_seconds,
                    "aspect_ratio": "9:16",
                },
                headers=_headers(),
            )
            if not resp.is_success:
                logger.error(
                    "Higgsfield %s error — body: %s",
                    resp.status_code,
                    resp.text[:500],
                )
                return {"error": f"Higgsfield API error {resp.status_code}: {resp.text[:200]}", "job_id": None}
            data = resp.json()

        return {
            "job_id": data.get("id") or data.get("job_id"),
            "status": data.get("status", "processing"),
            "video_url": data.get("video_url"),
            "duration_seconds": duration_seconds,
        }

    except Exception as e:
        logger.error("Higgsfield video generation failed: %s", e)
        return {"error": str(e), "job_id": None}


async def get_video_status(job_id: str) -> dict:
    """Poll Higgsfield for video generation status."""
    if not settings.hf_api_key:
        return {"job_id": job_id, "status": "error", "error": "Not configured"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{HIGGSFIELD_API_BASE}/video/{job_id}",
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "job_id": job_id,
            "status": data.get("status"),
            "video_url": data.get("video_url"),
            "progress": data.get("progress", 0),
            "error": data.get("error"),
        }

    except Exception as e:
        logger.error("Higgsfield status check failed: %s", e)
        return {"job_id": job_id, "status": "error", "error": str(e)}


def estimate_cost(duration_seconds: int = 5) -> dict:
    credits = duration_seconds * 10
    usd = credits / 16
    return {
        "provider": "Higgsfield AI",
        "duration_seconds": duration_seconds,
        "estimated_credits": credits,
        "estimated_cost_usd": round(usd, 2),
        "warning": f"~{credits} credits (≈${usd:.2f}). Confirm before proceeding.",
    }
