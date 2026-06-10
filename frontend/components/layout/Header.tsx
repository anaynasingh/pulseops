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
    <header className="h-14 px-3 md:px-6 border-b border-slate-800/60 flex items-center gap-2 md:gap-4 shrink-0 bg-[#020817]/50 backdrop-blur-sm sticky top-0 z-10">
      {/* Sidebar toggle — always visible on mobile, subtle on desktop */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="flex items-center justify-center w-8 h-8 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors shrink-0"
        aria-label="Toggle sidebar"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Title */}
      <div className="flex-1 min-w-0">
        <h1 className="text-sm font-semibold text-white truncate">{title}</h1>
        {subtitle && <p className="text-xs text-slate-500 truncate hidden sm:block">{subtitle}</p>}
      </div>

      {/* Actions — hidden on very small screens if needed */}
      {actions && (
        <div className="flex items-center gap-1.5 md:gap-2 shrink-0">
          {actions}
        </div>
      )}

      {/* AI Assistant toggle */}
      <button
        onClick={toggleAIAssistant}
        className="flex items-center gap-1 md:gap-1.5 px-2 md:px-3 py-1.5 rounded-lg bg-indigo-600/15 border border-indigo-600/30 text-indigo-400 text-xs font-medium hover:bg-indigo-600/25 transition-colors shrink-0"
      >
        <span className="ai-pulse">✦</span>
        <span className="hidden sm:inline">AI</span>
        <span className="hidden md:inline"> Assistant</span>
      </button>
    </header>
  );
}
