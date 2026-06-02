"""
UGC video generation using Higgsfield MCP.
Only triggered on explicit user request (never automatic).
Higgsfield generates authentic, engaging short-form videos.
"""

import logging

logger = logging.getLogger(__name__)


async def generate_video_from_image(
    image_url: str,
    motion_prompt: str,
    duration_seconds: int = 5,
    higgsfield_mcp=None,
) -> dict:
    """
    Generate a short UGC-style video from a static image using Higgsfield MCP.
    Returns job info; caller must poll for completion.
    """
    if higgsfield_mcp is None:
        return {"error": "Higgsfield MCP not available", "job_id": None}

    logger.info("Initiating UGC video generation: duration=%ds via Higgsfield", duration_seconds)

    try:
        result = await higgsfield_mcp.generate_video(
            image_url=image_url,
            prompt=motion_prompt,
            duration=duration_seconds,
        )

        return {
            "job_id": result.get("video_id") or result.get("id"),
            "status": result.get("status", "processing"),
            "video_url": result.get("video_url"),
            "duration_seconds": duration_seconds,
        }

    except Exception as e:
        logger.error("Higgsfield video generation failed: %s", e)
        return {"error": str(e), "job_id": None}


async def get_video_status(job_id: str, higgsfield_mcp=None) -> dict:
    """Poll Higgsfield for video generation status."""
    if higgsfield_mcp is None:
        return {"job_id": job_id, "status": "error", "error": "MCP not available"}

    try:
        result = await higgsfield_mcp.get_video_status(job_id)
        return {
            "job_id": job_id,
            "status": result.get("status"),
            "video_url": result.get("video_url"),
            "progress": result.get("progress", 0),
            "error": result.get("error"),
        }

    except Exception as e:
        logger.error("Failed to get video status: %s", e)
        return {"job_id": job_id, "status": "error", "error": str(e)}


def estimate_cost(duration_seconds: int = 5) -> dict:
    """Return cost estimate before generating."""
    return {
        "provider": "Higgsfield MCP",
        "duration_seconds": duration_seconds,
        "estimated_cost_usd": 0,
        "warning": "Higgsfield video generation will be triggered. No additional cost.",
    }
