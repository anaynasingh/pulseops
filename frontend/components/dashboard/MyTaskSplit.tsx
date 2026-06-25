"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "@/lib/api";
import { PRIORITY_CONFIG, PRIORITY_CONFIG_LIGHT } from "@/lib/types";
import { useUIStore } from "@/lib/store";
import { formatDate, getDaysUntil } from "@/lib/utils";
import type { Task } from "@/lib/types";

function TaskCard({
  task, overdue, isLight, done, onComplete,
}: {
  task: Task; overdue: boolean; isLight: boolean; done: boolean; onComplete: (id: string) => void;
}) {
  const PC = isLight ? PRIORITY_CONFIG_LIGHT : PRIORITY_CONFIG;
  const pc = PC[task.priority] ?? PC.medium;
  const daysLeft = getDaysUntil(task.due_date);
  const isDueToday = daysLeft === 0;

  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border transition-all duration-500 ${
        done ? "opacity-0 scale-95 pointer-events-none" :
        overdue
          ? isLight ? "bg-red-50 border-red-200" : "bg-red-950/20 border-red-900/40"
          : isLight ? "bg-slate-50 border-slate-200" : "bg-slate-900/50 border-slate-800/50"
      }`}
    >
      {/* Complete checkbox */}
      <button
        onClick={() => onComplete(task.id)}
        title="Mark complete"
        className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition-all cursor-pointer ${
          done ? "border-green-500 bg-green-500"
          : isLight ? "border-slate-400 hover:border-green-500 hover:bg-green-50"
                    : "border-slate-600 hover:border-green-400 hover:bg-green-900/30"
        }`}
      >
        {done && (
          <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </button>

      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md shrink-0 mt-0.5 ${pc.color} ${pc.bg}`}>
            {task.priority.toUpperCase()}
          </span>
          <p className={`text-sm font-medium leading-snug ${
            done ? "line-through opacity-40" : ""
          } ${isLight ? "text-slate-900" : "text-slate-100"}`}>
            {task.title}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap mt-1 pl-0.5">
          {task.project && (
            <span className={`text-xs font-semibold truncate max-w-[160px] ${isLight ? "text-indigo-700" : "text-indigo-400"}`}>
              {(task.project as { title: string }).title}
            </span>
          )}
          {task.due_date && (
            <span className={`text-xs font-semibold shrink-0 ${
              overdue ? isLight ? "text-red-700" : "text-red-400"
              : isDueToday ? isLight ? "text-amber-700" : "text-amber-400"
              : isLight ? "text-slate-500" : "text-slate-500"
            }`}>
              {overdue ? `${Math.abs(daysLeft!)}d overdue` : isDueToday ? "Due today" : `Due ${formatDate(task.due_date)}`}
            </span>
          )}
          {!task.due_date && (
            <span className={`text-xs ${isLight ? "text-slate-400" : "text-slate-600"}`}>No due date</span>
          )}
        </div>
      </div>
    </div>
  );
}

function Column({
  title, icon, tasks, overdue, isLight, accent, doneIds, onComplete,
}: {
  title: string; icon: string; tasks: Task[]; overdue: boolean; isLight: boolean; accent: string;
  doneIds: Set<string>; onComplete: (id: string) => void;
}) {
  const visible = tasks.filter((t) => !doneIds.has(t.id));
  return (
    <div className={`border rounded-xl p-5 flex flex-col ${isLight ? "bg-white border-slate-200" : "bg-[#0f1629] border-slate-800"}`}>
      <div className="flex items-center gap-2 mb-4">
        <span>{icon}</span>
        <h3 className={`text-base font-bold ${isLight ? "text-slate-900" : "text-white"}`}>{title}</h3>
        <span className={`text-sm font-normal px-2 py-0.5 rounded-full ${accent}`}>{visible.length}</span>
      </div>
      {visible.length === 0 ? (
        <div className="flex-1 flex items-center justify-center py-8">
          <p className={`text-sm ${isLight ? "text-slate-400" : "text-slate-600"}`}>
            {overdue ? "Nothing overdue 🎉" : "Nothing upcoming"}
          </p>
        </div>
      ) : (
        <div>
          <AnimatePresence initial={false}>
            {visible.map((t) => (
              <motion.div
                key={t.id}
                layout
                initial={false}
                exit={{ opacity: 0, height: 0, marginBottom: 0, scale: 0.97 }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                style={{ overflow: "hidden" }}
                className="mb-2.5 last:mb-0"
              >
                <TaskCard
                  task={t}
                  overdue={overdue}
                  isLight={isLight}
                  done={doneIds.has(t.id)}
                  onComplete={onComplete}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}

export function MyTaskSplit({ tasks, loading }: { tasks: Task[]; loading?: boolean }) {
  const { theme } = useUIStore();
  const isLight = theme === "light";
  const queryClient = useQueryClient();
  const [doneIds, setDoneIds] = useState<Set<string>>(new Set());

  const completeMutation = useMutation({
    mutationFn: (id: string) => tasksApi.update(id, { is_completed: true }),
    onSuccess: () => { setTimeout(() => queryClient.invalidateQueries({ queryKey: ["my-dashboard"] }), 600); },
    onError: (_, id) => setDoneIds((p) => { const n = new Set(p); n.delete(id); return n; }),
  });

  const handleComplete = (id: string) => {
    setDoneIds((p) => new Set(p).add(id));
    completeMutation.mutate(id);
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5">
        {[0, 1].map((c) => (
          <div key={c} className={`border rounded-xl p-5 ${isLight ? "bg-white border-slate-200" : "bg-[#0f1629] border-slate-800"}`}>
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className={`h-14 rounded-lg animate-pulse ${isLight ? "bg-slate-100" : "bg-slate-800"}`} />
              ))}
            </div>
          </div>
        ))}
      </div>
    );
  }

  const overdue = tasks.filter((t) => {
    const d = getDaysUntil(t.due_date);
    return d !== null && d < 0;
  });
  const upcoming = tasks.filter((t) => {
    const d = getDaysUntil(t.due_date);
    return d === null || d >= 0;
  });

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-5">
      <Column
        title="Overdue"
        icon="⚠"
        tasks={overdue}
        overdue
        isLight={isLight}
        accent={isLight ? "text-red-700 bg-red-100" : "text-red-400 bg-red-950/40"}
        doneIds={doneIds}
        onComplete={handleComplete}
      />
      <Column
        title="Upcoming"
        icon="📅"
        tasks={upcoming}
        overdue={false}
        isLight={isLight}
        accent={isLight ? "text-indigo-700 bg-indigo-100" : "text-indigo-400 bg-indigo-950/40"}
        doneIds={doneIds}
        onComplete={handleComplete}
      />
    </div>
  );
}
