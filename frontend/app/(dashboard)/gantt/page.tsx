"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { useMemo, useRef } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface GanttTask {
  id: string;
  title: string;
  type: "task";
  assignee?: string | null;
  start_date: string;
  end_date: string;
  is_completed: boolean;
  priority: string;
}

interface GanttProject {
  id: string;
  title: string;
  type: "project";
  status: string;
  priority: string;
  start_date: string;
  end_date: string;
  progress: number;
  subtasks: GanttTask[];
}

interface GanttData {
  items: GanttProject[];
  min_date: string;
  max_date: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function parseDate(s: string): Date {
  return new Date(s + "T00:00:00");
}

function daysBetween(a: Date, b: Date): number {
  return Math.floor((b.getTime() - a.getTime()) / 86400000);
}

function formatMonth(d: Date): string {
  return d.toLocaleString("default", { month: "short", year: "2-digit" });
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

const PRIORITY_BAR_COLORS: Record<string, string> = {
  urgent: "bg-red-500",
  high: "bg-amber-500",
  medium: "bg-blue-500",
  low: "bg-slate-500",
};

const PRIORITY_TEXT_COLORS: Record<string, string> = {
  urgent: "text-red-400",
  high: "text-amber-400",
  medium: "text-blue-400",
  low: "text-slate-500",
};

// ── Month column headers ───────────────────────────────────────────────────────

function buildMonthColumns(minDate: Date, totalDays: number): { label: string; offsetDays: number; widthDays: number }[] {
  const cols: { label: string; offsetDays: number; widthDays: number }[] = [];
  let cursor = new Date(minDate);
  cursor.setDate(1); // start of month

  while (daysBetween(minDate, cursor) < totalDays) {
    const monthStart = new Date(cursor);
    const nextMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    const monthEnd = nextMonth;

    const offsetDays = Math.max(0, daysBetween(minDate, monthStart));
    const endOffset = Math.min(totalDays, daysBetween(minDate, monthEnd));
    const widthDays = endOffset - offsetDays;

    if (widthDays > 0) {
      cols.push({ label: formatMonth(monthStart), offsetDays, widthDays });
    }
    cursor = nextMonth;
  }
  return cols;
}

// ── Bar component ──────────────────────────────────────────────────────────────

function GanttBar({
  startOffset,
  endOffset,
  totalDays,
  color,
  progress,
  label,
  tooltip,
  isCompleted,
  dayPx,
}: {
  startOffset: number;
  endOffset: number;
  totalDays: number;
  color: string;
  progress?: number;
  label?: string;
  tooltip: string;
  isCompleted?: boolean;
  dayPx: number;
}) {
  const left = (startOffset / totalDays) * 100;
  const width = Math.max(((endOffset - startOffset) / totalDays) * 100, 0.5);

  return (
    <div
      className="absolute top-1/2 -translate-y-1/2 rounded group"
      style={{ left: `${left}%`, width: `${width}%`, minWidth: "4px" }}
      title={tooltip}
    >
      <div className={`relative h-5 rounded overflow-hidden ${isCompleted ? "bg-green-800/60" : "bg-slate-700/50"}`}>
        {/* fill layer */}
        <div
          className={`absolute left-0 top-0 bottom-0 rounded ${isCompleted ? "bg-green-600" : color}`}
          style={{ width: progress !== undefined ? `${progress}%` : "100%" }}
        />
        {/* label */}
        {label && (
          <span className="absolute inset-0 flex items-center px-1.5 text-[9px] text-white font-medium truncate whitespace-nowrap z-10 pointer-events-none">
            {label}
          </span>
        )}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function GanttPage() {
  const { data, isLoading, error } = useQuery<GanttData>({
    queryKey: ["gantt"],
    queryFn: () => analyticsApi.gantt(),
    staleTime: 30_000,
  });

  const containerRef = useRef<HTMLDivElement>(null);

  const { minDate, maxDate, totalDays, todayOffset, monthCols, dayPx } = useMemo(() => {
    if (!data) return { minDate: new Date(), maxDate: new Date(), totalDays: 30, todayOffset: 0, monthCols: [], dayPx: 28 };
    const min = parseDate(data.min_date);
    const max = parseDate(data.max_date);
    const total = Math.max(daysBetween(min, max), 1);
    const today = new Date();
    const todOff = daysBetween(min, today);
    const cols = buildMonthColumns(min, total);
    const dayPx = 28; // px per day
    return { minDate: min, maxDate: max, totalDays: total, todayOffset: todOff, monthCols: cols, dayPx };
  }, [data]);

  const timelineWidth = totalDays * dayPx;
  const LEFT_PANEL = 280;

  if (isLoading) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <Header title="Gantt Chart" subtitle="Timeline view of all projects and tasks" />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500 text-sm animate-pulse">Loading timeline…</p>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <Header title="Gantt Chart" subtitle="Timeline view of all projects and tasks" />
        <div className="flex-1 flex items-center justify-center">
          <p className="text-slate-500 text-sm">Failed to load Gantt data.</p>
        </div>
      </div>
    );
  }

  if (data.items.length === 0) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <Header title="Gantt Chart" subtitle="Timeline view of all projects and tasks" />
        <div className="flex-1 flex items-center justify-center flex-col gap-3">
          <span className="text-slate-600 text-3xl">▬</span>
          <p className="text-slate-500 text-sm">No projects yet. Create a project to see the Gantt chart.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title="Gantt Chart"
        subtitle={`${data.items.length} project${data.items.length !== 1 ? "s" : ""} · ${data.min_date} → ${data.max_date}`}
      />

      <div className="flex-1 overflow-hidden flex flex-col">
        {/* Gantt container */}
        <div className="flex flex-1 overflow-hidden border-t border-slate-800">
          {/* Left panel — fixed width names */}
          <div
            className="shrink-0 bg-[#080f20] border-r border-slate-800 overflow-y-auto overflow-x-hidden z-10"
            style={{ width: LEFT_PANEL }}
          >
            {/* Header spacer (aligns with month headers) */}
            <div className="h-9 border-b border-slate-800 flex items-center px-4">
              <span className="text-[10px] text-slate-500 uppercase tracking-wide font-medium">Project / Task</span>
            </div>

            {data.items.map((proj) => (
              <div key={proj.id}>
                {/* Project row */}
                <div className="flex items-center gap-2 px-4 py-2.5 border-b border-slate-800/60 bg-[#0a0f20]">
                  <span className="text-[9px] text-slate-500 font-mono uppercase">{proj.status.replace("_", " ")}</span>
                  <span
                    className="text-xs font-semibold text-white truncate flex-1"
                    title={proj.title}
                  >
                    {proj.title}
                  </span>
                  <span className={`text-[9px] font-medium shrink-0 ${PRIORITY_TEXT_COLORS[proj.priority] || "text-slate-500"}`}>
                    {proj.priority}
                  </span>
                </div>

                {/* Task sub-rows */}
                {proj.subtasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center gap-2 pl-8 pr-4 py-2 border-b border-slate-800/30 hover:bg-slate-800/20 transition-colors"
                  >
                    <span
                      className={`w-2 h-2 rounded-full shrink-0 ${task.is_completed ? "bg-green-500" : PRIORITY_BAR_COLORS[task.priority] || "bg-slate-500"}`}
                    />
                    <span
                      className={`text-[11px] flex-1 truncate ${task.is_completed ? "line-through text-slate-600" : "text-slate-300"}`}
                      title={task.title}
                    >
                      {task.title}
                    </span>
                    {task.assignee && (
                      <span className="text-[9px] text-slate-600 shrink-0 truncate max-w-[60px]" title={task.assignee}>
                        {task.assignee.split(" ")[0]}
                      </span>
                    )}
                  </div>
                ))}

                {proj.subtasks.length === 0 && (
                  <div className="pl-8 pr-4 py-2 border-b border-slate-800/30">
                    <span className="text-[10px] text-slate-700 italic">No tasks</span>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Right panel — scrollable timeline */}
          <div className="flex-1 overflow-auto relative" ref={containerRef}>
            {/* Timeline inner */}
            <div style={{ width: timelineWidth, minWidth: "100%" }}>
              {/* Month headers */}
              <div className="h-9 border-b border-slate-800 flex relative bg-[#080f20] sticky top-0 z-10">
                {monthCols.map((col, i) => (
                  <div
                    key={i}
                    className="absolute top-0 bottom-0 flex items-center justify-center border-r border-slate-800/40"
                    style={{
                      left: (col.offsetDays / totalDays) * 100 + "%",
                      width: (col.widthDays / totalDays) * 100 + "%",
                    }}
                  >
                    <span className="text-[10px] text-slate-500 font-medium">{col.label}</span>
                  </div>
                ))}
              </div>

              {/* Rows */}
              {data.items.map((proj) => {
                const projStart = parseDate(proj.start_date);
                const projEnd = parseDate(proj.end_date);
                const projStartOff = Math.max(0, daysBetween(minDate, projStart));
                const projEndOff = Math.min(totalDays, daysBetween(minDate, projEnd));

                return (
                  <div key={proj.id}>
                    {/* Project row */}
                    <div className="relative h-10 border-b border-slate-800/60 bg-[#0a0f20]/40">
                      {proj.start_date && proj.end_date ? (
                        <GanttBar
                          startOffset={projStartOff}
                          endOffset={projEndOff}
                          totalDays={totalDays}
                          color="bg-gradient-to-r from-indigo-600 to-violet-600"
                          progress={proj.progress}
                          label={`${proj.title} ${proj.progress}%`}
                          tooltip={`${proj.title} | ${proj.start_date} → ${proj.end_date} | ${proj.progress}% done`}
                          dayPx={dayPx}
                        />
                      ) : (
                        <div className="absolute inset-0 flex items-center px-3">
                          <span className="text-[10px] text-slate-700 italic">No deadline</span>
                        </div>
                      )}
                      {/* Grid lines */}
                      {monthCols.map((col, i) => (
                        <div
                          key={i}
                          className="absolute top-0 bottom-0 border-r border-slate-800/20 pointer-events-none"
                          style={{ left: (col.offsetDays / totalDays) * 100 + "%" }}
                        />
                      ))}
                      {/* Today line */}
                      {todayOffset >= 0 && todayOffset <= totalDays && (
                        <div
                          className="absolute top-0 bottom-0 border-l-2 border-amber-500/60 border-dashed pointer-events-none z-20"
                          style={{ left: (todayOffset / totalDays) * 100 + "%" }}
                        />
                      )}
                    </div>

                    {/* Task sub-rows */}
                    {proj.subtasks.map((task) => {
                      const tStart = parseDate(task.start_date);
                      const tEnd = parseDate(task.end_date);
                      const tStartOff = Math.max(0, daysBetween(minDate, tStart));
                      const tEndOff = Math.min(totalDays, daysBetween(minDate, tEnd));
                      const barColor = task.is_completed
                        ? "bg-green-600"
                        : PRIORITY_BAR_COLORS[task.priority] || "bg-slate-500";

                      return (
                        <div key={task.id} className="relative h-9 border-b border-slate-800/30">
                          <GanttBar
                            startOffset={tStartOff}
                            endOffset={tEndOff}
                            totalDays={totalDays}
                            color={barColor}
                            label={task.title}
                            tooltip={`${task.title} | ${task.start_date} → ${task.end_date}${task.assignee ? ` | ${task.assignee}` : ""}${task.is_completed ? " | DONE" : ""}`}
                            isCompleted={task.is_completed}
                            dayPx={dayPx}
                          />
                          {/* Grid lines */}
                          {monthCols.map((col, i) => (
                            <div
                              key={i}
                              className="absolute top-0 bottom-0 border-r border-slate-800/20 pointer-events-none"
                              style={{ left: (col.offsetDays / totalDays) * 100 + "%" }}
                            />
                          ))}
                          {/* Today line */}
                          {todayOffset >= 0 && todayOffset <= totalDays && (
                            <div
                              className="absolute top-0 bottom-0 border-l-2 border-amber-500/60 border-dashed pointer-events-none z-20"
                              style={{ left: (todayOffset / totalDays) * 100 + "%" }}
                            />
                          )}
                        </div>
                      );
                    })}

                    {proj.subtasks.length === 0 && (
                      <div className="relative h-9 border-b border-slate-800/30" />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className="shrink-0 px-4 py-2 border-t border-slate-800 bg-[#080f20] flex items-center gap-4 flex-wrap">
          <span className="text-[10px] text-slate-600 uppercase tracking-wide font-medium">Legend</span>
          <div className="flex items-center gap-1.5">
            <div className="w-8 h-3 rounded bg-gradient-to-r from-indigo-600 to-violet-600" />
            <span className="text-[10px] text-slate-500">Project (with progress)</span>
          </div>
          {[
            { label: "Urgent", color: "bg-red-500" },
            { label: "High", color: "bg-amber-500" },
            { label: "Medium", color: "bg-blue-500" },
            { label: "Low", color: "bg-slate-500" },
            { label: "Done", color: "bg-green-600" },
          ].map(({ label, color }) => (
            <div key={label} className="flex items-center gap-1.5">
              <div className={`w-3 h-3 rounded ${color}`} />
              <span className="text-[10px] text-slate-500">{label}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5">
            <div className="w-0 h-3 border-l-2 border-amber-500 border-dashed" style={{ height: 12 }} />
            <span className="text-[10px] text-slate-500">Today</span>
          </div>
        </div>
      </div>
    </div>
  );
}
