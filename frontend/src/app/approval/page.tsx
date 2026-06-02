"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import {
  getPendingApprovals, approveContent, rejectContent,
  generateImage, requestVideoGeneration, uploadReferenceImage, getContentItem,
} from "@/lib/api";
import { CheckCircle, XCircle, Edit3, AlertTriangle, Eye, Zap, Film, ImagePlus, X, RefreshCw } from "lucide-react";
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
  const [generatingFor, setGeneratingFor] = useState<string | null>(null);
  const [mediaMode, setMediaMode] = useState<Record<string, "image" | "video">>({});
  const [referenceUrls, setReferenceUrls] = useState<Record<string, string>>({});
  const [uploadingRef, setUploadingRef] = useState<string | null>(null);
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    getPendingApprovals()
      .then((d) => setItems(d.items || []))
      .finally(() => setLoading(false));
  }, []);

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
  }, []);

  const startPolling = useCallback((contentId: string) => {
    stopPolling();
    let attempts = 0;
    pollRef.current = setInterval(async () => {
      attempts++;
      try {
        const updated = await getContentItem(contentId);
        if (updated.image_url || updated.video_url || updated.status !== "generating") {
          setItems((prev) =>
            prev.map((item) => item.id === contentId ? { ...item, ...updated } : item)
          );
          setGeneratingFor(null);
          stopPolling();
          return;
        }
      } catch { /* keep polling */ }
      if (attempts >= 30) { // 2 min timeout
        setGeneratingFor(null);
        stopPolling();
      }
    }, 4000);
  }, [stopPolling]);

  useEffect(() => () => stopPolling(), [stopPolling]);

  const handleRefUpload = async (id: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingRef(id);
    try {
      const { url } = await uploadReferenceImage(file);
      setReferenceUrls((prev) => ({ ...prev, [id]: url }));
    } catch {
      alert("Photo upload failed.");
    } finally {
      setUploadingRef(null);
      const input = fileRefs.current[id];
      if (input) input.value = "";
    }
  };

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
    setGeneratingFor(id);
    const refUrl = referenceUrls[id];
    try {
      if (mode === "image") {
        await generateImage(id, refUrl);
        startPolling(id);
      } else {
        const result = await requestVideoGeneration(id, true, refUrl);
        if (result?.error) {
          alert(`视频生成失败: ${result.error}`);
          setGeneratingFor(null);
        } else {
          startPolling(id);
        }
      }
    } catch (err: any) {
      alert(err?.response?.data?.detail || "Generation failed");
      setGeneratingFor(null);
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
          {items.map((item: any) => {
            const isGenerating = generatingFor === item.id;
            const hasMedia = item.thumbnail_url || item.image_url || item.video_url;
            return (
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
                  {/* Left: media preview + generate controls */}
                  <div>
                    {/* Image / video preview area */}
                    <div className="relative w-full rounded-lg overflow-hidden bg-gray-100 mb-3" style={{ minHeight: 160 }}>
                      {isGenerating ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50">
                          <RefreshCw size={24} className="text-indigo-400 animate-spin mb-2" />
                          <span className="text-xs text-gray-500">AI 生成中，请稍候…</span>
                        </div>
                      ) : item.video_url ? (
                        <video src={item.video_url} controls className="w-full max-h-64 object-cover" />
                      ) : item.image_url || item.thumbnail_url ? (
                        <img
                          src={item.image_url || item.thumbnail_url}
                          alt="Preview"
                          className="w-full max-h-64 object-cover"
                        />
                      ) : (
                        <div className="absolute inset-0 flex items-center justify-center text-gray-300">
                          <Eye size={24} />
                        </div>
                      )}
                    </div>

                    {/* Generate controls — always visible */}
                    <div className="mb-3">
                      <div className="flex gap-2 mb-2">
                        <label className="flex items-center gap-1.5 flex-1 cursor-pointer">
                          <input
                            type="radio" name={`media-${item.id}`} value="image"
                            checked={(mediaMode[item.id] || "image") === "image"}
                            onChange={() => setMediaMode((prev) => ({ ...prev, [item.id]: "image" }))}
                            className="w-3.5 h-3.5 cursor-pointer accent-indigo-600"
                          />
                          <span className="text-sm text-gray-700">🎨 {hasMedia ? "重新生成图" : "生成设计图"}</span>
                        </label>
                        <label className="flex items-center gap-1.5 flex-1 cursor-pointer">
                          <input
                            type="radio" name={`media-${item.id}`} value="video"
                            checked={(mediaMode[item.id] || "image") === "video"}
                            onChange={() => setMediaMode((prev) => ({ ...prev, [item.id]: "video" }))}
                            className="w-3.5 h-3.5 cursor-pointer accent-indigo-600"
                          />
                          <span className="text-sm text-gray-700">🎬 Higgsfield 视频</span>
                        </label>
                      </div>

                      {/* Reference photo upload */}
                      <div className="flex items-center gap-2 mb-2">
                        {referenceUrls[item.id] && (
                          <div className="relative w-10 h-10 rounded-lg overflow-hidden border border-gray-200 shrink-0">
                            <img src={referenceUrls[item.id]} alt="ref" className="w-full h-full object-cover" />
                            <button
                              onClick={() => setReferenceUrls((prev) => { const n = { ...prev }; delete n[item.id]; return n; })}
                              className="absolute top-0 right-0 bg-black/60 text-white p-0.5 hover:bg-red-500"
                            ><X size={9} /></button>
                          </div>
                        )}
                        <button
                          onClick={() => fileRefs.current[item.id]?.click()}
                          disabled={uploadingRef === item.id}
                          className="flex items-center gap-1 text-xs text-gray-500 hover:text-indigo-600 border border-dashed border-gray-300 hover:border-indigo-400 px-2 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                        >
                          <ImagePlus size={12} />
                          {uploadingRef === item.id ? "上传中..." : referenceUrls[item.id] ? "换图" : "上传参考图"}
                        </button>
                        <input
                          type="file" accept="image/jpeg,image/png,image/webp"
                          ref={(el) => { fileRefs.current[item.id] = el; }}
                          onChange={(e) => handleRefUpload(item.id, e)}
                          className="hidden"
                        />
                      </div>

                      <button
                        onClick={() => handleGenerateMedia(item.id)}
                        disabled={isGenerating}
                        className="w-full flex items-center justify-center gap-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-sm py-2 rounded-lg border border-indigo-200 transition-colors disabled:opacity-50"
                      >
                        {isGenerating ? (
                          <><RefreshCw size={14} className="animate-spin" /> AI 生成中...</>
                        ) : (mediaMode[item.id] || "image") === "image" ? (
                          <><Zap size={14} /> {hasMedia ? "重新生成图片" : "生成设计图"}</>
                        ) : (
                          <><Film size={14} /> 生成 UGC 视频</>
                        )}
                      </button>
                    </div>

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
            );
          })}
        </div>
      )}
    </div>
  );
}
