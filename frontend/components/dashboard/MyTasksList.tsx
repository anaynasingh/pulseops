"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "@/lib/api";
import { PRIORITY_CONFIG, PRIORITY_CONFIG_LIGHT } from "@/lib/types";
import { useUIStore } from "@/lib/store";
import { formatDate, getDaysUntil } from "@/lib/utils";
import type { Task } from "@/lib/types";

export function MyTasksList({ tasks, loading }: { tasks: Task[]; loading?: boolean }) {
  const queryClient = useQueryClient();
  const { theme } = useUIStore();
  const isLight = theme === "light";
  const PC = isLight ? PRIORITY_CONFIG_LIGHT : PRIORITY_CONFIG;

  const [doneIds, setDoneIds] = useState<Set<string>>(new Set());
  const [retiredIds, setRetiredIds] = useState<Set<string>>(new Set());
  const [confirmRetire, setConfirmRetire] = useState<string | null>(null);

  const completeMutation = useMutation({
    mutationFn: (id: string) => tasksApi.update(id, { is_completed: true }),
    onSuccess: () => { setTimeout(() => queryClient.invalidateQueries({ queryKey: ["my-dashboard"] }), 600); },
    onError: (_, id) => setDoneIds(p => { const n = new Set(p); n.delete(id); return n; }),
  });
  const retireMutation = useMutation({
    mutationFn: (id: string) => tasksApi.update(id, { status: "cancelled" }),
    onSuccess: () => { setTimeout(() => queryClient.invalidateQueries({ queryKey: ["my-dashboard"] }), 600); },
    onError: (_, id) => setRetiredIds(p => { const n = new Set(p); n.delete(id); return n; }),
  });

  const handleComplete = (id: string) => { setDoneIds(p => new Set(p).add(id)); completeMutation.mutate(id); };
  const handleRetire  = (id: string) => { setConfirmRetire(null); setRetiredIds(p => new Set(p).add(id)); retireMutation.mutate(id); };

  const visible = tasks.filter(t => !doneIds.has(t.id) && !retiredIds.has(t.id));

  if (loading) return (
    <div className={`border rounded-xl p-6 ${isLight ? "bg-white border-slate-200" : "bg-[#0f1629] border-slate-800"}`}>
      <div className="space-y-3">
        {[...Array(4)].map((_, i) => (
          <div key={i} className={`h-16 rounded-lg animate-pulse ${isLight ? "bg-slate-100" : "bg-slate-800"}`} />
        ))}
      </div>
    </div>
  );

  return (
    <div className={`border rounded-xl p-6 ${isLight ? "bg-white border-slate-200" : "bg-[#0f1629] border-slate-800"}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className={`text-base font-bold flex items-center gap-2 ${isLight ? "text-slate-900" : "text-white"}`}>
          <span>📋</span>
          <span>My Tasks</span>
          {visible.length > 0 && (
            <span className={`text-sm font-normal px-2 py-0.5 rounded-full ${isLight ? "text-slate-500 bg-slate-100" : "text-slate-500 bg-slate-800"}`}>
              {visible.length}
            </span>
          )}
        </h3>
      </div>

      {visible.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-3xl mb-3">🎉</p>
          <p className={`text-base font-medium ${isLight ? "text-slate-600" : "text-slate-400"}`}>All caught up!</p>
          <p className={`text-sm mt-1 ${isLight ? "text-slate-400" : "text-slate-600"}`}>No tasks assigned to you.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map(task => {
            const daysLeft = getDaysUntil(task.due_date);
            const isOverdue  = daysLeft !== null && daysLeft < 0;
            const isDueToday = daysLeft === 0;
            const isGone = doneIds.has(task.id) || retiredIds.has(task.id);
            const pc = PC[task.priority] ?? PC.medium;

            return (
              <div key={task.id} className={`flex items-start gap-4 p-4 rounded-xl border transition-all duration-500 group ${
                isGone ? "opacity-0 scale-95 pointer-events-none" :
                isOverdue
                  ? isLight ? "bg-red-50 border-red-200" : "bg-red-950/20 border-red-900/40"
                  : isLight ? "bg-slate-50 border-slate-200 hover:border-slate-300 hover:bg-white"
                             : "bg-slate-900/50 border-slate-800/50 hover:border-slate-700"
              }`}>

                {/* Checkbox */}
                <button onClick={() => handleComplete(task.id)}
                  className={`mt-0.5 w-6 h-6 rounded-full border-2 flex items-center justify-center shrink-0 transition-all cursor-pointer ${
                    doneIds.has(task.id)
                      ? "border-green-500 bg-green-500"
                      : isLight
                      ? "border-slate-400 hover:border-green-500 hover:bg-green-50"
                      : "border-slate-600 hover:border-green-400 hover:bg-green-900/30"
                  }`} title="Mark complete">
                  {doneIds.has(task.id) && (
                    <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </button>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  {/* Priority badge + title */}
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className={`text-xs font-bold px-2.5 py-1 rounded-md shrink-0 ${pc.color} ${pc.bg}`}>
                      {task.priority.toUpperCase()}
                    </span>
                    <p className={`text-sm font-semibold leading-snug ${
                      doneIds.has(task.id) ? "line-through opacity-40" :
                      isLight ? "text-slate-900" : "text-slate-100"
                    }`}>
                      {task.title}
                    </p>
                  </div>

                  {/* Meta row */}
                  <div className="flex items-center gap-3 flex-wrap">
                    {task.project && (
                      <span className={`text-xs font-semibold truncate max-w-[200px] ${isLight ? "text-indigo-700" : "text-indigo-400"}`}>
                        {(task.project as any).title}
                      </span>
                    )}
                    <span className={`text-xs ${isLight ? "text-slate-500" : "text-slate-500"}`}>
                      {task.status.replace("_", " ")}
                    </span>
                    {task.due_date && (
                      <span className={`text-xs font-semibold shrink-0 ${
                        isOverdue   ? isLight ? "text-red-700"   : "text-red-400"   :
                        isDueToday  ? isLight ? "text-amber-700" : "text-amber-400" :
                                      isLight ? "text-slate-500" : "text-slate-500"
                      }`}>
                        {isOverdue ? `${Math.abs(daysLeft!)}d overdue` : isDueToday ? "Due today" : `Due ${formatDate(task.due_date)}`}
                      </span>
                    )}
                  </div>
                </div>

                {/* Retire */}
                <div className="shrink-0">
                  {confirmRetire === task.id ? (
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs ${isLight ? "text-slate-500" : "text-slate-500"}`}>Retire?</span>
                      <button onClick={() => handleRetire(task.id)}
                        className={`text-xs px-2 py-1 rounded font-medium transition-colors ${isLight ? "bg-amber-100 text-amber-800 hover:bg-amber-200" : "bg-amber-900/40 text-amber-400 hover:bg-amber-900/60"}`}>
                        Yes
                      </button>
                      <button onClick={() => setConfirmRetire(null)}
                        className={`text-xs px-2 py-1 rounded font-medium transition-colors ${isLight ? "bg-slate-200 text-slate-700 hover:bg-slate-300" : "bg-slate-800 text-slate-400 hover:bg-slate-700"}`}>
                        No
                      </button>
                    </div>
                  ) : (
                    <button onClick={() => setConfirmRetire(task.id)}
                      className={`opacity-0 group-hover:opacity-100 transition-opacity w-7 h-7 rounded-lg flex items-center justify-center ${isLight ? "text-slate-400 hover:text-red-600 hover:bg-red-50" : "text-slate-600 hover:text-amber-400 hover:bg-amber-900/20"}`}
                      title="Retire this task">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
