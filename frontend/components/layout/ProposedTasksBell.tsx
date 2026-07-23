"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Loader2, X } from "lucide-react";
import { format } from "date-fns";
import { proposedTasksApi } from "@/lib/api";
import { PRIORITY_CONFIG } from "@/lib/types";
import type { ProposedTask, ProposedTaskConfirmResult } from "@/lib/types";

interface MeetingGroup {
  key: string;
  meetingTitle: string;
  meetingDate: string | null;
  items: ProposedTask[];
}

/**
 * Top-right bell surfacing PROPOSED tasks extracted from Teams meeting
 * transcripts. Confirm semantics (Orchestrator ruling 2026-07-22):
 * "Add selected" sends only the checked ids as accepted_ids — unchecked
 * items are NOT sent and remain pending for later triage. Dismissal is a
 * separate explicit affordance (per-item X, "Dismiss unchecked").
 */
export function ProposedTasksBell() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  // Ids the user has explicitly unchecked — everything else defaults to checked.
  const [uncheckedIds, setUncheckedIds] = useState<Set<string>>(new Set());
  const panelRef = useRef<HTMLDivElement>(null);

  // Badge count — polls every 60s (R1-8, matches dashboard precedent)
  const { data: countData } = useQuery<{ pending: number }>({
    queryKey: ["proposed-tasks", "count"],
    queryFn: () => proposedTasksApi.count(),
    refetchInterval: 60_000,
  });
  const pendingCount = countData?.pending ?? 0;

  // Panel list — only fetched while the panel is open
  const { data: proposals, isLoading } = useQuery<ProposedTask[]>({
    queryKey: ["proposed-tasks", "list", "pending"],
    queryFn: () => proposedTasksApi.list("pending"),
    enabled: open,
  });

  const confirmMutation = useMutation<
    ProposedTaskConfirmResult,
    Error,
    { acceptedIds: string[]; dismissedIds: string[] }
  >({
    mutationFn: ({ acceptedIds, dismissedIds }) =>
      proposedTasksApi.confirm(acceptedIds, dismissedIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["proposed-tasks"] });
      queryClient.invalidateQueries({ queryKey: ["projects-kanban"] });
      queryClient.invalidateQueries({ queryKey: ["my-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const groups = useMemo<MeetingGroup[]>(() => {
    const byMeeting = new Map<string, MeetingGroup>();
    for (const item of proposals ?? []) {
      const key = `${item.meeting_title}|${item.meeting_date ?? ""}`;
      const group = byMeeting.get(key);
      if (group) {
        group.items.push(item);
      } else {
        byMeeting.set(key, {
          key,
          meetingTitle: item.meeting_title,
          meetingDate: item.meeting_date,
          items: [item],
        });
      }
    }
    return Array.from(byMeeting.values());
  }, [proposals]);

  const allItems = proposals ?? [];
  const checkedIds = allItems.filter((p) => !uncheckedIds.has(p.id)).map((p) => p.id);
  const explicitlyUncheckedIds = allItems
    .filter((p) => uncheckedIds.has(p.id))
    .map((p) => p.id);

  const toggleChecked = (id: string) => {
    setUncheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleAddSelected = () => {
    if (checkedIds.length === 0) return;
    // Unchecked items are intentionally omitted — they stay pending.
    confirmMutation.mutate({ acceptedIds: checkedIds, dismissedIds: [] });
  };

  const handleDismissUnchecked = () => {
    if (explicitlyUncheckedIds.length === 0) return;
    confirmMutation.mutate({ acceptedIds: [], dismissedIds: explicitlyUncheckedIds });
  };

  const handleDismissOne = (id: string) => {
    confirmMutation.mutate({ acceptedIds: [], dismissedIds: [id] });
  };

  return (
    <div className="relative shrink-0" ref={panelRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative flex items-center justify-center w-8 h-8 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
        aria-label="Proposed tasks"
        aria-expanded={open}
      >
        <Bell className="w-4 h-4" />
        {pendingCount > 0 && (
          <span
            className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-indigo-600 text-white text-[10px] font-semibold flex items-center justify-center"
            aria-label={`${pendingCount} pending proposed tasks`}
          >
            {pendingCount > 99 ? "99+" : pendingCount}
          </span>
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-10 w-[22rem] max-h-[70vh] overflow-y-auto rounded-xl border border-slate-700 bg-[#0b1220] shadow-2xl z-30"
          role="dialog"
          aria-label="Proposed tasks panel"
        >
          <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <h2 className="text-xs font-semibold text-white">Proposed tasks</h2>
            <span className="text-[10px] text-slate-500">From meeting transcripts</span>
          </div>

          {isLoading && (
            <div className="flex items-center justify-center gap-2 py-8 text-slate-500 text-xs">
              <Loader2 className="w-4 h-4 animate-spin" />
              Loading…
            </div>
          )}

          {!isLoading && allItems.length === 0 && (
            <div className="py-8 px-4 text-center text-xs text-slate-500">
              No proposed tasks. You&apos;re all caught up.
            </div>
          )}

          {!isLoading &&
            groups.map((group) => (
              <div key={group.key} className="px-4 py-3 border-b border-slate-800/60">
                <div className="mb-2">
                  <p className="text-xs font-medium text-slate-200 truncate">
                    {group.meetingTitle}
                  </p>
                  {group.meetingDate && (
                    <p className="text-[10px] text-slate-500">
                      {format(new Date(`${group.meetingDate}T00:00:00`), "d MMM yyyy")}
                    </p>
                  )}
                </div>
                <ul className="space-y-2">
                  {group.items.map((item) => (
                    <li key={item.id} className="flex items-start gap-2">
                      <input
                        type="checkbox"
                        checked={!uncheckedIds.has(item.id)}
                        onChange={() => toggleChecked(item.id)}
                        aria-label={`Select ${item.title}`}
                        className="mt-0.5 w-3.5 h-3.5 rounded border-slate-600 bg-slate-900 accent-indigo-600 shrink-0"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-xs text-slate-300 leading-snug">{item.title}</p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span
                            className={`text-[10px] px-1.5 py-px rounded ${PRIORITY_CONFIG[item.priority].bg} ${PRIORITY_CONFIG[item.priority].color}`}
                          >
                            {PRIORITY_CONFIG[item.priority].label}
                          </span>
                          {item.assignee_hint && (
                            <span className="text-[10px] text-slate-500 truncate">
                              {item.assignee_hint}
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleDismissOne(item.id)}
                        className="text-slate-500 hover:text-red-400 transition-colors shrink-0"
                        aria-label={`Dismiss ${item.title}`}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ))}

          {!isLoading && allItems.length > 0 && (
            <div className="px-4 py-3 flex items-center gap-2 sticky bottom-0 bg-[#0b1220] border-t border-slate-800">
              <button
                onClick={handleAddSelected}
                disabled={checkedIds.length === 0 || confirmMutation.isPending}
                className="flex-1 px-3 py-1.5 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Add selected ({checkedIds.length})
              </button>
              <button
                onClick={handleDismissUnchecked}
                disabled={explicitlyUncheckedIds.length === 0 || confirmMutation.isPending}
                className="px-3 py-1.5 rounded-lg border border-slate-700 text-slate-400 text-xs font-medium hover:text-white hover:bg-slate-800/60 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Dismiss unchecked
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
