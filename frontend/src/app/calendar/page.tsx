"use client";
import { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { generateCalendar, getCalendar, getGenerationStatus, generateContent } from "@/lib/api";
import { Calendar, Sparkles, ChevronRight, Globe, Clock, Check, FileText } from "lucide-react";
import clsx from "clsx";

const PLATFORMS = ["instagram", "facebook", "xiaohongshu"];
const PLATFORM_LABELS: Record<string, string> = {
  instagram: "Instagram", facebook: "Facebook", xiaohongshu: "小红书",
};
const PLATFORM_COLORS: Record<string, string> = {
  instagram: "border-l-pink-400 bg-pink-50",
  facebook: "border-l-blue-400 bg-blue-50",
  xiaohongshu: "border-l-red-400 bg-red-50",
};
const LANGUAGES = [
  { value: "english", label: "English" },
  { value: "malay", label: "Bahasa Melayu" },
  { value: "chinese", label: "中文" },
];
const DAY_OPTIONS = [
  { value: 1, label: "1 Day" },
  { value: 7, label: "7 Days" },
  { value: 14, label: "14 Days" },
  { value: 30, label: "30 Days" },
];
const STYLE_COLORS: Record<string, string> = {
  educational: "bg-blue-100 text-blue-700",
  storytelling: "bg-purple-100 text-purple-700",
  problem_solution: "bg-orange-100 text-orange-700",
  social_proof: "bg-green-100 text-green-700",
  behind_scenes: "bg-yellow-100 text-yellow-700",
  feature_spotlight: "bg-indigo-100 text-indigo-700",
  question_debate: "bg-pink-100 text-pink-700",
  lifestyle: "bg-teal-100 text-teal-700",
  before_after: "bg-red-100 text-red-700",
  tips_hacks: "bg-cyan-100 text-cyan-700",
  myth_busting: "bg-amber-100 text-amber-700",
  emotional: "bg-rose-100 text-rose-700",
  ugc_authentic: "bg-lime-100 text-lime-700",
  comparison: "bg-violet-100 text-violet-700",
};

function ContentTypeTag({ type }: { type: string }) {
  const labels: Record<string, string> = {
    image_post: "Image", carousel: "Carousel", reel: "Reel",
    story: "Story", video: "Video",
  };
  return (
    <span className="text-xs bg-white border border-gray-200 text-gray-600 px-1.5 py-0.5 rounded">
      {labels[type] || type}
    </span>
  );
}

function StyleBadge({ style }: { style: string }) {
  const label = style.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded-full font-medium", STYLE_COLORS[style] || "bg-gray-100 text-gray-600")}>
      {label}
    </span>
  );
}

