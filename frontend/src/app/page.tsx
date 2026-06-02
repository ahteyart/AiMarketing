"use client";
import { useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import { uploadReferenceImage } from "@/lib/api";
import { Plus, Copy, Check, Calendar, CheckSquare, FolderOpen, ChevronRight, Trash2, Globe, Tag, ImagePlus, X } from "lucide-react";
import clsx from "clsx";

const PLATFORMS = [
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
  { id: "xiaohongshu", label: "小红书" },
];

const LANGUAGES = [
  { value: "english", label: "English" },
  { value: "malay", label: "Bahasa Melayu" },
  { value: "chinese", label: "中文" },
];

interface Campaign {
  id: string;
  name: string;
  brand_voice: string | null;
  target_audience: string | null;
  target_platforms: string[];
  keywords: string[] | null;
  language: string;
  status: string;
}

function CopiedId({ id }: { id: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={copy} className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 font-mono group">
      <span className="truncate max-w-[180px]">{id}</span>
      {copied ? <Check size={12} className="text-green-500 shrink-0" /> : <Copy size={12} className="shrink-0 opacity-0 group-hover:opacity-100" />}
    </button>
  );
}

export default function HomePage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [keywordInput, setKeywordInput] = useState("");
  const [referenceImages, setReferenceImages] = useState<string[]>([]);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState({
    name: "",
    brand_voice: "",
    target_audience: "",
    target_platforms: ["instagram", "facebook", "xiaohongshu"],
    keywords: [] as string[],
    language: "english",
  });

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingPhoto(true);
    try {
      const { url } = await uploadReferenceImage(file);
      setReferenceImages((prev) => [...prev, url]);
    } catch {
      alert("Photo upload failed. Check your storage configuration.");
    } finally {
      setUploadingPhoto(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  useEffect(() => {
    api.get("/campaigns/").then((r) => setCampaigns(r.data)).catch(() => {});
  }, []);

  const togglePlatform = (p: string) => {
    setForm((f) => ({
      ...f,
      target_platforms: f.target_platforms.includes(p)
        ? f.target_platforms.filter((x) => x !== p)
        : [...f.target_platforms, p],
    }));
  };

  const addKeyword = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const kw = keywordInput.trim().replace(/,$/, "");
      if (kw && !form.keywords.includes(kw)) {
        setForm((f) => ({ ...f, keywords: [...f.keywords, kw] }));
      }
      setKeywordInput("");
    }
  };

  const removeKeyword = (kw: string) => {
    setForm((f) => ({ ...f, keywords: f.keywords.filter((k) => k !== kw) }));
  };

  const handleCreate = async () => {
    if (!form.name.trim()) return alert("Please enter a product / brand name");
    if (form.target_platforms.length === 0) return alert("Select at least one platform");
    setSaving(true);
    try {
      const payload = {
        ...form,
        brand_context: referenceImages.length > 0 ? { reference_images: referenceImages } : null,
      };
      const { data } = await api.post("/campaigns/", payload);
      setCampaigns((prev) => [data, ...prev]);
      setShowForm(false);
      setForm({ name: "", brand_voice: "", target_audience: "", target_platforms: ["instagram", "facebook", "xiaohongshu"], keywords: [], language: "english" });
      setKeywordInput("");
      setReferenceImages([]);
    } catch (e: any) {
      alert(e.response?.data?.detail || "Failed to create campaign");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Archive this campaign?")) return;
    try {
      await api.delete(`/campaigns/${id}`);
      setCampaigns((prev) => prev.filter((c) => c.id !== id));
    } catch {}
  };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">AI Marketing Automation</h1>
          <p className="text-sm text-gray-500 mt-0.5">Create a campaign → generate content calendar → approve → export</p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-lg transition-colors font-medium"
        >
          <Plus size={15} />
          New Campaign
        </button>
      </div>

      {/* Create Campaign Form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-indigo-200 shadow-sm p-5 mb-6 space-y-4">
          <h2 className="text-sm font-bold text-gray-900">Create New Campaign</h2>

          {/* Product / Brand Name */}
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1.5">Product / Brand Name <span className="text-red-400">*</span></label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="e.g. GlowSkin Serum, Kedai Makan Pak Ali, 美白精华液"
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-300"
            />
          </div>

          {/* Target Audience */}
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1.5">Target Audience</label>
            <input
              type="text"
              value={form.target_audience}
              onChange={(e) => setForm((f) => ({ ...f, target_audience: e.target.value }))}
              placeholder="e.g. Women 25-35, skincare enthusiasts, budget-conscious"
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-300"
            />
          </div>

          {/* Brand Voice / Content Brief */}
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1.5">Content Brief & Brand Voice</label>
            <textarea
              value={form.brand_voice}
              onChange={(e) => setForm((f) => ({ ...f, brand_voice: e.target.value }))}
              placeholder="Describe your product, key benefits, unique selling points, tone of voice. e.g. 'Lightweight serum that reduces dark spots in 14 days. Tone: friendly, science-backed, affordable luxury.'"
              rows={3}
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-300 resize-none"
            />
          </div>

          {/* Keywords */}
          <div>
            <label className="text-xs font-semibold text-gray-600 block mb-1.5">
              <Tag size={11} className="inline mr-1" />
              Keywords / Topics <span className="font-normal text-gray-400">(press Enter to add)</span>
            </label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {form.keywords.map((kw) => (
                <span key={kw} className="flex items-center gap-1 bg-indigo-50 text-indigo-700 text-xs px-2 py-1 rounded-full border border-indigo-200">
                  {kw}
                  <button onClick={() => removeKeyword(kw)} className="hover:text-red-500">×</button>
                </span>
              ))}
            </div>
            <input
              type="text"
              value={keywordInput}
              onChange={(e) => setKeywordInput(e.target.value)}
              onKeyDown={addKeyword}
              placeholder="e.g. skincare, anti-aging, K-beauty — press Enter"
              className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-300"
            />
          </div>

          {/* Language + Platforms row */}
          <div className="flex gap-6 flex-wrap">
            {/* Language */}
            <div>
              <label className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-1.5">
                <Globe size={11} /> Content Language
              </label>
              <div className="flex gap-1.5">
                {LANGUAGES.map((l) => (
                  <button
                    key={l.value}
                    onClick={() => setForm((f) => ({ ...f, language: l.value }))}
                    className={clsx("text-xs px-3 py-1.5 rounded-lg border transition-colors",
                      form.language === l.value ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                    )}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Platforms */}
            <div>
              <label className="text-xs font-semibold text-gray-600 block mb-1.5">Target Platforms</label>
              <div className="flex gap-1.5">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => togglePlatform(p.id)}
                    className={clsx("text-xs px-3 py-1.5 rounded-lg border transition-colors",
                      form.target_platforms.includes(p.id) ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Reference Photos */}
          <div>
            <label className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-1.5">
              <ImagePlus size={11} /> Reference Photos <span className="font-normal text-gray-400">(product / model / shop — optional)</span>
            </label>
            <div className="flex flex-wrap gap-2 mb-2">
              {referenceImages.map((url, i) => (
                <div key={i} className="relative w-16 h-16 rounded-lg overflow-hidden border border-gray-200 bg-gray-50">
                  <img src={url} alt="reference" className="w-full h-full object-cover" />
                  <button
                    onClick={() => setReferenceImages((prev) => prev.filter((_, idx) => idx !== i))}
                    className="absolute top-0.5 right-0.5 bg-black/60 text-white rounded-full p-0.5 hover:bg-red-500"
                  >
                    <X size={10} />
                  </button>
                </div>
              ))}
              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={uploadingPhoto}
                className="w-16 h-16 rounded-lg border-2 border-dashed border-gray-300 hover:border-indigo-400 flex flex-col items-center justify-center text-gray-400 hover:text-indigo-500 transition-colors disabled:opacity-50"
              >
                {uploadingPhoto ? (
                  <span className="text-[10px]">Uploading...</span>
                ) : (
                  <><ImagePlus size={16} /><span className="text-[10px] mt-0.5">Add photo</span></>
                )}
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              onChange={handlePhotoUpload}
              className="hidden"
            />
            {referenceImages.length > 0 && (
              <p className="text-xs text-gray-400">These photos will guide DALL-E image generation and Higgsfield video animation.</p>
            )}
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-1">
            <button
              onClick={handleCreate}
              disabled={saving}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-5 py-2 rounded-lg transition-colors disabled:opacity-50 font-medium"
            >
              {saving ? "Creating..." : "Create Campaign"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Campaign List */}
      {campaigns.length > 0 ? (
        <div className="space-y-3">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Your Campaigns</h2>
          {campaigns.map((c) => (
            <div key={c.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <h3 className="font-semibold text-gray-900 text-sm">{c.name}</h3>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    <CopiedId id={c.id} />
                    <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                      {LANGUAGES.find((l) => l.value === c.language)?.label || c.language}
                    </span>
                    {c.target_platforms?.map((p) => (
                      <span key={p} className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full">{p}</span>
                    ))}
                  </div>
                  {c.target_audience && (
                    <p className="text-xs text-gray-500 mt-1.5">👥 {c.target_audience}</p>
                  )}
                  {c.brand_voice && (
                    <p className="text-xs text-gray-400 mt-0.5 line-clamp-1">💬 {c.brand_voice}</p>
                  )}
                </div>
                <button onClick={() => handleDelete(c.id)} className="text-gray-300 hover:text-red-400 transition-colors shrink-0">
                  <Trash2 size={14} />
                </button>
              </div>

              {/* Quick Actions */}
              <div className="flex gap-2 flex-wrap">
                <a
                  href={`/calendar?campaign_id=${c.id}&language=${c.language}`}
                  className="flex items-center gap-1.5 text-xs bg-indigo-50 hover:bg-indigo-100 text-indigo-700 px-3 py-1.5 rounded-lg transition-colors font-medium"
                >
                  <Calendar size={12} /> Generate Calendar
                  <ChevronRight size={11} />
                </a>
                <a
                  href={`/approval?campaign_id=${c.id}`}
                  className="flex items-center gap-1.5 text-xs bg-green-50 hover:bg-green-100 text-green-700 px-3 py-1.5 rounded-lg transition-colors font-medium"
                >
                  <CheckSquare size={12} /> Review Content
                  <ChevronRight size={11} />
                </a>
                <a
                  href={`/export?campaign_id=${c.id}`}
                  className="flex items-center gap-1.5 text-xs bg-orange-50 hover:bg-orange-100 text-orange-700 px-3 py-1.5 rounded-lg transition-colors font-medium"
                >
                  <FolderOpen size={12} /> Export
                  <ChevronRight size={11} />
                </a>
              </div>
            </div>
          ))}
        </div>
      ) : (
        !showForm && (
          <div className="text-center py-16 bg-white rounded-xl border border-dashed border-gray-200">
            <div className="text-4xl mb-3">🚀</div>
            <p className="text-sm font-medium text-gray-700 mb-1">No campaigns yet</p>
            <p className="text-xs text-gray-400 mb-4">Create your first campaign to start generating AI content</p>
            <button
              onClick={() => setShowForm(true)}
              className="text-sm bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg transition-colors font-medium"
            >
              + Create Campaign
            </button>
          </div>
        )
      )}
    </div>
  );
}
