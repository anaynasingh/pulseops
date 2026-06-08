"use client";

import { useQuery } from "@tanstack/react-query";
import { useReminderStore } from "@/lib/store";
import { tasksApi } from "@/lib/api";
import { PRIORITY_CONFIG } from "@/lib/types";
import type { Task } from "@/lib/types";

const PRIORITY_ORDER: Record<string, number> = { urgent: 0, high: 1, medium: 2, low: 3 };

function topTasks(tasks: Task[]): Task[] {
  return tasks
    .filter((t) => !t.is_completed)
    .sort((a, b) => {
      const pd = (PRIORITY_ORDER[a.priority] ?? 4) - (PRIORITY_ORDER[b.priority] ?? 4);
      if (pd !== 0) return pd;
      if (a.due_date && b.due_date) return a.due_date.localeCompare(b.due_date);
      if (a.due_date) return -1;
      if (b.due_date) return 1;
      return 0;
    })
    .slice(0, 3);
}

export function ReminderModal() {
  const { visible, dismiss, snooze } = useReminderStore();

  const { data: tasks = [] } = useQuery<Task[]>({
    queryKey: ["tasks-reminder"],
    queryFn: () => tasksApi.list(),
    enabled: visible,
    staleTime: 30_000,
  });

  if (!visible) return null;

  const focus = topTasks(tasks);
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-[#0f1629] border border-indigo-800/50 rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center gap-3">
          <span className="text-indigo-400 text-lg ai-pulse">⏱</span>
          <div className="flex-1">
            <p className="text-sm font-semibold text-white">Hourly Focus Check</p>
            <p className="text-[11px] text-slate-500">{now} — what are you working on?</p>
          </div>
        </div>

        {/* Task list */}
        <div className="px-5 py-4">
          {focus.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-2">
              No incomplete tasks found. Nice work!
            </p>
          ) : (
            <div className="space-y-2.5">
              <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-3">
                Top priorities right now
              </p>
              {focus.map((task, i) => {
                const cfg = PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium;
                return (
                  <div key={task.id} className="flex items-start gap-3">
                    <span className="text-slate-600 text-xs mt-0.5 w-3 shrink-0">{i + 1}.</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-200 leading-snug">{task.title}</p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`text-[10px] font-medium ${cfg.color}`}>{cfg.label}</span>
                        {task.due_date && (
                          <span className="text-[10px] text-slate-600">due {task.due_date}</span>
                        )}
                        {task.assignee && (
                          <span className="text-[10px] text-slate-600">
                            → {task.assignee.name.split(" ")[0]}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="px-5 py-3 border-t border-slate-800 flex items-center gap-2">
          <button
            onClick={() => snooze(15)}
            className="flex-1 py-2 text-xs text-slate-400 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors"
          >
            Snooze 15 min
          </button>
          <button
            onClick={() => snooze(30)}
            className="flex-1 py-2 text-xs text-slate-400 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg transition-colors"
          >
            Snooze 30 min
          </button>
          <button
            onClick={dismiss}
            className="flex-1 py-2 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium transition-colors"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
