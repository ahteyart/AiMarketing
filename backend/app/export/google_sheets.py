"""
Google Sheets + Google Drive exporter for the 30-day content calendar.
Drive: uploads approved images/videos into AI Marketing/{Campaign}/Images|Videos folders.
Sheets: creates per-platform tabs with AIDA copy + Google Drive links.
"""

import io
import logging
from datetime import datetime

import gspread
import httpx
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

PLATFORM_COLORS = {
    "instagram": {"red": 0.94, "green": 0.39, "blue": 0.63},
    "facebook": {"red": 0.26, "green": 0.40, "blue": 0.70},
    "xiaohongshu": {"red": 0.95, "green": 0.26, "blue": 0.21},
}

STATUS_COLORS = {
    "approved": {"red": 0.72, "green": 0.88, "blue": 0.72},
    "pending_review": {"red": 1.0, "green": 0.95, "blue": 0.70},
    "draft": {"red": 0.90, "green": 0.90, "blue": 0.90},
}

SHEET_COLUMNS = [
    "日期",
    "平台",
    "内容类型",
    "主题/话题",
    "[A] 吸引注意",
    "[I] 激发兴趣",
    "[D] 引发欲望",
    "[A] 行动号召",
    "完整文案",
    "话题标签",
    "图片 (Google Drive)",
    "视频 (Google Drive)",
    "状态",
    "字数",
    "标签数",
    "合规检查",
    "备注",
]


def _make_credentials(credentials_dict: dict) -> Credentials:
    return Credentials(
        token=credentials_dict.get("access_token"),
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=credentials_dict.get("client_id"),
        client_secret=credentials_dict.get("client_secret"),
        scopes=SCOPES,
    )


class GoogleDriveUploader:
    """Uploads images and videos to Google Drive under AI Marketing/{campaign}/ folder."""

    def __init__(self, credentials_dict: dict):
        creds = _make_credentials(credentials_dict)
        self.service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def _create_folder(self, name: str, parent_id: str | None = None) -> str:
        metadata: dict = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            metadata["parents"] = [parent_id]
        folder = self.service.files().create(body=metadata, fields="id").execute()
        return folder["id"]

    def _find_folder(self, name: str, parent_id: str | None = None) -> str | None:
        q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            q += f" and '{parent_id}' in parents"
        results = self.service.files().list(q=q, fields="files(id)", pageSize=1).execute()
        files = results.get("files", [])
        return files[0]["id"] if files else None

    def setup_campaign_folders(self, campaign_name: str) -> dict:
        """Create (or reuse) AI Marketing / {campaign} / Images + Videos folders."""
        root_id = self._find_folder("AI Marketing") or self._create_folder("AI Marketing")
        safe_name = campaign_name[:50]
        campaign_id = self._find_folder(safe_name, root_id) or self._create_folder(safe_name, root_id)
        images_id = self._find_folder("Images", campaign_id) or self._create_folder("Images", campaign_id)
        videos_id = self._find_folder("Videos", campaign_id) or self._create_folder("Videos", campaign_id)
        return {"root": root_id, "campaign": campaign_id, "images": images_id, "videos": videos_id}

    def _make_public(self, file_id: str) -> None:
        try:
            self.service.permissions().create(
                fileId=file_id,
                body={"role": "reader", "type": "anyone"},
            ).execute()
        except Exception as e:
            logger.warning("Could not make file public: %s", e)

    def upload_from_url(self, url: str, filename: str, mime_type: str, folder_id: str) -> str:
        """Download file from URL and upload to Drive. Returns web view link or original URL on failure."""
        if not url:
            return ""
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
                content = response.content
        except Exception as e:
            logger.warning("Could not download %s: %s — using original URL", url, e)
            return url

        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
        file = self.service.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id,webViewLink",
        ).execute()
        self._make_public(file["id"])
        return file.get("webViewLink", url)

    def upload_content_media(self, campaign_name: str, content_items: list[dict]) -> tuple[list[dict], dict]:
        """
        For each content item, upload image_url and video_url to Drive.
        Returns updated content_items with drive_image_url and drive_video_url fields.
        """
        folders = self.setup_campaign_folders(campaign_name)
        updated = []
        for i, item in enumerate(content_items):
            updated_item = dict(item)
            platform = item.get("platform", "unknown")
            date_str = (item.get("scheduled_date") or datetime.now().strftime("%Y%m%d")).replace("-", "")

            if item.get("image_url"):
                img_filename = f"{date_str}_{platform}_{i+1}_image.jpg"
                try:
                    updated_item["drive_image_url"] = self.upload_from_url(
                        item["image_url"], img_filename, "image/jpeg", folders["images"]
                    )
                    logger.info("Uploaded image to Drive: %s", img_filename)
                except Exception as e:
                    logger.warning("Image upload failed for item %d: %s", i, e)
                    updated_item["drive_image_url"] = item["image_url"]

            if item.get("video_url"):
                vid_filename = f"{date_str}_{platform}_{i+1}_video.mp4"
                try:
                    updated_item["drive_video_url"] = self.upload_from_url(
                        item["video_url"], vid_filename, "video/mp4", folders["videos"]
                    )
                    logger.info("Uploaded video to Drive: %s", vid_filename)
                except Exception as e:
                    logger.warning("Video upload failed for item %d: %s", i, e)
                    updated_item["drive_video_url"] = item["video_url"]

            updated.append(updated_item)
        return updated, folders


