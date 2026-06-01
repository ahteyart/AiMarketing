"use client";
import { useState } from "react";
import { getResearchPosts, getTrendingTopics, triggerResearch } from "@/lib/api";
import { RefreshCw, TrendingUp, Hash } from "lucide-react";
import clsx from "clsx";

const PLATFORMS = [
  { id: "all", label: "全部" },
  { id: "instagram", label: "Instagram" },
  { id: "facebook", label: "Facebook" },
  { id: "tiktok", label: "TikTok" },
  { id: "xiaohongshu", label: "小红书" },
];

function PlatformBadge({ platform }: { platform: string }) {
  const labels: Record<string, string> = {
    instagram: "Instagram", facebook: "Facebook", tiktok: "TikTok", xiaohongshu: "小红书",
  };
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded-full border font-medium",
      `platform-badge-${platform}`
    )}>
      {labels[platform] || platform}
    </span>
  );
}

export default function TrendsPage() {
  const [campaignId] = useState(""); // In real app: get from context or URL param
  const [platform, setPlatform] = useState("all");
  const [posts, setPosts] = useState<any[]>([]);
  const [topics, setTopics] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [triggered, setTriggered] = useState(false);

  const handleTrigger = async () => {
    if (!campaignId) return alert("请先选择 Campaign");
    setLoading(true);
    try {
      await triggerResearch(campaignId);
      setTriggered(true);
      setTimeout(async () => {
        const [postsData, topicsData] = await Promise.all([
          getResearchPosts(campaignId, platform === "all" ? undefined : platform),
          getTrendingTopics(campaignId),
        ]);
        setPosts(postsData);
        setTopics(topicsData.topics || []);
        setLoading(false);
      }, 3000);
    } catch {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">热门内容调研</h1>
          <p className="text-sm text-gray-500 mt-0.5">从各平台抓取高互动内容，分析趋势话题</p>
        </div>
        <button
          onClick={handleTrigger}
          disabled={loading}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          {loading ? "抓取中..." : "开始调研"}
        </button>
      </div>

      <div className="flex gap-2 mb-6 flex-wrap">
        {PLATFORMS.map((p) => (
          <button
            key={p.id}
            onClick={() => setPlatform(p.id)}
            className={clsx(
              "text-sm px-3 py-1.5 rounded-lg border transition-colors",
              platform === p.id
                ? "bg-indigo-600 text-white border-indigo-600"
                : "bg-white text-gray-600 border-gray-200 hover:border-indigo-300"
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      {topics.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={16} className="text-indigo-600" />
            <span className="font-semibold text-sm">热门话题</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {topics.map((t: any) => (
              <span key={t.hashtag} className="flex items-center gap-1 bg-indigo-50 text-indigo-700 text-xs px-2 py-1 rounded-full">
                <Hash size={10} />{t.hashtag}
                <span className="text-indigo-400 ml-1">{t.post_count}帖</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-3">
        {posts.map((post: any) => (
          <div key={post.id} className="bg-white rounded-xl border border-gray-200 p-4">
            <div className="flex items-start justify-between gap-3 mb-2">
              <PlatformBadge platform={post.platform} />
              <span className="text-xs text-gray-400 bg-gray-50 px-2 py-0.5 rounded font-mono">
                互动率 {(post.engagement_score * 100).toFixed(2)}%
              </span>
            </div>
            {post.author_handle && (
              <div className="text-xs text-gray-400 mb-1">@{post.author_handle}</div>
            )}
            <p className="text-sm text-gray-700 leading-relaxed line-clamp-3">{post.caption}</p>
            <div className="flex gap-4 mt-3 text-xs text-gray-500">
              <span>❤️ {post.likes?.toLocaleString()}</span>
              <span>💬 {post.comments?.toLocaleString()}</span>
              <span>🔁 {post.shares?.toLocaleString()}</span>
            </div>
          </div>
        ))}
        {posts.length === 0 && triggered && !loading && (
          <div className="text-center py-12 text-gray-400 text-sm">暂无数据，请配置平台 API Key 后重试</div>
        )}
        {posts.length === 0 && !triggered && (
          <div className="text-center py-12 text-gray-400 text-sm">点击「开始调研」抓取各平台热门内容</div>
        )}
      </div>
    </div>
  );
}
