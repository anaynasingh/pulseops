"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuthStore, useUIStore, useReminderStore } from "@/lib/store";
import { ClaudeSetupModal } from "@/components/layout/ClaudeSetupModal";
import { useState } from "react";
import { cn, initials } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/dashboard",  icon: "⬡", label: "Dashboard" },
  { href: "/day",        icon: "◷", label: "Day View" },
  { href: "/board",      icon: "⊞", label: "Kanban Board" },
  { href: "/gantt",      icon: "▬", label: "Gantt Chart" },
  { href: "/intake",     icon: "✦", label: "AI Intake" },
  { href: "/meetings",   icon: "◎", label: "Meetings" },
  { href: "/emails",     icon: "✉", label: "Emails" },
  { href: "/search",     icon: "⌕", label: "Search" },
  { href: "/analytics",  icon: "◈", label: "Analytics" },
];

export function Sidebar({ onNavClick }: { onNavClick?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, clearAuth } = useAuthStore();
  const { sidebarOpen, toggleCommandPalette, theme, toggleTheme } = useUIStore();
  const [showClaudeSetup, setShowClaudeSetup] = useState(false);
  const { enabled: reminderEnabled, intervalMin, setEnabled: setReminderEnabled, setIntervalMin, show } = useReminderStore();

  if (!sidebarOpen) return null;

  return (
    <aside className="w-64 h-screen bg-[#080f20] border-r border-slate-800/60 flex flex-col shrink-0 overflow-y-auto">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-slate-800/60">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center shrink-0">
            <span className="text-white font-bold text-xs">P</span>
          </div>
          <span className="text-white font-semibold text-sm tracking-wide">PulseOps</span>
          <span className="ml-auto text-[10px] text-indigo-400 bg-indigo-950 border border-indigo-800 rounded px-1.5 py-0.5 font-medium">
            AI
          </span>
        </div>
      </div>

      {/* Command palette trigger */}
      <div className="px-3 pt-3 pb-2">
        <button
          onClick={toggleCommandPalette}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-900/60 border border-slate-800 text-slate-500 text-xs hover:border-slate-700 transition-colors"
        >
          <span>⌕</span>
          <span>Search…</span>
          <kbd className="ml-auto text-[10px] bg-slate-800 px-1.5 py-0.5 rounded text-slate-600 font-mono">⌘K</kbd>
        </button>
      </div>

      {/* Nav */}
      <nav className="px-3 py-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavClick}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-smooth",
                active
                  ? "bg-indigo-600/15 text-indigo-300 border-l-2 border-indigo-500 pl-[10px]"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              )}
            >
              <span className="text-base leading-none">{item.icon}</span>
              <span>{item.label}</span>
              {item.href === "/intake" && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-500 ai-pulse" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Claude connection status */}
      <div className="px-3 py-2 border-t border-slate-800/60">
        <button
          onClick={() => setShowClaudeSetup(true)}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-slate-800/50 transition-smooth group"
          title={user?.mcp_setup_done ? "Claude connected — click to view setup guide" : "Claude not connected — click to set up"}
        >
          {/* Status dot */}
          <span className={`w-2 h-2 rounded-full shrink-0 ${user?.mcp_setup_done ? "bg-green-400" : "bg-amber-400 animate-pulse"}`} />
          <span className={`text-xs ${user?.mcp_setup_done ? "text-green-400" : "text-amber-400"}`}>
            Claude {user?.mcp_setup_done ? "connected" : "not connected"}
          </span>
          <span className="ml-auto text-[10px] text-slate-600 group-hover:text-slate-400 transition-colors">
            {user?.mcp_setup_done ? "guide" : "setup →"}
          </span>
        </button>
      </div>

      {showClaudeSetup && user && (
        <ClaudeSetupModal
          userName={user.name}
          onDone={() => setShowClaudeSetup(false)}
          onSkip={() => setShowClaudeSetup(false)}
        />
      )}

      {/* Light / Dark mode toggle */}
      <div className="px-3 py-2 border-t border-slate-800/60">
        <button
          onClick={toggleTheme}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-400 hover:text-slate-200 hover:bg-slate-800/50 transition-smooth"
          title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
        >
          <span className="text-base leading-none">{theme === "light" ? "◑" : "☀"}</span>
          <span className="text-xs">{theme === "light" ? "Dark mode" : "Light mode"}</span>
          <span className="ml-auto text-[10px] text-slate-600 bg-slate-800/60 px-1.5 py-0.5 rounded">
            {theme === "light" ? "off" : "on"}
          </span>
        </button>
      </div>

      {/* Hourly reminders */}
      <div className="px-3 py-3 border-t border-slate-800/60">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 text-sm">⏱</span>
            <span className="text-xs text-slate-400">Focus reminders</span>
          </div>
          <button
            onClick={() => setReminderEnabled(!reminderEnabled)}
            role="switch"
            aria-checked={reminderEnabled}
            aria-label="Focus reminders"
            className={cn(
              "relative w-8 h-4 rounded-full transition-colors shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-[#080f20]",
              reminderEnabled ? "bg-indigo-600" : "bg-slate-700"
            )}
            title={reminderEnabled ? "Disable reminders" : "Enable hourly focus reminders"}
          >
            <span
              className={cn(
                "absolute top-0.5 left-0.5 w-3 h-3 rounded-full bg-white transition-transform",
                reminderEnabled ? "translate-x-4" : "translate-x-0"
              )}
            />
          </button>
        </div>
        {reminderEnabled && (
          <div className="flex items-center gap-2">
            <select
              value={intervalMin}
              onChange={(e) => setIntervalMin(Number(e.target.value))}
              className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-400 focus:outline-none focus:border-indigo-500"
            >
              <option value={15}>Every 15 min</option>
              <option value={30}>Every 30 min</option>
              <option value={60}>Every 1 hr</option>
              <option value={120}>Every 2 hr</option>
            </select>
            <button
              onClick={show}
              className="text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors whitespace-nowrap"
              title="Preview reminder now"
            >
              Preview
            </button>
          </div>
        )}
      </div>

      {/* User */}
      {user && (
        <div className="px-3 py-3 border-t border-slate-800/60">
          <div className="flex items-center gap-2.5 px-2">
            <div className="w-7 h-7 rounded-full bg-indigo-700 flex items-center justify-center shrink-0">
              <span className="text-white text-xs font-medium">{initials(user.name)}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs text-white font-medium truncate">{user.name}</p>
              <p className="text-[10px] text-slate-500 truncate">{user.role}</p>
            </div>
            <button
              onClick={() => { clearAuth(); router.push("/login"); }}
              className="text-slate-600 hover:text-slate-400 text-xs transition-colors"
              title="Sign out"
            >
              ⎋
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
