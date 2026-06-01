import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || (typeof window !== "undefined" && window.location.hostname !== "localhost" ? "" : "http://localhost:8000");

export const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { "Content-Type": "application/json" },
});

// ── Campaigns ──────────────────────────────────────────────
export const getCampaigns = () => api.get("/campaigns/").then((r) => r.data);
export const createCampaign = (data: object) => api.post("/campaigns/", data).then((r) => r.data);
export const getCampaign = (id: string) => api.get(`/campaigns/${id}`).then((r) => r.data);
export const updateCampaign = (id: string, data: object) => api.patch(`/campaigns/${id}`, data).then((r) => r.data);

// ── 30-Day Planner ─────────────────────────────────────────
export const getCalendar = (campaignId: string, platform?: string) =>
  api.get(`/planner/${campaignId}/calendar`, { params: { platform } }).then((r) => r.data);
export const generateCalendar = (campaignId: string, startDate?: string, days: number = 30, language?: string) =>
  api.post("/planner/generate", { campaign_id: campaignId, start_date: startDate, days, language }).then((r) => r.data);
export const updateCalendarEntry = (entryId: string, data: object) =>
  api.patch(`/planner/entry/${entryId}`, data).then((r) => r.data);

// ── Content ────────────────────────────────────────────────
export const getContent = (campaignId: string, status?: string) =>
  api.get(`/content/${campaignId}`, { params: { status } }).then((r) => r.data);
export const getContentItem = (contentId: string) =>
  api.get(`/content/item/${contentId}`).then((r) => r.data);
export const generateContent = (calendarEntryId: string, generateImage = true) =>
  api.post("/content/generate", { calendar_entry_id: calendarEntryId, generate_image: generateImage }).then((r) => r.data);
export const updateContent = (contentId: string, data: object) =>
  api.patch(`/content/item/${contentId}`, data).then((r) => r.data);
export const requestVideoGeneration = (contentId: string, confirmed = false) =>
  api.post(`/content/item/${contentId}/generate-video`, null, { params: { confirmed } }).then((r) => r.data);

// ── Approvals ──────────────────────────────────────────────
export const getPendingApprovals = (campaignId?: string) =>
  api.get("/approvals/", { params: { campaign_id: campaignId } }).then((r) => r.data);
export const approveContent = (contentId: string, editedCopy?: string, notes?: string) =>
  api.post(`/approvals/${contentId}/approve`, { edited_copy: editedCopy, notes }).then((r) => r.data);
export const rejectContent = (contentId: string, reason: string) =>
  api.post(`/approvals/${contentId}/reject`, { reason }).then((r) => r.data);

// ── Google Drive + Sheets Export ───────────────────────────
export const startGoogleAuth = (campaignId: string) =>
  api.get("/export/google/auth", { params: { campaign_id: campaignId } }).then((r) => r.data);
export const exportToGoogle = (campaignId: string, credentials: object, spreadsheetId?: string) =>
  api.post("/export/google", { campaign_id: campaignId, credentials, spreadsheet_id: spreadsheetId, upload_to_drive: true }).then((r) => r.data);
