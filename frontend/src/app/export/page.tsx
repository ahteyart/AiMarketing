"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { FileSpreadsheet, FolderOpen, CheckCircle, Upload } from "lucide-react";

export default function ExportPage() {
  const [campaignId, setCampaignId] = useState("");
  const [credentials, setCredentials] = useState<object | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState("");

  const handleGoogleAuth = async () => {
    if (!campaignId) return alert("请先输入 Campaign ID");
    try {
      const { data } = await api.get("/export/google/auth", { params: { campaign_id: campaignId } });
      window.open(data.auth_url, "_blank", "width=600,height=700");
      alert("请在弹出窗口完成 Google 授权，授权完成后将 callback 返回的 JSON 粘贴到下方");
    } catch {
      alert("请先在 Railway 配置 GOOGLE_CLIENT_ID 和 GOOGLE_CLIENT_SECRET");
    }
  };

  const handleExport = async () => {
    if (!credentials) return alert("请先完成 Google 授权");
    if (!campaignId) return alert("请先输入 Campaign ID");
    setLoading(true);
    setStep("上传图片/视频到 Google Drive...");
    try {
      const { data } = await api.post("/export/google", {
        campaign_id: campaignId,
        credentials,
        upload_to_drive: true,
      });
      setResult(data);
      setStep("");
    } catch (e: any) {
      alert(e.response?.data?.detail || "导出失败");
      setStep("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">导出到 Google Drive & Sheets</h1>
        <p className="text-sm text-gray-500 mt-0.5">批准的图片/视频上传至 Google Drive，文案日历写入 Google Sheets</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
        {/* Campaign ID */}
        <div>
          <label className="text-sm font-semibold text-gray-700 block mb-2">Campaign ID</label>
          <input
            type="text"
            value={campaignId}
            onChange={(e) => setCampaignId(e.target.value)}
            placeholder="从概览页复制 Campaign ID"
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-300"
          />
        </div>

        {/* Step 1: Google Auth */}
        <div>
          <div className="text-sm font-semibold text-gray-700 mb-3">① Google 授权（Sheets + Drive）</div>
          <button
            onClick={handleGoogleAuth}
            className="flex items-center gap-2 text-sm px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <img src="https://www.google.com/favicon.ico" alt="" className="w-4 h-4" />
            连接 Google 账号
          </button>
          <div className="mt-3">
            <label className="text-xs text-gray-500 block mb-1">授权完成后粘贴 callback 返回的 JSON：</label>
            <textarea
              className="w-full text-xs border border-gray-200 rounded-lg p-2 h-24 font-mono resize-none focus:outline-none focus:border-indigo-300"
              placeholder='{"access_token": "...", "refresh_token": "...", "client_id": "...", "client_secret": "..."}'
              onChange={(e) => {
                try { setCredentials(JSON.parse(e.target.value)); } catch {}
              }}
            />
          </div>
        </div>

        {/* Step 2: Export */}
        <div>
          <div className="text-sm font-semibold text-gray-700 mb-3">② 一键导出</div>
          <div className="bg-indigo-50 rounded-lg p-3 text-xs text-indigo-700 mb-3 space-y-1">
            <div className="flex items-center gap-1.5"><FolderOpen size={12} /> <strong>Google Drive：</strong>图片上传至 Images/，视频上传至 Videos/</div>
            <div className="flex items-center gap-1.5"><FileSpreadsheet size={12} /> <strong>Google Sheets：</strong>每平台一个 Tab，包含 AIDA 文案 + Drive 文件链接</div>
          </div>
          <button
            onClick={handleExport}
            disabled={loading || !credentials}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            <Upload size={14} />
            {loading ? step || "导出中..." : "导出到 Google Drive & Sheets"}
          </button>
        </div>

        {/* Result */}
        {result && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-green-600" />
              <span className="font-semibold text-green-800 text-sm">导出成功！{result.entry_count} 条内容</span>
            </div>
            <div className="space-y-2">
              {result.drive_folder_url && (
                <a href={result.drive_folder_url} target="_blank" rel="noopener noreferrer"
                  className="flex items-center gap-2 text-sm text-blue-700 hover:text-blue-900">
                  <FolderOpen size={13} />
                  <span className="underline">打开 Google Drive 文件夹</span>
                </a>
              )}
              <a href={result.spreadsheet_url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm text-green-700 hover:text-green-900">
                <FileSpreadsheet size={13} />
                <span className="underline">打开 Google Sheets 日历</span>
              </a>
            </div>
          </div>
        )}
      </div>

      {/* What gets exported */}
      <div className="mt-6 bg-white rounded-xl border border-gray-200 p-4">
        <div className="text-sm font-semibold text-gray-700 mb-3">导出内容说明</div>
        <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
          {[
            ["📁 Drive / Images", "所有批准的图片文件"],
            ["📁 Drive / Videos", "所有批准的视频文件"],
            ["📊 [A] 吸引注意", "AIDA 第1段 — Hook"],
            ["📊 [I] 激发兴趣", "AIDA 第2段 — 正文"],
            ["📊 [D] 引发欲望", "AIDA 第3段 — 价值"],
            ["📊 [A] 行动号召", "AIDA 第4段 — CTA"],
          ].map(([col, desc]) => (
            <div key={col} className="flex gap-1.5">
              <span className="font-medium text-gray-700">{col}</span>
              <span className="text-gray-400">— {desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
