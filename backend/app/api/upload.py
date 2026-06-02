from fastapi import APIRouter, UploadFile, File

from app.storage import upload_reference_image

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/reference")
async def upload_reference(file: UploadFile = File(...)):
    """Upload a product / model / shop photo and get back a public URL."""
    url = await upload_reference_image(file)
    return {"url": url, "filename": file.filename}
