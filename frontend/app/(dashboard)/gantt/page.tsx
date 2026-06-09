"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { useUIStore } from "@/lib/store";
import { Header } from "@/components/layout/Header";
import { useMemo, useRef, useState, useCallback } from "react";

interface GanttTask {
  id: string; title: string; type: "task";
  assignee?: string | null; start_date: string; end_date: string;
  is_completed: boolean; priority: string;
}
interface GanttProject {
  id: string; title: string; type: "project"; status: string; priority: string;
  start_date: string; end_date: string; progress: number; subtasks: GanttTask[];
}
interface GanttData { items: GanttProject[]; min_date: string; max_date: string; }

function parseDate(s: string): Date { return new Date(s + "T00:00:00"); }
function daysBetween(a: Date, b: Date): number { return Math.floor((b.getTime() - a.getTime()) / 86400000); }
function formatMonth(d: Date): string { return d.toLocaleString("default", { month: "short", year: "2-digit" }); }

// Dark mode priority colors
const PRIORITY_BAR_DARK: Record<string, string> = { urgent: "bg-red-500", high: "bg-amber-500", medium: "bg-blue-500", low: "bg-slate-500" };
const PRIORITY_TEXT_DARK: Record<string, string> = { urgent: "text-red-400", high: "text-amber-400", medium: "text-blue-400", low: "text-slate-400" };
// Light mode priority colors
const PRIORITY_BAR_LIGHT: Record<string, string> = { urgent: "bg-red-500", high: "bg-amber-500", medium: "bg-blue-500", low: "bg-slate-400" };
const PRIORITY_TEXT_LIGHT: Record<string, string> = { urgent: "text-red-700", high: "text-amber-700", medium: "text-blue-700", low: "text-slate-600" };

function buildMonthColumns(minDate: Date, totalDays: number) {
  const cols: { label: string; offsetDays: number; widthDays: number }[] = [];
  let cursor = new Date(minDate); cursor.setDate(1);
  while (daysBetween(minDate, cursor) < totalDays) {
    const monthStart = new Date(cursor);
    const nextMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
    const offsetDays = Math.max(0, daysBetween(minDate, monthStart));
    const endOffset = Math.min(totalDays, daysBetween(minDate, nextMonth));
    const widthDays = endOffset - offsetDays;
    if (widthDays > 0) cols.push({ label: formatMonth(monthStart), offsetDays, widthDays });
    cursor = nextMonth;
  }
  return cols;
}

function GanttBar({ startOffset, endOffset, totalDays, color, progress, label, tooltip, isCompleted, isLight }: {
  startOffset: number; endOffset: number; totalDays: number;
  color: string; progress?: number; label?: string; tooltip: string; isCompleted?: boolean; isLight: boolean;
}) {
  const left = (startOffset / totalDays) * 100;
  const width = Math.max(((endOffset - startOffset) / totalDays) * 100, 0.5);
  const trackBg = isLight
    ? (isCompleted ? "bg-green-100" : "bg-slate-200")
    : (isCompleted ? "bg-green-800/60" : "bg-slate-700/50");
  return (
    <div className="absolute top-1/2 -translate-y-1/2 rounded" style={{ left: `${left}%`, width: `${width}%`, minWidth: "4px" }} title={tooltip}>
      <div className={`relative h-5 rounded overflow-hidden ${trackBg}`}>
        <div className={`absolute left-0 top-0 bottom-0 rounded ${isCompleted ? "bg-green-500" : color}`}
          style={{ width: progress !== undefined ? `${progress}%` : "100%" }} />
        {label && <span className="absolute inset-0 flex items-center px-1.5 text-[9px] text-white font-medium truncate whitespace-nowrap z-10 pointer-events-none drop-shadow">{label}</span>}
      </div>
    </div>
  );
}

