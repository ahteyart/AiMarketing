"use client";
import Link from "next/link";
import { Calendar, CheckSquare, FolderOpen, Zap, ArrowRight } from "lucide-react";

const steps = [
  {
    number: "01",
    title: "创建 Campaign",
    description: "输入品牌信息、目标受众、内容关键词，AI 自动规划 30 天内容日历",
    icon: Zap,
    href: "/calendar",
    color: "bg-blue-50 text-blue-600 border-blue-200",
  },
  {
    number: "02",
    title: "AI 生成内容",
    description: "基于 AIDA 模型自动生成各平台文案 + 图片设计（视频按需生成）",
    icon: Calendar,
    href: "/calendar",
    color: "bg-purple-50 text-purple-600 border-purple-200",
  },
  {
    number: "03",
    title: "审批内容",
    description: "审阅 AI 生成的文案 + 图片，可内联编辑，一键批准或拒绝",
    icon: CheckSquare,
    href: "/approval",
    color: "bg-green-50 text-green-600 border-green-200",
  },
  {
    number: "04",
    title: "导出 Drive & Sheets",
    description: "批准后一键上传图片/视频到 Google Drive，文案日历写入 Sheets，按平台分 Tab",
    icon: FolderOpen,
    href: "/export",
    color: "bg-orange-50 text-orange-600 border-orange-200",
  },
];

export default function HomePage() {
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">AI 营销内容自动化</h1>
        <p className="text-gray-500">从创建 Campaign 到30天内容日历，AI 生成符合 AIDA 结构的文案和图片，审批后导出到 Google Drive & Sheets</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        {steps.map((step) => (
          <Link
            key={step.number}
            href={step.href}
            className="group bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start gap-4">
              <div className={`w-10 h-10 rounded-lg border flex items-center justify-center shrink-0 ${step.color}`}>
                <step.icon size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs text-gray-400 font-mono mb-1">STEP {step.number}</div>
                <div className="font-semibold text-gray-900 mb-1 text-sm">{step.title}</div>
                <div className="text-xs text-gray-500 leading-relaxed">{step.description}</div>
              </div>
              <ArrowRight size={16} className="text-gray-300 group-hover:text-gray-500 transition-colors shrink-0 mt-1" />
            </div>
          </Link>
        ))}
      </div>

      <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5">
        <h2 className="font-semibold text-indigo-900 mb-2 text-sm">AIDA 文案结构</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { letter: "A", name: "Attention", desc: "3秒抓住注意力" },
            { letter: "I", name: "Interest", desc: "激发持续兴趣" },
            { letter: "D", name: "Desire", desc: "引发购买欲望" },
            { letter: "A", name: "Action", desc: "明确行动号召" },
          ].map((item) => (
            <div key={item.name} className="bg-white rounded-lg p-3 text-center border border-indigo-100">
              <div className="text-2xl font-black text-indigo-600 mb-1">{item.letter}</div>
              <div className="text-xs font-semibold text-gray-800">{item.name}</div>
              <div className="text-xs text-gray-500 mt-0.5">{item.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