class GoogleSheetsExporter:
    def __init__(self, credentials_dict: dict):
        creds = _make_credentials(credentials_dict)
        self.gc = gspread.authorize(creds)

    def export_calendar(
        self,
        campaign_name: str,
        content_items: list[dict],
        spreadsheet_id: str | None = None,
    ) -> dict:
        if spreadsheet_id:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
        else:
            title = f"{campaign_name} — 内容日历 {datetime.now().strftime('%Y-%m')}"
            spreadsheet = self.gc.create(title)
            spreadsheet.share(None, perm_type="anyone", role="reader")

        by_platform: dict[str, list[dict]] = {}
        for item in content_items:
            p = item.get("platform", "unknown")
            by_platform.setdefault(p, []).append(item)

        total_entries = 0
        for platform, items in by_platform.items():
            sheet = self._get_or_create_sheet(spreadsheet, platform)
            rows = self._build_rows(items, platform)
            self._write_rows(sheet, rows)
            total_entries += len(rows)

        try:
            default_sheet = spreadsheet.worksheet("Sheet1")
            if len(spreadsheet.worksheets()) > 1:
                spreadsheet.del_worksheet(default_sheet)
        except gspread.exceptions.WorksheetNotFound:
            pass

        return {
            "spreadsheet_id": spreadsheet.id,
            "spreadsheet_url": spreadsheet.url,
            "entry_count": total_entries,
        }

    def _get_or_create_sheet(self, spreadsheet, platform: str):
        display_names = {
            "instagram": "📸 Instagram",
            "facebook": "👥 Facebook",
            "xiaohongshu": "📕 小红书",
        }
        sheet_title = display_names.get(platform, platform.title())
        try:
            return spreadsheet.worksheet(sheet_title)
        except gspread.exceptions.WorksheetNotFound:
            sheet = spreadsheet.add_worksheet(title=sheet_title, rows=200, cols=len(SHEET_COLUMNS))
            sheet.append_row(SHEET_COLUMNS, value_input_option="RAW")
            self._format_header(sheet, platform)
            return sheet

    def _build_rows(self, items: list[dict], platform: str) -> list[list]:
        rows = []
        for item in sorted(items, key=lambda x: x.get("scheduled_date") or ""):
            compliance = item.get("platform_compliance") or {}
            hashtags = ", ".join(item.get("hashtags") or [])
            compliance_status = "✅ 通过" if compliance.get("passed") else "❌ " + "; ".join(compliance.get("issues", []))
            row = [
                item.get("scheduled_date", ""),
                item.get("platform", "").title(),
                item.get("content_type", ""),
                item.get("theme", ""),
                item.get("copy_attention", ""),
                item.get("copy_interest", ""),
                item.get("copy_desire", ""),
                item.get("copy_action", ""),
                item.get("copy_text", ""),
                hashtags,
                item.get("drive_image_url") or item.get("image_url", ""),
                item.get("drive_video_url") or item.get("video_url", ""),
                item.get("status", "").replace("_", " ").title(),
                compliance.get("char_count", len(item.get("copy_text") or "")),
                compliance.get("hashtag_count", len(item.get("hashtags") or [])),
                compliance_status,
                "",
            ]
            rows.append(row)
        return rows

    def _write_rows(self, sheet, rows: list[list]):
        if not rows:
            return
        start_row = len(sheet.get_all_values()) + 1
        sheet.append_rows(rows, value_input_option="RAW")
        for i, row in enumerate(rows):
            status_raw = (row[12] or "").lower().replace(" ", "_")
            color = STATUS_COLORS.get(status_raw, STATUS_COLORS["draft"])
            row_idx = start_row + i
            sheet.format(f"A{row_idx}:{chr(65 + len(SHEET_COLUMNS) - 1)}{row_idx}", {"backgroundColor": color})

    def _format_header(self, sheet, platform: str):
        color = PLATFORM_COLORS.get(platform, {"red": 0.5, "green": 0.5, "blue": 0.5})
        sheet.format(
            f"A1:{chr(65 + len(SHEET_COLUMNS) - 1)}1",
            {
                "backgroundColor": color,
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER",
            },
        )
        sheet.freeze(rows=1)