function CalendarPageInner() {
  const searchParams = useSearchParams();
  const [campaignId, setCampaignId] = useState(searchParams.get("campaign_id") || "");
  const [language, setLanguage] = useState(searchParams.get("language") || "english");
  const [days, setDays] = useState(30);

  useEffect(() => {
    const id = searchParams.get("campaign_id");
    if (id) setCampaignId(id);
    const lang = searchParams.get("language");
    if (lang) setLanguage(lang);
  }, [searchParams]);

  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [genError, setGenError] = useState("");
  const [selectedPlatform, setSelectedPlatform] = useState("all");
  const [pollCount, setPollCount] = useState(0);

  // Hook selection: { [entryId]: selectedHookText }
  const [selectedHooks, setSelectedHooks] = useState<Record<string, string>>({});
  // Generating body content: Set of entryIds currently being generated
  const [generatingContent, setGeneratingContent] = useState<Set<string>>(new Set());
  // Done: Set of entryIds that content was started for
  const [contentStarted, setContentStarted] = useState<Set<string>>(new Set());

  const handleGenerate = async () => {
    if (!campaignId.trim()) return alert("Please enter a Campaign ID");
    setLoading(true);
    setEntries([]);
    setGenError("");
    setSelectedHooks({});
    setContentStarted(new Set());
    try {
      await generateCalendar(campaignId, undefined, days, language);
      let attempts = 0;
      const poll = setInterval(async () => {
        attempts++;
        setPollCount(attempts);
        try {
          const status = await getGenerationStatus(campaignId);
          if (status.status === "error") {
            setLoading(false);
            clearInterval(poll);
            setGenError(status.message || "Generation failed. Check that ANTHROPIC_API_KEY is set in Railway.");
            return;
          }
          const data = await getCalendar(campaignId);
          if (data && data.length > 0) {
            setEntries(data);
            setLoading(false);
            clearInterval(poll);
          }
        } catch {}
        if (attempts >= 36) {
          setLoading(false);
          clearInterval(poll);
          setGenError("Generation is taking longer than expected. Check Railway logs for errors.");
        }
      }, 5000);
    } catch (e: any) {
      setGenError(e.response?.data?.detail || "Generation failed");
      setLoading(false);
    }
  };

  const selectHook = (entryId: string, hook: string) => {
    setSelectedHooks(prev => ({
      ...prev,
      [entryId]: prev[entryId] === hook ? "" : hook, // toggle off if same
    }));
  };

  const handleGenerateBody = async (entryId: string) => {
    const hook = selectedHooks[entryId];
    setGeneratingContent(prev => new Set(prev).add(entryId));
    try {
      await generateContent(entryId, false, hook || undefined);
      setContentStarted(prev => new Set(prev).add(entryId));
    } catch (e: any) {
      alert(e.response?.data?.detail || "Failed to start content generation");
    } finally {
      setGeneratingContent(prev => { const s = new Set(prev); s.delete(entryId); return s; });
    }
  };

  const totalSelected = Object.values(selectedHooks).filter(Boolean).length;

  const handleGenerateAllSelected = async () => {
    const toGenerate = entries.filter(e => selectedHooks[e.id]);
    for (const entry of toGenerate) {
      if (!contentStarted.has(entry.id)) {
        await handleGenerateBody(entry.id);
      }
    }
  };

  const filtered = entries.filter(
    (e: any) => selectedPlatform === "all" || e.platform === selectedPlatform
  );
  const byDay: Record<number, any[]> = {};
  filtered.forEach((e: any) => {
    byDay[e.day_number] = byDay[e.day_number] || [];
    byDay[e.day_number].push(e);
  });

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Content Calendar</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Step 1: Generate calendar → Step 2: Pick a headline per post → Step 3: Generate body copy
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 space-y-4">
        <div>
          <label className="text-xs font-semibold text-gray-600 block mb-1.5">Campaign ID</label>
          <input
            type="text"
            value={campaignId}
            onChange={(e) => setCampaignId(e.target.value)}
            placeholder="Paste your Campaign ID from the overview"
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-300"
          />
        </div>

        <div className="flex gap-4 flex-wrap">
          <div className="flex-1 min-w-[160px]">
            <label className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-1.5">
              <Globe size={11} /> Language
            </label>
            <div className="flex gap-1.5 flex-wrap">
              {LANGUAGES.map((l) => (
                <button key={l.value} onClick={() => setLanguage(l.value)}
                  className={clsx("text-xs px-3 py-1.5 rounded-lg border transition-colors",
                    language === l.value ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                  )}>
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 min-w-[160px]">
            <label className="text-xs font-semibold text-gray-600 flex items-center gap-1 mb-1.5">
              <Clock size={11} /> Planning Period
            </label>
            <div className="flex gap-1.5 flex-wrap">
              {DAY_OPTIONS.map((d) => (
                <button key={d.value} onClick={() => setDays(d.value)}
                  className={clsx("text-xs px-3 py-1.5 rounded-lg border transition-colors",
                    days === d.value ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200 hover:border-gray-300"
                  )}>
                  {d.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        <button onClick={handleGenerate} disabled={loading}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-5 py-2 rounded-lg transition-colors disabled:opacity-50 font-medium">
          <Sparkles size={14} />
          {loading ? `Generating... (${pollCount * 5}s)` : `Generate ${days}-Day Calendar in ${LANGUAGES.find(l => l.value === language)?.label}`}
        </button>
        {genError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            <strong>Error:</strong> {genError}
          </div>
        )}
      </div>

      {/* Sticky "Generate Body for Selected" bar */}
      {totalSelected > 0 && (
        <div className="sticky top-4 z-10 mb-4 bg-indigo-600 text-white rounded-xl px-4 py-3 flex items-center justify-between shadow-lg">
          <span className="text-sm font-medium">
            {totalSelected} headline{totalSelected > 1 ? "s" : ""} selected
          </span>
          <button
            onClick={handleGenerateAllSelected}
            className="flex items-center gap-2 bg-white text-indigo-700 text-xs font-semibold px-4 py-1.5 rounded-lg hover:bg-indigo-50 transition-colors"
          >
            <FileText size={13} />
            Generate Body Copy for All
          </button>
        </div>
      )}

      {/* Platform filter */}
      {entries.length > 0 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          <button onClick={() => setSelectedPlatform("all")}
            className={clsx("text-sm px-3 py-1.5 rounded-lg border transition-colors",
              selectedPlatform === "all" ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200"
            )}>All ({entries.length})</button>
          {PLATFORMS.map((p) => {
            const count = entries.filter((e: any) => e.platform === p).length;
            return count > 0 ? (
              <button key={p} onClick={() => setSelectedPlatform(p)}
                className={clsx("text-sm px-3 py-1.5 rounded-lg border transition-colors",
                  selectedPlatform === p ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200"
                )}>
                {PLATFORM_LABELS[p]} ({count})
              </button>
            ) : null;
          })}
        </div>
      )}

      {/* Instruction hint */}
      {entries.length > 0 && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
          <strong>Pick your headlines:</strong> Click a hook below to select it (turns green), then click "Generate Body Copy" to write the full post body using your chosen opening line.
        </div>
      )}

      {/* Calendar entries */}
      <div className="space-y-3">
        {Object.entries(byDay)
          .sort(([a], [b]) => Number(a) - Number(b))
          .map(([day, dayEntries]) => (
            <div key={day} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-2 bg-gray-50 border-b border-gray-100 flex items-center gap-3">
                <Calendar size={14} className="text-gray-400" />
                <span className="text-sm font-semibold text-gray-700">Day {day}</span>
                {(dayEntries[0] as any).scheduled_date && (
                  <span className="text-xs text-gray-400">{(dayEntries[0] as any).scheduled_date}</span>
                )}
              </div>
              <div className="divide-y divide-gray-50">
                {dayEntries.map((entry: any) => {
                  const chosenHook = selectedHooks[entry.id] || "";
                  const isGenerating = generatingContent.has(entry.id);
                  const isDone = contentStarted.has(entry.id);
                  return (
                    <div key={entry.id}
                      className={clsx("p-4 border-l-4", PLATFORM_COLORS[entry.platform] || "border-l-gray-300 bg-white")}
                    >
                      <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-semibold text-gray-600">{PLATFORM_LABELS[entry.platform]}</span>
                          <ContentTypeTag type={entry.content_type} />
                          {entry.content_format && (
                            <span className="text-xs text-gray-400">{entry.content_format}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          {entry.content_style && <StyleBadge style={entry.content_style} />}
                          <span className={clsx("text-xs px-2 py-0.5 rounded-full", {
                            "bg-yellow-100 text-yellow-700": entry.status === "planned",
                            "bg-green-100 text-green-700": entry.status === "approved",
                            "bg-blue-100 text-blue-700": entry.status === "generating",
                          })}>
                            {entry.status}
                          </span>
                        </div>
                      </div>

                      <p className="text-sm font-medium text-gray-800 mb-3">{entry.theme}</p>

                      {/* Selectable hooks */}
                      {entry.suggested_hooks && entry.suggested_hooks.length > 0 && (
                        <div className="space-y-1.5 mb-3">
                          <p className="text-xs font-semibold text-gray-500 mb-1">Pick an opening hook:</p>
                          {entry.suggested_hooks.map((hook: string, i: number) => {
                            const isSelected = chosenHook === hook;
                            return (
                              <button
                                key={i}
                                onClick={() => selectHook(entry.id, hook)}
                                className={clsx(
                                  "w-full text-left text-xs px-3 py-2 rounded-lg border transition-all",
                                  isSelected
                                    ? "bg-green-50 border-green-400 text-green-800 font-medium"
                                    : "bg-white border-gray-200 text-gray-600 hover:border-indigo-300 hover:bg-indigo-50"
                                )}
                              >
                                <span className="flex items-start gap-2">
                                  {isSelected
                                    ? <Check size={12} className="mt-0.5 text-green-500 shrink-0" />
                                    : <ChevronRight size={12} className="mt-0.5 text-gray-400 shrink-0" />
                                  }
                                  <span className="italic">"{hook}"</span>
                                </span>
                              </button>
                            );
                          })}
                        </div>
                      )}

                      {/* Generate body button (per entry) */}
                      <div className="flex items-center gap-2 flex-wrap">
                        {isDone ? (
                          <span className="flex items-center gap-1.5 text-xs text-green-600 font-medium">
                            <Check size={12} /> Body generation started — check Review Content
                          </span>
                        ) : (
                          <button
                            onClick={() => handleGenerateBody(entry.id)}
                            disabled={isGenerating}
                            className={clsx(
                              "flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border transition-colors font-medium",
                              chosenHook
                                ? "bg-indigo-600 text-white border-indigo-600 hover:bg-indigo-700"
                                : "bg-gray-50 text-gray-500 border-gray-200 hover:bg-gray-100"
                            )}
                          >
                            <FileText size={12} />
                            {isGenerating ? "Starting..." : chosenHook ? "Generate Body Copy" : "Generate Body (no hook selected)"}
                          </button>
                        )}

                        {entry.suggested_hashtags && entry.suggested_hashtags.length > 0 && (
                          <div className="flex gap-1 flex-wrap">
                            {entry.suggested_hashtags.slice(0, 4).map((tag: string, i: number) => (
                              <span key={i} className="text-xs text-indigo-400">{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

        {Object.keys(byDay).length === 0 && !loading && (
          <div className="text-center py-16 text-gray-400 text-sm">
            <Sparkles size={32} className="mx-auto mb-3 opacity-30" />
            <p>Select language, planning period, enter Campaign ID, then click Generate</p>
          </div>
        )}
        {loading && (
          <div className="text-center py-16 text-gray-400 text-sm">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto mb-3" />
            <p>AI is generating your {days}-day content plan in {LANGUAGES.find(l => l.value === language)?.label}...</p>
            <p className="text-xs mt-1 text-gray-300">This takes ~30-60 seconds</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function CalendarPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64 text-gray-400 text-sm">Loading...</div>}>
      <CalendarPageInner />
    </Suspense>
  );
}
