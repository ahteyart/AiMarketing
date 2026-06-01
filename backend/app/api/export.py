import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.export.google_sheets import GoogleSheetsExporter
from app.models.content import GeneratedContent
from app.models.export import SheetExport
from app.workflow.approval import mark_exported

router = APIRouter(prefix="/export", tags=["export"])

_oauth_state_store: dict[str, dict] = {}  # In production, use Redis


@router.get("/google-sheets/auth")
async def start_google_auth(campaign_id: str):
    """Initiate Google OAuth2 flow."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uris": [settings.google_redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"],
    )
    flow.redirect_uri = settings.google_redirect_uri
    auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
    _oauth_state_store[state] = {"campaign_id": campaign_id}
    return {"auth_url": auth_url}


@router.get("/google-sheets/callback")
async def google_auth_callback(request: Request):
    """Handle Google OAuth2 callback."""
    state = request.query_params.get("state")
    code = request.query_params.get("code")

    if not state or state not in _oauth_state_store:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uris": [settings.google_redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"],
        state=state,
    )
    flow.redirect_uri = settings.google_redirect_uri
    flow.fetch_token(code=code)

    credentials = flow.credentials
    campaign_id = _oauth_state_store.pop(state, {}).get("campaign_id")

    # Return credentials to frontend (in production, store encrypted in DB/session)
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "campaign_id": campaign_id,
    }


class ExportRequest(BaseModel):
    campaign_id: UUID
    credentials: dict  # Google OAuth credentials from callback
    spreadsheet_id: str | None = None  # Append to existing sheet if provided
    platforms: list[str] | None = None  # None = all platforms


@router.post("/google-sheets")
async def export_to_sheets(body: ExportRequest, db: AsyncSession = Depends(get_db)):
    """Export approved content calendar to Google Sheets."""
    query = (
        select(GeneratedContent)
        .where(GeneratedContent.campaign_id == body.campaign_id)
        .where(GeneratedContent.status == "approved")
    )
    if body.platforms:
        query = query.where(GeneratedContent.platform.in_(body.platforms))
    result = await db.execute(query)
    approved_items = result.scalars().all()

    if not approved_items:
        raise HTTPException(status_code=400, detail="No approved content found for this campaign")

    # Get campaign name
    from app.models.campaign import Campaign
    campaign = await db.get(Campaign, body.campaign_id)

    # Build export data: join with calendar entry for scheduled_date
    export_data = []
    for item in approved_items:
        calendar_entry = await db.get(
            __import__("app.models.calendar_entry", fromlist=["CalendarEntry"]).CalendarEntry,
            item.calendar_entry_id,
        ) if item.calendar_entry_id else None

        export_data.append({
            "platform": item.platform,
            "content_type": item.content_type,
            "scheduled_date": calendar_entry.scheduled_date.isoformat() if calendar_entry and calendar_entry.scheduled_date else "",
            "theme": calendar_entry.theme if calendar_entry else "",
            "title": (item.generation_metadata or {}).get("xhs_title", ""),
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

    # Export to Google Sheets
    try:
        exporter = GoogleSheetsExporter(body.credentials)
        sheet_result = exporter.export_calendar(
            campaign_name=campaign.name if campaign else "Campaign",
            content_items=export_data,
            spreadsheet_id=body.spreadsheet_id,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google Sheets export failed: {str(e)}")

    # Record export
    export_record = SheetExport(
        campaign_id=body.campaign_id,
        spreadsheet_id=sheet_result["spreadsheet_id"],
        spreadsheet_url=sheet_result["spreadsheet_url"],
        entry_count=sheet_result["entry_count"],
        status="completed",
    )
    db.add(export_record)

    # Mark content as exported
    for item in approved_items:
        try:
            await mark_exported(item.id, db)
        except ValueError:
            pass  # Already exported, skip

    await db.flush()
    return {
        "spreadsheet_url": sheet_result["spreadsheet_url"],
        "spreadsheet_id": sheet_result["spreadsheet_id"],
        "entry_count": sheet_result["entry_count"],
        "message": "Successfully exported to Google Sheets",
    }
