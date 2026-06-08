"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "@/lib/api";
import { PRIORITY_CONFIG } from "@/lib/types";
import { formatDate, getDaysUntil } from "@/lib/utils";
import type { Task } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  todo: "text-slate-400",
  in_progress: "text-blue-400",
  review: "text-purple-400",
  blocked: "text-red-400",
  done: "text-green-400",
};

export function MyTasksList({ tasks, loading }: { tasks: Task[]; loading?: boolean }) {
  const queryClient = useQueryClient();
  // Track which tasks have been optimistically completed (instant UI feedback)
  const [doneIds, setDoneIds] = useState<Set<string>>(new Set());

  const completeMutation = useMutation({
    mutationFn: (taskId: string) => tasksApi.update(taskId, { is_completed: true }),
    onSuccess: () => {
      // Wait 600ms (fade animation) then refetch to remove from list
      setTimeout(() => {
        queryClient.invalidateQueries({ queryKey: ["my-dashboard"] });
      }, 600);
    },
    onError: (_, taskId) => {
      // Revert on error
      setDoneIds((prev) => {
        const next = new Set(prev);
        next.delete(taskId);
        return next;
      });
    },
  });

  const handleComplete = (taskId: string) => {
    // Instantly mark done in UI
    setDoneIds((prev) => new Set(prev).add(taskId));
    completeMutation.mutate(taskId);
  };

  // Filter out already-done tasks from local state
  const visibleTasks = tasks.filter((t) => !doneIds.has(t.id));

  return (
    <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span>📋</span>
          <span>My Tasks</span>
          {!loading && tasks.length > 0 && (
            <span className="text-xs font-normal text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded-full">
              {visibleTasks.length}
            </span>
          )}
        </h3>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 bg-slate-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : visibleTasks.length === 0 ? (
        <div className="text-center py-10">
          <p className="text-2xl mb-2">🎉</p>
          <p className="text-slate-400 text-sm font-medium">All caught up!</p>
          <p className="text-slate-600 text-xs mt-1">No tasks assigned to you.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {visibleTasks.map((task) => {
            const daysLeft = getDaysUntil(task.due_date);
            const isOverdue = daysLeft !== null && daysLeft < 0;
            const isDueToday = daysLeft === 0;
            const isDone = doneIds.has(task.id);

            return (
              <div
                key={task.id}
                className={`flex items-start gap-3 p-3 rounded-lg border transition-all duration-500 ${
                  isDone
                    ? "opacity-0 scale-95 pointer-events-none"
                    : isOverdue
                    ? "bg-red-950/20 border-red-900/40 hover:border-red-800/60"
                    : "bg-slate-900/50 border-slate-800/50 hover:border-slate-700"
                }`}
              >
                {/* Checkbox */}
                <button
                  onClick={() => handleComplete(task.id)}
                  className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all cursor-pointer ${
                    isDone
                      ? "border-green-500 bg-green-500"
                      : "border-slate-600 hover:border-green-400 hover:bg-green-900/30"
                  }`}
                  title="Mark complete"
                >
                  {isDone && (
                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </button>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start gap-2 flex-wrap">
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                        PRIORITY_CONFIG[task.priority]?.color ?? "text-slate-400"
                      } ${PRIORITY_CONFIG[task.priority]?.bg ?? "bg-slate-800"}`}
                    >
                      {task.priority.toUpperCase()}
                    </span>
                    <p className={`text-sm leading-snug flex-1 transition-all ${isDone ? "line-through text-slate-500" : "text-slate-200"}`}>
                      {task.title}
                    </p>
                  </div>
                  <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                    {task.project && (
                      <span className="text-[11px] text-indigo-400 truncate max-w-[160px]">
                        {(task.project as any).title}
                      </span>
                    )}
                    <span className={`text-[11px] ${STATUS_COLORS[task.status] ?? "text-slate-500"}`}>
                      {task.status.replace("_", " ")}
                    </span>
                    {task.due_date && (
                      <span
                        className={`text-[11px] shrink-0 ${
                          isOverdue
                            ? "text-red-400 font-medium"
                            : isDueToday
                            ? "text-amber-400 font-medium"
                            : "text-slate-500"
                        }`}
                      >
                        {isOverdue
                          ? `${Math.abs(daysLeft!)}d overdue`
                          : isDueToday
                          ? "Due today"
                          : `Due ${formatDate(task.due_date)}`}
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
  );
}
