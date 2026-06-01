"""
UGC video generation using Runway ML.
Only triggered on explicit user request (never automatic) due to cost.
Cost guard: $0.05/second minimum 5s = ~$0.25/video.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"


async def generate_video_from_image(
    image_url: str,
    motion_prompt: str,
    duration_seconds: int = 5,
) -> dict:
    """
    Generate a short UGC-style video from a static image using Runway Gen-3 Alpha.
    Returns job info; caller must poll for completion.
    """
    if not settings.runway_api_key:
        return {"error": "Runway API key not configured", "job_id": None}

    estimated_cost = duration_seconds * 0.05
    logger.info("Initiating video generation: duration=%ds, estimated_cost=$%.2f", duration_seconds, estimated_cost)

    payload = {
        "model": "gen3a_turbo",
        "promptImage": image_url,
        "promptText": motion_prompt,
        "duration": duration_seconds,
        "ratio": "9:16",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{RUNWAY_API_BASE}/image_to_video",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.runway_api_key}",
                "X-Runway-Version": "2024-11-06",
            },
        )
        response.raise_for_status()
        data = response.json()

    return {
        "job_id": data.get("id"),
        "status": data.get("status", "pending"),
        "estimated_cost_usd": estimated_cost,
        "duration_seconds": duration_seconds,
    }


async def get_video_status(job_id: str) -> dict:
    """Poll Runway for video generation status."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{RUNWAY_API_BASE}/tasks/{job_id}",
            headers={
                "Authorization": f"Bearer {settings.runway_api_key}",
                "X-Runway-Version": "2024-11-06",
            },
        )
        response.raise_for_status()
        data = response.json()

    return {
        "job_id": job_id,
        "status": data.get("status"),  # PENDING | RUNNING | SUCCEEDED | FAILED
        "video_url": data.get("output", [None])[0] if data.get("status") == "SUCCEEDED" else None,
        "progress": data.get("progressRatio", 0),
        "error": data.get("failure"),
    }


def estimate_cost(duration_seconds: int = 5) -> dict:
    """Return cost estimate before generating."""
    cost = duration_seconds * 0.05
    return {
        "provider": "Runway ML Gen-3 Turbo",
        "duration_seconds": duration_seconds,
        "estimated_cost_usd": cost,
        "warning": f"This will cost approximately ${cost:.2f}. Confirm before proceeding.",
    }
