"""
Google Sheets exporter for the 30-day content calendar.
Each campaign gets a Spreadsheet with one tab per platform.
Approved content is exported with full AIDA copy + media links + compliance status.
"""

import logging
from datetime import datetime

import gspread
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]

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
    "标题（小红书）",
    "[A] 吸引注意",
    "[I] 激发兴趣",
    "[D] 引发欲望",
    "[A] 行动号召",
    "完整文案",
    "话题标签",
    "图片链接",
    "视频链接",
    "状态",
    "字数",
    "标签数",
    "合规检查",
    "备注",
]


class GoogleSheetsExporter:
    def __init__(self, credentials_dict: dict):
        """
        credentials_dict: OAuth2 token dict obtained after user authorizes.
        """
        self.creds = Credentials(
            token=credentials_dict.get("access_token"),
            refresh_token=credentials_dict.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=credentials_dict.get("client_id"),
            client_secret=credentials_dict.get("client_secret"),
            scopes=SCOPES,
        )
        self.gc = gspread.authorize(self.creds)

    def export_calendar(
        self,
        campaign_name: str,
        content_items: list[dict],
        spreadsheet_id: str | None = None,
    ) -> dict:
        """
        Export all approved content to a Google Spreadsheet.
        Creates a new spreadsheet if spreadsheet_id is None.
        Returns {spreadsheet_id, spreadsheet_url, entry_count}.
        """
        if spreadsheet_id:
            spreadsheet = self.gc.open_by_key(spreadsheet_id)
        else:
            title = f"{campaign_name} — 内容日历 {datetime.now().strftime('%Y-%m')}"
            spreadsheet = self.gc.create(title)
            # Share with anyone who has the link (view)
            spreadsheet.share(None, perm_type="anyone", role="reader")

        # Group content by platform
        by_platform: dict[str, list[dict]] = {}
        for item in content_items:
            p = item.get("platform", "unknown")
            by_platform.setdefault(p, []).append(item)

        total_entries = 0
        for platform, items in by_platform.items():
            sheet = self._get_or_create_sheet(spreadsheet, platform)
            rows = self._build_rows(items, platform)
            self._write_rows(sheet, rows, platform)
            total_entries += len(rows)

        # Remove default "Sheet1" if it exists
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
            # Write header row
            sheet.append_row(SHEET_COLUMNS, value_input_option="RAW")
            self._format_header(sheet, platform)
            return sheet

    def _build_rows(self, items: list[dict], platform: str) -> list[list]:
        rows = []
        sorted_items = sorted(items, key=lambda x: x.get("scheduled_date") or "")
        for item in sorted_items:
            compliance = item.get("platform_compliance") or {}
            hashtags = ", ".join(item.get("hashtags") or [])
            compliance_status = "✅ 通过" if compliance.get("passed") else "❌ " + "; ".join(compliance.get("issues", []))

            row = [
                item.get("scheduled_date", ""),
                item.get("platform", "").title(),
                item.get("content_type", ""),
                item.get("theme", ""),
                item.get("title", "") if platform == "xiaohongshu" else "",
                item.get("copy_attention", ""),
                item.get("copy_interest", ""),
                item.get("copy_desire", ""),
                item.get("copy_action", ""),
                item.get("copy_text", ""),
                hashtags,
                item.get("image_url", ""),
                item.get("video_url", ""),
                item.get("status", "").replace("_", " ").title(),
                compliance.get("char_count", len(item.get("copy_text") or "")),
                compliance.get("hashtag_count", len(item.get("hashtags") or [])),
                compliance_status,
                "",  # 备注 — blank for user to fill
            ]
            rows.append(row)
        return rows

    def _write_rows(self, sheet, rows: list[list], platform: str):
        if not rows:
            return
        start_row = len(sheet.get_all_values()) + 1
        sheet.append_rows(rows, value_input_option="RAW")

        # Color-code status column (column 14 = index 13)
        for i, row in enumerate(rows):
            status_raw = (row[13] or "").lower().replace(" ", "_")
            color = STATUS_COLORS.get(status_raw, STATUS_COLORS["draft"])
            row_idx = start_row + i
            sheet.format(
                f"A{row_idx}:R{row_idx}",
                {"backgroundColor": color},
            )

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
        # Freeze header row
        sheet.freeze(rows=1)
