"use client";

import { useState } from "react";
import { Header } from "@/components/layout/Header";
import { KanbanBoard } from "@/components/kanban/KanbanBoard";
import { useAuthStore } from "@/lib/store";
import Link from "next/link";

const PRIORITY_OPTIONS = [
  { value: "", label: "All Priorities" },
  { value: "urgent", label: "Urgent" },
  { value: "high", label: "High" },
  { value: "medium", label: "Medium" },
  { value: "low", label: "Low" },
];

export default function BoardPage() {
  const { user } = useAuthStore();
  const [search, setSearch] = useState("");
  const [priority, setPriority] = useState("");
  const [scope, setScope] = useState<"mine" | "all">("mine");

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title="Kanban Board"
        subtitle="Drag and drop to update project status"
        actions={
          <Link
            href="/intake"
            className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium rounded-lg transition-colors"
          >
            <span className="ai-pulse">✦</span>
            <span>AI Intake</span>
          </Link>
        }
      />

      {/* Filters bar */}
      <div className="flex items-center gap-3 px-6 py-3 border-b border-slate-800/60 shrink-0">
        {/* Mine / All toggle */}
        <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5 shrink-0">
          <button
            onClick={() => setScope("mine")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
              scope === "mine" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-white"
            }`}
          >
            Mine
          </button>
          <button
            onClick={() => setScope("all")}
            className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
              scope === "all" ? "bg-indigo-600 text-white shadow" : "text-slate-400 hover:text-white"
            }`}
          >
            All
          </button>
        </div>

        <div className="w-px h-4 bg-slate-700 shrink-0" />

        <div className="relative flex-1 max-w-xs">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500 text-xs">⌕</span>
          <input
            type="text"
            placeholder="Search projects…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>

        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
        >
          {PRIORITY_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        <div className="text-xs text-slate-600 ml-auto">
          {scope === "mine" ? `Showing your projects` : "Showing all team projects"}
        </div>
      </div>

      {/* Board */}
      <div className="flex-1 overflow-x-auto overflow-y-hidden px-6 pt-4 kanban-board">
        <KanbanBoard
          searchQuery={search}
          filterPriority={priority}
          filterOwner={scope === "mine" ? user?.id : undefined}
        />
      </div>
    </div>
  );
}
