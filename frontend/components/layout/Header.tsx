"use client";

import { useUIStore } from "@/lib/store";

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function Header({ title, subtitle, actions }: HeaderProps) {
  const { toggleAIAssistant, setSidebarOpen, sidebarOpen } = useUIStore();

  return (
    <header className="h-14 px-6 border-b border-slate-800/60 flex items-center gap-4 shrink-0 bg-[#020817]/50 backdrop-blur-sm sticky top-0 z-10">
      {/* Sidebar toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="text-slate-500 hover:text-slate-300 transition-colors text-lg leading-none"
      >
        ☰
      </button>

      {/* Title */}
      <div className="flex-1">
        <h1 className="text-sm font-semibold text-white">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      </div>

      {/* Actions */}
      {actions && <div className="flex items-center gap-2">{actions}</div>}

      {/* AI Assistant toggle */}
      <button
        onClick={toggleAIAssistant}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/15 border border-indigo-600/30 text-indigo-400 text-xs font-medium hover:bg-indigo-600/25 transition-colors"
      >
        <span className="ai-pulse">✦</span>
        <span>AI Assistant</span>
      </button>
    </header>
  );
}
