"""
MinIO (S3-compatible) storage for user-uploaded reference images.
"""

import io
import uuid
import logging
import mimetypes

import boto3
from botocore.client import Config
from fastapi import HTTPException, UploadFile

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_access_key,
        aws_secret_access_key=settings.minio_secret_key,
        config=Config(signature_version="s3v4"),
        use_ssl=settings.minio_use_ssl,
    )


async def upload_reference_image(file: UploadFile) -> str:
    """Upload a reference image to MinIO and return its public URL."""
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {content_type}. Use JPEG, PNG, WebP or GIF.")

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10 MB.")

    ext = mimetypes.guess_extension(content_type) or ".jpg"
    ext = ext.replace(".jpe", ".jpg")
    key = f"reference-images/{uuid.uuid4().hex}{ext}"

    try:
        client = _s3_client()
        client.put_object(
            Bucket=settings.minio_bucket,
            Key=key,
            Body=io.BytesIO(data),
            ContentType=content_type,
            ACL="public-read",
        )
        endpoint = settings.minio_endpoint.rstrip("/")
        return f"{endpoint}/{settings.minio_bucket}/{key}"
    except Exception as e:
        logger.error("MinIO upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Image upload failed. Check storage configuration.")