export default function GanttPage() {
  const { data, isLoading, error } = useQuery<GanttData>({ queryKey: ["gantt"], queryFn: () => analyticsApi.gantt(), staleTime: 30_000 });
  const { theme } = useUIStore();
  const isLight = theme === "light";
  const containerRef = useRef<HTMLDivElement>(null);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const PRIORITY_BAR  = isLight ? PRIORITY_BAR_LIGHT  : PRIORITY_BAR_DARK;
  const PRIORITY_TEXT = isLight ? PRIORITY_TEXT_LIGHT : PRIORITY_TEXT_DARK;

  const toggleProject = useCallback((id: string) => {
    setExpandedIds((prev) => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n; });
  }, []);
  const expandAll  = useCallback(() => { if (data) setExpandedIds(new Set(data.items.map(p => p.id))); }, [data]);
  const collapseAll = useCallback(() => setExpandedIds(new Set()), []);
  const allExpanded = data ? data.items.length > 0 && expandedIds.size === data.items.length : false;

  const { minDate, totalDays, todayOffset, monthCols } = useMemo(() => {
    if (!data) return { minDate: new Date(), totalDays: 30, todayOffset: 0, monthCols: [] };
    const min = parseDate(data.min_date), max = parseDate(data.max_date);
    return { minDate: min, totalDays: Math.max(daysBetween(min, max), 1), todayOffset: daysBetween(min, new Date()), monthCols: buildMonthColumns(min, Math.max(daysBetween(min, max), 1)) };
  }, [data]);

  const DAY_PX = 28;
  const timelineWidth = totalDays * DAY_PX;
  const LEFT_PANEL = 300;

  // Theme classes
  const panelBg     = isLight ? "bg-white"    : "bg-[#080f20]";
  const rowBg       = isLight ? "bg-slate-50" : "bg-[#0a0f20]/40";
  const borderColor = isLight ? "border-slate-200" : "border-slate-800";
  const headerBg    = isLight ? "bg-slate-100" : "bg-[#080f20]";
  const headerText  = isLight ? "text-slate-600" : "text-slate-500";
  const titleColor  = isLight ? "text-slate-900" : "text-white";
  const subtaskColor= isLight ? "text-slate-700" : "text-slate-300";
  const metaText    = isLight ? "text-slate-500" : "text-slate-500";
  const rowHover    = isLight ? "hover:bg-slate-100" : "hover:bg-slate-800/40";
  const subtaskHover= isLight ? "hover:bg-slate-50"  : "hover:bg-slate-800/20";
  const gridLine    = isLight ? "border-slate-200/80" : "border-slate-800/20";
  const legendBg    = isLight ? "bg-slate-50 border-slate-200" : "bg-[#080f20] border-slate-800";
  const legendText  = isLight ? "text-slate-500" : "text-slate-500";
  const btnBase     = isLight
    ? "border-slate-300 text-slate-600 hover:text-slate-900 hover:border-slate-400 disabled:opacity-30"
    : "border-slate-700 text-slate-400 hover:text-white hover:border-slate-600 disabled:opacity-40";

  if (isLoading) return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header title="Gantt Chart" subtitle="Timeline view" />
      <div className="flex-1 flex items-center justify-center"><p className={`text-sm animate-pulse ${metaText}`}>Loading timeline…</p></div>
    </div>
  );

  if (error || !data || data.items.length === 0) return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header title="Gantt Chart" subtitle="Timeline view" />
      <div className="flex-1 flex items-center justify-center flex-col gap-2">
        <span className={`text-3xl ${metaText}`}>▬</span>
        <p className={`text-sm ${metaText}`}>No projects to display.</p>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title="Gantt Chart"
        subtitle={`${data.items.length} projects · ${expandedIds.size} expanded`}
        actions={
          <div className="flex items-center gap-2">
            <button onClick={expandAll} disabled={allExpanded} className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${btnBase}`}>Expand All</button>
            <button onClick={collapseAll} disabled={expandedIds.size === 0} className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${btnBase}`}>Collapse All</button>
          </div>
        }
      />

      <div className="flex-1 overflow-hidden flex flex-col">
        <div className={`flex flex-1 overflow-hidden border-t ${borderColor}`}>

          {/* Left panel */}
          <div className={`shrink-0 ${panelBg} border-r ${borderColor} overflow-y-auto overflow-x-hidden z-10`} style={{ width: LEFT_PANEL }}>
            <div className={`h-9 border-b ${borderColor} flex items-center px-4 gap-2 ${headerBg}`}>
              <span className={`text-[10px] uppercase tracking-wide font-medium ${headerText}`}>Project / Task</span>
              <span className={`text-[9px] ml-auto ${metaText}`}>click to expand</span>
            </div>

            {data.items.map((proj) => {
              const isExpanded = expandedIds.has(proj.id);
              return (
                <div key={proj.id}>
                  <button onClick={() => toggleProject(proj.id)}
                    className={`w-full flex items-center gap-2 px-3 py-2.5 border-b ${borderColor} ${rowBg} ${rowHover} transition-colors text-left group`}>
                    <span className={`text-[10px] transition-transform shrink-0 ${metaText} ${isExpanded ? "rotate-90" : ""}`}>▶</span>
                    <span className={`text-[10px] font-mono uppercase shrink-0 ${metaText}`}>{proj.status.replace("_", " ")}</span>
                    <span className={`text-xs font-semibold truncate flex-1 ${titleColor}`} title={proj.title}>{proj.title}</span>
                    <span className={`text-xs font-bold px-1.5 py-0.5 rounded text-white shrink-0 ${
                      proj.priority === "urgent" ? "bg-red-600" :
                      proj.priority === "high"   ? "bg-amber-500" :
                      proj.priority === "medium" ? "bg-blue-600" : "bg-slate-500"
                    }`}>{proj.priority}</span>
                    <span className={`text-[10px] shrink-0 ${metaText}`}>{proj.subtasks.length}t</span>
                  </button>

                  {isExpanded && proj.subtasks.map((task) => (
                    <div key={task.id} className={`flex items-center gap-2 pl-8 pr-4 py-2 border-b ${borderColor} ${subtaskHover} transition-colors`}>
                      <span className={`w-2 h-2 rounded-full shrink-0 ${task.is_completed ? "bg-green-500" : PRIORITY_BAR[task.priority] || "bg-slate-400"}`} />
                      <span className={`text-xs flex-1 truncate ${task.is_completed ? "line-through opacity-50" : subtaskColor}`} title={task.title}>{task.title}</span>
                      {task.assignee && <span className={`text-[10px] shrink-0 truncate max-w-[60px] ${metaText}`}>{task.assignee.split(" ")[0]}</span>}
                    </div>
                  ))}
                  {isExpanded && proj.subtasks.length === 0 && (
                    <div className={`pl-8 pr-4 py-2 border-b ${borderColor}`}>
                      <span className={`text-[10px] italic ${metaText}`}>No tasks</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Timeline */}
          <div className="flex-1 overflow-auto relative" ref={containerRef}>
            <div style={{ width: timelineWidth, minWidth: "100%" }}>

              {/* Month headers */}
              <div className={`h-9 border-b ${borderColor} flex relative ${headerBg} sticky top-0 z-10`}>
                {monthCols.map((col, i) => (
                  <div key={i} className={`absolute top-0 bottom-0 flex items-center justify-center border-r ${borderColor}`}
                    style={{ left: (col.offsetDays / totalDays) * 100 + "%", width: (col.widthDays / totalDays) * 100 + "%" }}>
                    <span className={`text-[10px] font-medium ${headerText}`}>{col.label}</span>
                  </div>
                ))}
              </div>

              {data.items.map((proj) => {
                const isExpanded = expandedIds.has(proj.id);
                const projStartOff = Math.max(0, daysBetween(minDate, parseDate(proj.start_date)));
                const projEndOff   = Math.min(totalDays, daysBetween(minDate, parseDate(proj.end_date)));

                const GridLines = () => (
                  <>
                    {monthCols.map((col, i) => (
                      <div key={i} className={`absolute top-0 bottom-0 border-r ${gridLine} pointer-events-none`} style={{ left: (col.offsetDays / totalDays) * 100 + "%" }} />
                    ))}
                    {todayOffset >= 0 && todayOffset <= totalDays && (
                      <div className="absolute top-0 bottom-0 border-l-2 border-amber-500/70 border-dashed pointer-events-none z-20" style={{ left: (todayOffset / totalDays) * 100 + "%" }} />
                    )}
                  </>
                );

                return (
                  <div key={proj.id}>
                    <div className={`relative h-10 border-b ${borderColor} ${rowBg} cursor-pointer`} onClick={() => toggleProject(proj.id)}>
                      <GanttBar startOffset={projStartOff} endOffset={projEndOff} totalDays={totalDays}
                        color="bg-gradient-to-r from-indigo-600 to-violet-600"
                        progress={proj.progress} label={`${proj.title} ${proj.progress}%`}
                        tooltip={`${proj.title} | ${proj.start_date} → ${proj.end_date} | ${proj.progress}% | ${proj.subtasks.length} tasks`}
                        isLight={isLight} />
                      <GridLines />
                    </div>

                    {isExpanded && proj.subtasks.map((task) => {
                      const tStartOff = Math.max(0, daysBetween(minDate, parseDate(task.start_date)));
                      const tEndOff   = Math.min(totalDays, daysBetween(minDate, parseDate(task.end_date)));
                      return (
                        <div key={task.id} className={`relative h-9 border-b ${borderColor}`}>
                          <GanttBar startOffset={tStartOff} endOffset={tEndOff} totalDays={totalDays}
                            color={task.is_completed ? "bg-green-500" : PRIORITY_BAR[task.priority] || "bg-slate-400"}
                            label={task.title}
                            tooltip={`${task.title} | ${task.start_date} → ${task.end_date}${task.assignee ? ` | ${task.assignee}` : ""}${task.is_completed ? " | DONE" : ""}`}
                            isCompleted={task.is_completed} isLight={isLight} />
                          <GridLines />
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Legend */}
        <div className={`shrink-0 px-4 py-2 border-t ${legendBg} flex items-center gap-4 flex-wrap`}>
          <span className={`text-[10px] uppercase tracking-wide font-medium ${legendText}`}>Legend</span>
          <div className="flex items-center gap-1.5">
            <div className="w-8 h-3 rounded bg-gradient-to-r from-indigo-600 to-violet-600" />
            <span className={`text-[10px] ${legendText}`}>Project</span>
          </div>
          {[{ label: "Urgent", color: "bg-red-500" }, { label: "High", color: "bg-amber-500" }, { label: "Medium", color: "bg-blue-500" }, { label: "Low", color: "bg-slate-400" }, { label: "Done", color: "bg-green-500" }].map(({ label, color }) => (
            <div key={label} className="flex items-center gap-1.5">
              <div className={`w-3 h-3 rounded ${color}`} />
              <span className={`text-[10px] ${legendText}`}>{label}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5">
            <div className="w-0 h-3 border-l-2 border-amber-500 border-dashed" style={{ height: 12 }} />
            <span className={`text-[10px] ${legendText}`}>Today</span>
          </div>
          <span className={`ml-auto text-[10px] ${metaText}`}>Click a project row to expand tasks</span>
        </div>
      </div>
    </div>
  );
}
