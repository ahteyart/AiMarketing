"use client";
import { useState } from "react";
import { startGoogleAuth, exportToSheets } from "@/lib/api";
import { FileSpreadsheet, ExternalLink, CheckCircle } from "lucide-react";

export default function ExportPage() {
  const [campaignId] = useState("");
  const [credentials, setCredentials] = useState<object | null>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const handleGoogleAuth = async () => {
    if (!campaignId) return alert("请先选择 Campaign");
    try {
      const data = await startGoogleAuth(campaignId);
      window.open(data.auth_url, "_blank", "width=600,height=700");
      alert("请在弹出窗口完成 Google 授权，授权完成后粘贴返回的 credentials JSON");
    } catch (e: any) {
      alert("请先配置 GOOGLE_CLIENT_ID 和 GOOGLE_CLIENT_SECRET");
    }
  };

  const handleExport = async () => {
    if (!credentials) return alert("请先完成 Google 授权");
    if (!campaignId) return alert("请先选择 Campaign");
    setLoading(true);
    try {
      const data = await exportToSheets(campaignId, credentials);
      setResult(data);
    } catch (e: any) {
      alert(e.response?.data?.detail || "导出失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">导出到 Google Sheets</h1>
        <p className="text-sm text-gray-500 mt-0.5">将批准的内容日历导出到 Google Sheets，按平台分 Tab</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
        {/* Step 1: Auth */}
        <div>
          <div className="text-sm font-semibold text-gray-700 mb-3">① Google 授权</div>
          <button
            onClick={handleGoogleAuth}
            className="flex items-center gap-2 text-sm px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            <img src="https://www.google.com/favicon.ico" alt="" className="w-4 h-4" />
            连接 Google 账号
          </button>
          <div className="mt-2">
            <label className="text-xs text-gray-500 block mb-1">或直接粘贴 credentials JSON：</label>
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
          <div className="text-sm font-semibold text-gray-700 mb-3">② 导出内容</div>
          <div className="bg-indigo-50 rounded-lg p-3 text-xs text-indigo-700 mb-3">
            <strong>导出格式：</strong>每个平台一个 Tab（📸 Instagram / 👥 Facebook / 📕 小红书），
            包含 AIDA 四段文案、话题标签、图片链接、合规检查结果。颜色标注审批状态。
          </div>
          <button
            onClick={handleExport}
            disabled={loading || !credentials}
            className="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
          >
            <FileSpreadsheet size={14} />
            {loading ? "导出中..." : "一键导出到 Google Sheets"}
          </button>
        </div>

        {/* Result */}
        {result && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle size={16} className="text-green-600" />
              <span className="font-semibold text-green-800 text-sm">导出成功！{result.entry_count} 条内容</span>
            </div>
            <a
              href={result.spreadsheet_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 text-sm text-green-700 hover:text-green-900 underline"
            >
              <ExternalLink size={13} />
              打开 Google Sheets
            </a>
          </div>
        )}
      </div>

      {/* Column legend */}
      <div className="mt-6 bg-white rounded-xl border border-gray-200 p-4">
        <div className="text-sm font-semibold text-gray-700 mb-3">Sheets 列说明</div>
        <div className="grid grid-cols-2 gap-1.5 text-xs text-gray-600">
          {[
            ["日期", "计划发布日期"],
            ["平台", "Instagram / Facebook / 小红书"],
            ["[A] 吸引注意", "AIDA 第1段 — Hook"],
            ["[I] 激发兴趣", "AIDA 第2段 — 正文"],
            ["[D] 引发欲望", "AIDA 第3段 — 价值"],
            ["[A] 行动号召", "AIDA 第4段 — CTA"],
            ["完整文案", "组合后的完整发帖文案"],
            ["合规检查", "字数/标签数合规状态"],
          ].map(([col, desc]) => (
            <div key={col} className="flex gap-1.5">
              <span className="font-medium text-gray-700 min-w-0 truncate">{col}</span>
              <span className="text-gray-400">— {desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
