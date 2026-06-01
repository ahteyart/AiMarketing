import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.export.google_sheets import GoogleDriveUploader, GoogleSheetsExporter
from app.models.calendar_entry import CalendarEntry
from app.models.campaign import Campaign
from app.models.content import GeneratedContent
from app.models.export import SheetExport
from app.workflow.approval import mark_exported

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/export", tags=["export"])

_oauth_state_store: dict[str, dict] = {}

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _flow(state: str | None = None) -> Flow:
    config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uris": [settings.google_redirect_uri],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    kwargs = {"state": state} if state else {}
    return Flow.from_client_config(config, scopes=SCOPES, **kwargs)


@router.get("/google/auth")
async def start_google_auth(campaign_id: str):
    """Initiate Google OAuth2 flow for Sheets + Drive access."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google credentials not configured")
    flow = _flow()
    flow.redirect_uri = settings.google_redirect_uri
    auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    _oauth_state_store[state] = {"campaign_id": campaign_id}
    return {"auth_url": auth_url}


@router.get("/google/callback")
async def google_auth_callback(request: Request):
    """Handle Google OAuth2 callback — returns credentials to frontend."""
    state = request.query_params.get("state")
    code = request.query_params.get("code")
    if not state or state not in _oauth_state_store:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    flow = _flow(state=state)
    flow.redirect_uri = settings.google_redirect_uri
    flow.fetch_token(code=code)
    credentials = flow.credentials
    campaign_id = _oauth_state_store.pop(state, {}).get("campaign_id")
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "campaign_id": campaign_id,
    }


class ExportRequest(BaseModel):
    campaign_id: UUID
    credentials: dict
    spreadsheet_id: str | None = None
    upload_to_drive: bool = True


@router.post("/google")
async def export_to_google(body: ExportRequest, db: AsyncSession = Depends(get_db)):
    """Upload media to Google Drive and export content calendar to Google Sheets."""
    result = await db.execute(
        select(GeneratedContent)
        .where(GeneratedContent.campaign_id == body.campaign_id)
        .where(GeneratedContent.status == "approved")
    )
    approved_items = result.scalars().all()
    if not approved_items:
        raise HTTPException(status_code=400, detail="No approved content found for this campaign")

    campaign = await db.get(Campaign, body.campaign_id)
    campaign_name = campaign.name if campaign else "Campaign"

    # Build export data
    export_data = []
    for item in approved_items:
        calendar_entry = await db.get(CalendarEntry, item.calendar_entry_id) if item.calendar_entry_id else None
        export_data.append({
            "platform": item.platform,
            "content_type": item.content_type,
            "scheduled_date": calendar_entry.scheduled_date.isoformat() if calendar_entry and calendar_entry.scheduled_date else "",
            "theme": calendar_entry.theme if calendar_entry else "",
            "copy_attention": item.copy_attention or "",
            "copy_interest": item.copy_interest or "",
            "copy_desire": item.copy_desire or "",
            "copy_action": item.copy_action or "",
            "copy_text": item.copy_text or "",
            "hashtags": item.hashtags or [],
            "image_url": item.image_url or "",
            "video_url": item.video_url or "",
            "status": item.status,
            "platform_compliance": item.platform_compliance or {},
        })

    drive_folder_url = None

    # Step 1: Upload media to Google Drive
    if body.upload_to_drive:
        try:
            uploader = GoogleDriveUploader(body.credentials)
            export_data, folders = uploader.upload_content_media(campaign_name, export_data)
            drive_folder_url = f"https://drive.google.com/drive/folders/{folders['campaign']}"
            logger.info("Drive upload complete for campaign %s", campaign_name)
        except Exception as e:
            logger.warning("Drive upload failed, continuing with original URLs: %s", e)

    # Step 2: Export to Google Sheets
    try:
        exporter = GoogleSheetsExporter(body.credentials)
        sheet_result = exporter.export_calendar(
            campaign_name=campaign_name,
            content_items=export_data,
            spreadsheet_id=body.spreadsheet_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Sheets export failed: {str(e)}")

    # Record export
    db.add(SheetExport(
        campaign_id=body.campaign_id,
        spreadsheet_id=sheet_result["spreadsheet_id"],
        spreadsheet_url=sheet_result["spreadsheet_url"],
        entry_count=sheet_result["entry_count"],
        status="completed",
    ))

    for item in approved_items:
        try:
            await mark_exported(item.id, db)
        except ValueError:
            pass

    await db.flush()
    return {
        "spreadsheet_url": sheet_result["spreadsheet_url"],
        "spreadsheet_id": sheet_result["spreadsheet_id"],
        "drive_folder_url": drive_folder_url,
        "entry_count": sheet_result["entry_count"],
        "message": f"Exported {sheet_result['entry_count']} items to Google Drive + Sheets",
    }


# Keep legacy endpoint alias
@router.get("/google-sheets/auth")
async def start_google_auth_legacy(campaign_id: str):
    return await start_google_auth(campaign_id)
