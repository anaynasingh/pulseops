"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useUIStore } from "@/lib/store";
import { searchApi } from "@/lib/api";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import type { Project, Task } from "@/lib/types";

interface SearchResults {
  projects: Project[];
  tasks: Task[];
}

const QUICK_LINKS = [
  { label: "Dashboard", href: "/dashboard", icon: "⬡" },
  { label: "Kanban Board", href: "/board", icon: "⊞" },
  { label: "AI Intake", href: "/intake", icon: "✦" },
  { label: "Meetings", href: "/meetings", icon: "◎" },
  { label: "Emails", href: "/emails", icon: "✉" },
  { label: "Semantic Search", href: "/search", icon: "⌕" },
  { label: "Analytics", href: "/analytics", icon: "◈" },
];

export function CommandPalette() {
  const router = useRouter();
  const { toggleCommandPalette } = useUIStore();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const { data: results } = useQuery<SearchResults>({
    queryKey: ["search", query],
    queryFn: () => searchApi.keyword(query),
    enabled: query.length >= 2,
  });

  const allItems = [
    ...(query.length < 2
      ? QUICK_LINKS.map((l) => ({ type: "link" as const, ...l }))
      : []),
    ...(results?.projects ?? []).map((p) => ({
      type: "project" as const,
      label: p.title,
      href: `/projects/${p.id}`,
      icon: "◈",
      sub: p.status.replace("_", " "),
    })),
    ...(results?.tasks ?? []).map((t) => ({
      type: "task" as const,
      label: t.title,
      href: `/projects/${t.project_id}`,
      icon: "○",
      sub: "task",
    })),
  ];

  const navigate = useCallback((href: string) => {
    router.push(href);
    toggleCommandPalette();
  }, [router, toggleCommandPalette]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        toggleCommandPalette();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, allItems.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        e.preventDefault();
        const item = allItems[selectedIndex];
        if (item) navigate(item.href);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggleCommandPalette, selectedIndex, allItems, navigate]);

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 px-4">
      {/* Backdrop */}
      <div className="absolute inset-0 cmd-backdrop" onClick={toggleCommandPalette} />

      {/* Palette */}
      <div className="relative w-full max-w-lg bg-[#0f1629] border border-slate-700 rounded-2xl shadow-2xl overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-800">
          <span className="text-slate-500">⌕</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelectedIndex(0); }}
            placeholder="Search projects, tasks, or navigate…"
            className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
          />
          <kbd className="text-[10px] bg-slate-800 text-slate-600 px-1.5 py-0.5 rounded font-mono">ESC</kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto py-1.5">
          {allItems.length === 0 && query.length >= 2 && (
            <p className="text-center text-slate-600 text-xs py-8">No results for &quot;{query}&quot;</p>
          )}

          {query.length < 2 && (
            <p className="text-[10px] text-slate-600 uppercase tracking-wide px-4 pt-1 pb-2">
              Quick navigation
            </p>
          )}

          {allItems.map((item, i) => (
            <button
              key={i}
              onClick={() => navigate(item.href)}
              className={cn(
                "w-full flex items-center gap-3 px-4 py-2.5 text-sm transition-colors text-left",
                i === selectedIndex
                  ? "bg-indigo-600/15 text-white"
                  : "text-slate-300 hover:bg-slate-800/60"
              )}
            >
              <span className="text-slate-500 shrink-0">{item.icon}</span>
              <span className="flex-1 truncate">{item.label}</span>
              {"sub" in item && item.sub && (
                <span className="text-[11px] text-slate-600 shrink-0">{item.sub}</span>
              )}
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-slate-800 flex items-center gap-4 text-[10px] text-slate-600">
          <span>↵ to select</span>
          <span>↑↓ navigate</span>
          <span>ESC to close</span>
        </div>
      </div>
    </div>
  );
}
