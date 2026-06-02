"use client";
import { useState, useEffect } from "react";
import { getPendingApprovals, approveContent, rejectContent, generateImage, requestVideoGeneration } from "@/lib/api";
import { CheckCircle, XCircle, Edit3, AlertTriangle, Eye, Zap, Film } from "lucide-react";
import clsx from "clsx";

const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Instagram", facebook: "Facebook", xiaohongshu: "小红书",
};

function ComplianceBadge({ compliance }: { compliance: any }) {
  if (!compliance) return null;
  const ok = compliance.passed;
  return (
    <div className={clsx("flex items-center gap-1.5 text-xs px-2 py-1 rounded-lg", ok ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700")}>
      {ok ? <CheckCircle size={12} /> : <AlertTriangle size={12} />}
      <span>{ok ? "合规 ✓" : `问题: ${compliance.issues?.[0]}`}</span>
      <span className="text-gray-400">| {compliance.char_count}字 {compliance.hashtag_count}标签</span>
    </div>
  );
}

function AidaSection({ label, text, color }: { label: string; text: string; color: string }) {
  if (!text) return null;
  return (
    <div className="mb-2">
      <span className={clsx("text-xs font-bold px-1.5 py-0.5 rounded mr-2", color)}>{label}</span>
      <span className="text-sm text-gray-700">{text}</span>
    </div>
  );
}

export default function ApprovalPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [processing, setProcessing] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState<Record<string, string>>({});
  const [generatingImage, setGeneratingImage] = useState<string | null>(null);
  const [mediaMode, setMediaMode] = useState<Record<string, "image" | "video">({});

  useEffect(() => {
    getPendingApprovals()
      .then((d) => setItems(d.items || []))
      .finally(() => setLoading(false));
  }, []);

  const handleApprove = async (id: string) => {
    setProcessing(id);
    try {
      await approveContent(id, editing[id]);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (id: string) => {
    const reason = rejectReason[id];
    if (!reason) return alert("请填写拒绝原因");
    setProcessing(id);
    try {
      await rejectContent(id, reason);
      setItems((prev) => prev.filter((i) => i.id !== id));
    } finally {
      setProcessing(null);
    }
  };

  const handleGenerateMedia = async (id: string) => {
    const mode = mediaMode[id] || "image";
    setGeneratingImage(id);
    try {
      if (mode === "image") {
        await generateImage(id);
      } else {
        await requestVideoGeneration(id, true);
      }
      const updated = await getPendingApprovals();
      setItems(updated.items || []);
    } finally {
      setGeneratingImage(null);
    }
  };

  if (loading) return <div className="text-center py-16 text-gray-400">加载中...</div>;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">待审批内容</h1>
        <p className="text-sm text-gray-500 mt-0.5">{items.length} 条内容等待审批</p>
      </div>

      {items.length === 0 ? (
        <div className="text-center py-16 text-gray-400 text-sm bg-white rounded-xl border border-gray-200">
          <CheckCircle size={32} className="mx-auto mb-3 text-green-300" />
          暂无待审批内容
        </div>
      ) : (
        <div className="space-y-4">
          {items.map((item: any) => (
            <div key={item.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className={clsx("text-xs font-semibold px-2 py-0.5 rounded-full border",
                    `platform-badge-${item.platform}`
                  )}>{PLATFORM_LABELS[item.platform] || item.platform}</span>
                  <span className="text-xs text-gray-400">{item.content_type}</span>
                </div>
                <ComplianceBadge compliance={item.platform_compliance} />
              </div>

              <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Left: content preview */}
                <div>
                  {item.thumbnail_url || item.image_url ? (
                    <img
                      src={item.image_url || item.thumbnail_url}
                      alt="Preview"
                      className="w-full rounded-lg object-cover max-h-64 mb-3 bg-gray-100"
                    />
                  ) : (
                    <div>
                      <div className="w-full h-40 rounded-lg bg-gray-100 flex items-center justify-center text-gray-400 mb-3">
                        <Eye size={24} />
                      </div>
                      <div className="mb-3">
                        <div className="bg-amber-50 border border-amber-200 rounded-lg p-2 mb-2">
                          <p className="text-xs text-amber-800 mb-2">
                            需要配置 MCP 和 API 才能生成媒体：
                          </p>
                          <ul className="text-xs text-amber-700 space-y-1 ml-3">
                            <li>• AI 生成图片：Higgsfield MCP (已集成)</li>
                            <li>• UGC 视频：Runway ML API</li>
                          </ul>
                        </div>
                        <div className="flex gap-2 mb-2">
                          <label className="flex items-center gap-1.5 flex-1 cursor-pointer opacity-50">
                            <input
                              type="radio"
                              name={`media-${item.id}`}
                              value="image"
                              checked={(mediaMode[item.id] || "image") === "image"}
                              onChange={() => setMediaMode((prev) => ({ ...prev, [item.id]: "image" }))}
                              className="w-3.5 h-3.5 cursor-pointer"
                              disabled
                            />
                            <span className="text-sm text-gray-700">设计图片</span>
                          </label>
                          <label className="flex items-center gap-1.5 flex-1 cursor-pointer opacity-50">
                            <input
                              type="radio"
                              name={`media-${item.id}`}
                              value="video"
                              checked={(mediaMode[item.id] || "image") === "video"}
                              onChange={() => setMediaMode((prev) => ({ ...prev, [item.id]: "video" }))}
                              className="w-3.5 h-3.5 cursor-pointer"
                              disabled
                            />
                            <span className="text-sm text-gray-700">UGC 视频</span>
                          </label>
                        </div>
                        <button
                          disabled={true}
                          className="w-full flex items-center justify-center gap-1.5 bg-gray-100 text-gray-400 text-sm py-2 rounded-lg border border-gray-200 cursor-not-allowed"
                        >
                          <Zap size={14} /> 配置 API 后启用
                        </button>
                      </div>
                    </div>
                  )}
                  <div className="space-y-1">
                    <AidaSection label="A" text={item.copy_attention} color="bg-red-100 text-red-700" />
                    <AidaSection label="I" text={item.copy_interest} color="bg-orange-100 text-orange-700" />
                    <AidaSection label="D" text={item.copy_desire} color="bg-yellow-100 text-yellow-700" />
                    <AidaSection label="A" text={item.copy_action} color="bg-green-100 text-green-700" />
                  </div>
                </div>

                {/* Right: editable copy + actions */}
                <div>
                  <label className="text-xs font-semibold text-gray-500 mb-1 flex items-center gap-1">
                    <Edit3 size={11} /> 完整文案（可编辑）
                  </label>
                  <textarea
                    className="w-full text-sm border border-gray-200 rounded-lg p-2.5 h-36 resize-none focus:outline-none focus:border-indigo-300"
                    value={editing[item.id] ?? item.copy_text ?? ""}
                    onChange={(e) => setEditing((prev) => ({ ...prev, [item.id]: e.target.value }))}
                  />

                  <div className="mt-3">
                    <input
                      type="text"
                      placeholder="拒绝原因（拒绝时必填）"
                      className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-300"
                      value={rejectReason[item.id] || ""}
                      onChange={(e) => setRejectReason((prev) => ({ ...prev, [item.id]: e.target.value }))}
                    />
                  </div>

                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={() => handleApprove(item.id)}
                      disabled={processing === item.id}
                      className="flex-1 flex items-center justify-center gap-1.5 bg-green-600 hover:bg-green-700 text-white text-sm py-2 rounded-lg transition-colors disabled:opacity-50"
                    >
                      <CheckCircle size={14} /> 批准
                    </button>
                    <button
                      onClick={() => handleReject(item.id)}
                      disabled={processing === item.id}
                      className="flex-1 flex items-center justify-center gap-1.5 bg-red-50 hover:bg-red-100 text-red-700 text-sm py-2 rounded-lg border border-red-200 transition-colors disabled:opacity-50"
                    >
                      <XCircle size={14} /> 拒绝
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
