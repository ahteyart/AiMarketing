"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart2, Calendar, CheckSquare, FileSpreadsheet, Search, Zap } from "lucide-react";
import clsx from "clsx";

const navItems = [
  { href: "/", label: "概览", icon: BarChart2 },
  { href: "/trends", label: "热门调研", icon: Search },
  { href: "/calendar", label: "30天日历", icon: Calendar },
  { href: "/approval", label: "待审批", icon: CheckSquare },
  { href: "/export", label: "导出 Sheets", icon: FileSpreadsheet },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="w-56 bg-white border-r border-gray-200 flex flex-col py-6 px-3 shrink-0">
      <div className="flex items-center gap-2 px-3 mb-8">
        <Zap className="text-indigo-600" size={22} />
        <span className="font-bold text-gray-900 text-sm leading-tight">AI Marketing<br />Automation</span>
      </div>
      <nav className="flex flex-col gap-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
              pathname === href
                ? "bg-indigo-50 text-indigo-700"
                : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
            )}
          >
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
