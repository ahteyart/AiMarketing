"use client";
import { useState } from "react";
import { generateCalendar, getCalendar } from "@/lib/api";
import { Calendar, Sparkles, ChevronRight } from "lucide-react";
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

function ContentTypeTag({ type }: { type: string }) {
  const labels: Record<string, string> = {
    image_post: "图文", carousel: "轮播", reel: "Reel", story: "Story", video: "视频",
  };
  return (
    <span className="text-xs bg-white border border-gray-200 text-gray-600 px-1.5 py-0.5 rounded">
      {labels[type] || type}
    </span>
  );
}

export default function CalendarPage() {
  const [campaignId] = useState("");
  const [entries, setEntries] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState("all");

  const handleGenerate = async () => {
    if (!campaignId) return alert("请先选择 Campaign");
    setLoading(true);
    try {
      await generateCalendar(campaignId);
      setTimeout(async () => {
        const data = await getCalendar(campaignId);
        setEntries(data);
        setLoading(false);
      }, 5000);
    } catch {
      setLoading(false);
    }
  };

  const filtered = entries.filter(
    (e: any) => selectedPlatform === "all" || e.platform === selectedPlatform
  );

  // Group by day
  const byDay: Record<number, any[]> = {};
  filtered.forEach((e: any) => {
    byDay[e.day_number] = byDay[e.day_number] || [];
    byDay[e.day_number].push(e);
  });

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">30天内容日历</h1>
          <p className="text-sm text-gray-500 mt-0.5">AI 基于调研数据规划的内容日程，所有文案遵循 AIDA 结构</p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          <Sparkles size={14} />
          {loading ? "生成中..." : "AI 生成30天日历"}
        </button>
      </div>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setSelectedPlatform("all")}
          className={clsx("text-sm px-3 py-1.5 rounded-lg border transition-colors",
            selectedPlatform === "all" ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200"
          )}
        >全部</button>
        {PLATFORMS.map((p) => (
          <button key={p} onClick={() => setSelectedPlatform(p)}
            className={clsx("text-sm px-3 py-1.5 rounded-lg border transition-colors",
              selectedPlatform === p ? "bg-indigo-600 text-white border-indigo-600" : "bg-white text-gray-600 border-gray-200"
            )}>
            {PLATFORM_LABELS[p]}
          </button>
        ))}
      </div>

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
                {dayEntries.map((entry: any) => (
                  <div key={entry.id}
                    className={clsx("p-4 border-l-4", PLATFORM_COLORS[entry.platform] || "border-l-gray-300 bg-white")}
                  >
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-semibold text-gray-600">{PLATFORM_LABELS[entry.platform]}</span>
                        <ContentTypeTag type={entry.content_type} />
                        {entry.content_format && (
                          <span className="text-xs text-gray-400">{entry.content_format}</span>
                        )}
                      </div>
                      <span className={clsx("text-xs px-2 py-0.5 rounded-full", {
                        "bg-yellow-100 text-yellow-700": entry.status === "planned",
                        "bg-green-100 text-green-700": entry.status === "approved",
                        "bg-blue-100 text-blue-700": entry.status === "generating",
                      })}>
                        {entry.status}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-800 mb-2">{entry.theme}</p>
                    {entry.suggested_hooks && (
                      <div className="space-y-1">
                        {entry.suggested_hooks.slice(0, 1).map((hook: string, i: number) => (
                          <div key={i} className="flex items-start gap-2">
                            <ChevronRight size={12} className="mt-0.5 text-gray-400 shrink-0" />
                            <span className="text-xs text-gray-600 italic">"{hook}"</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        {Object.keys(byDay).length === 0 && (
          <div className="text-center py-16 text-gray-400 text-sm">
            点击「AI 生成30天日历」开始规划
          </div>
        )}
      </div>
    </div>
  );
}
