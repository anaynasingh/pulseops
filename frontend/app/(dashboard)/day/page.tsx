"use client";

import { useMemo, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { tasksApi } from "@/lib/api";
import { useUIStore } from "@/lib/store";
import { Header } from "@/components/layout/Header";
import type { DayViewResponse, Task } from "@/lib/types";

const DAY_START_HOUR = 6;
const DAY_END_HOUR = 22;
const SLOT_H = 64; // px per hour
const DEFAULT_DURATION = 60;

const PRIORITY_BAR: Record<string, string> = {
  urgent: "bg-red-500", high: "bg-amber-500", medium: "bg-blue-500", low: "bg-slate-500",
};

function pad(n: number): string { return String(n).padStart(2, "0"); }
function toDateStr(d: Date): string { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; }
function fromDateStr(s: string): Date { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); }
function hourLabel(h: number): string {
  const ampm = h < 12 ? "am" : "pm";
  const hr = h % 12 === 0 ? 12 : h % 12;
  return `${hr}${ampm}`;
}

export default function DayViewPage() {
  const { theme } = useUIStore();
  const isLight = theme === "light";
  const queryClient = useQueryClient();

  const [dateStr, setDateStr] = useState<string>(() => toDateStr(new Date()));

  // Local day boundaries — DST-correct (Date construction respects local tz)
  const { startIso, endIso } = useMemo(() => {
    const base = fromDateStr(dateStr);
    const start = new Date(base.getFullYear(), base.getMonth(), base.getDate(), 0, 0, 0);
    const end = new Date(base.getFullYear(), base.getMonth(), base.getDate() + 1, 0, 0, 0);
    return { startIso: start.toISOString(), endIso: end.toISOString() };
  }, [dateStr]);

  const { data, isLoading } = useQuery<DayViewResponse>({
    queryKey: ["tasks", "day", dateStr],
    queryFn: () => tasksApi.day(startIso, endIso),
  });

  const scheduleMutation = useMutation({
    mutationFn: ({ id, scheduled_at }: { id: string; scheduled_at: string | null }) =>
      tasksApi.update(id, { scheduled_at, duration_minutes: DEFAULT_DURATION }),
    onMutate: async ({ id, scheduled_at }) => {
      await queryClient.cancelQueries({ queryKey: ["tasks", "day", dateStr] });
      const previous = queryClient.getQueryData<DayViewResponse>(["tasks", "day", dateStr]);
      if (previous) {
        const all = [...previous.scheduled, ...previous.unscheduled];
        const task = all.find((t) => t.id === id);
        if (task) {
          const updated: Task = { ...task, scheduled_at, duration_minutes: task.duration_minutes ?? DEFAULT_DURATION };
          const scheduled = previous.scheduled.filter((t) => t.id !== id);
          const unscheduled = previous.unscheduled.filter((t) => t.id !== id);
          if (scheduled_at) scheduled.push(updated);
          else unscheduled.push(updated);
          queryClient.setQueryData<DayViewResponse>(["tasks", "day", dateStr], { scheduled, unscheduled });
        }
      }
      return { previous };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(["tasks", "day", dateStr], ctx.previous);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["tasks", "day", dateStr] }),
  });

  const shiftDay = (delta: number) => {
    const d = fromDateStr(dateStr);
    d.setDate(d.getDate() + delta);
    setDateStr(toDateStr(d));
  };

  const scheduleTask = (id: string, hour: number) => {
    const base = fromDateStr(dateStr);
    const at = new Date(base.getFullYear(), base.getMonth(), base.getDate(), hour, 0, 0);
    scheduleMutation.mutate({ id, scheduled_at: at.toISOString() });
  };
  const unschedule = (id: string) => scheduleMutation.mutate({ id, scheduled_at: null });

  const scheduled = data?.scheduled ?? [];
  const unscheduled = data?.unscheduled ?? [];

  // Partition scheduled into in-grid vs outside working hours
  const { inGrid, offHours } = useMemo(() => {
    const inGrid: Task[] = [];
    const offHours: Task[] = [];
    for (const t of scheduled) {
      if (!t.scheduled_at) continue;
      const h = new Date(t.scheduled_at).getHours();
      if (h < DAY_START_HOUR || h >= DAY_END_HOUR) offHours.push(t);
      else inGrid.push(t);
    }
    return { inGrid, offHours };
  }, [scheduled]);

  const hours = Array.from({ length: DAY_END_HOUR - DAY_START_HOUR }, (_, i) => DAY_START_HOUR + i);

  // Achievability
  const scheduledMinutes = scheduled.reduce((sum, t) => sum + (t.duration_minutes ?? DEFAULT_DURATION), 0);
  const availableMinutes = (DAY_END_HOUR - DAY_START_HOUR) * 60;
  const overbooked = scheduledMinutes > availableMinutes;
  const pctBooked = Math.min(Math.round((scheduledMinutes / availableMinutes) * 100), 100);
  const barColor = overbooked ? "bg-red-500" : pctBooked > 80 ? "bg-amber-500" : "bg-green-500";

  const card = isLight ? "bg-white border-slate-200" : "bg-[#0f1629] border-slate-800";

  function blockTop(t: Task): number {
    const d = new Date(t.scheduled_at!);
    return (d.getHours() + d.getMinutes() / 60 - DAY_START_HOUR) * SLOT_H;
  }
  function blockHeight(t: Task): number {
    const mins = t.duration_minutes ?? DEFAULT_DURATION;
    const top = blockTop(t);
    const gridH = (DAY_END_HOUR - DAY_START_HOUR) * SLOT_H;
    return Math.min((mins / 60) * SLOT_H, gridH - top); // clamp to grid bottom
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header title="Day View" subtitle="Time-block your day — schedule tasks into hourly slots" />

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
        {/* Date nav + achievability */}
        <div className={`border rounded-xl p-4 flex flex-col md:flex-row md:items-center gap-4 ${card}`}>
          <div className="flex items-center gap-2">
            <button onClick={() => shiftDay(-1)} className="w-8 h-8 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors">‹</button>
            <input
              type="date"
              value={dateStr}
              onChange={(e) => setDateStr(e.target.value)}
              className={`text-sm rounded-lg px-3 py-1.5 border focus:outline-none ${isLight ? "bg-white border-slate-300 text-slate-900" : "bg-slate-900 border-slate-700 text-white"}`}
            />
            <button onClick={() => shiftDay(1)} className="w-8 h-8 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors">›</button>
            <button onClick={() => setDateStr(toDateStr(new Date()))} className="ml-1 text-xs px-2.5 py-1.5 rounded-lg border border-slate-700 text-slate-400 hover:text-white hover:border-slate-500 transition-colors">Today</button>
          </div>

          {/* Achievability bar */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <span className={`text-xs ${isLight ? "text-slate-600" : "text-slate-400"}`}>
                {Math.round(scheduledMinutes / 60 * 10) / 10}h scheduled of {availableMinutes / 60}h
              </span>
              <span className={`text-xs font-semibold ${overbooked ? "text-red-400" : pctBooked > 80 ? "text-amber-400" : "text-green-400"}`}>
                {overbooked ? `Overbooked by ${Math.round((scheduledMinutes - availableMinutes) / 60 * 10) / 10}h` : `${pctBooked}% booked`}
              </span>
            </div>
            <div className="bg-slate-800 rounded-full h-2">
              <div className={`h-2 rounded-full transition-all ${barColor}`} style={{ width: `${pctBooked}%` }} />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Hour grid — 2 cols */}
          <div className="lg:col-span-2 space-y-3">
            {/* Outside working hours strip */}
            {offHours.length > 0 && (
              <div className={`border rounded-xl p-4 ${card}`}>
                <h3 className="text-xs font-semibold text-amber-400 mb-2">Outside working hours</h3>
                <div className="space-y-2">
                  {offHours.map((t) => (
                    <div key={t.id} className={`flex items-center gap-2 p-2 rounded-lg ${isLight ? "bg-slate-50" : "bg-slate-900/50"}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${PRIORITY_BAR[t.priority] ?? PRIORITY_BAR.medium}`} />
                      <span className={`text-xs flex-1 ${isLight ? "text-slate-700" : "text-slate-300"}`}>
                        {new Date(t.scheduled_at!).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })} · {t.title}
                      </span>
                      <button onClick={() => unschedule(t.id)} className="text-slate-500 hover:text-red-400 text-xs" title="Unschedule">✕</button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className={`border rounded-xl p-4 ${card}`}>
              {isLoading ? (
                <div className="space-y-2">{[...Array(6)].map((_, i) => <div key={i} className="h-12 bg-slate-800 rounded animate-pulse" />)}</div>
              ) : (
                <div className="relative" style={{ height: hours.length * SLOT_H }}>
                  {/* Hour rows */}
                  {hours.map((h, i) => (
                    <div key={h} className="absolute left-0 right-0 flex" style={{ top: i * SLOT_H, height: SLOT_H }}>
                      <div className={`w-14 shrink-0 text-xs pt-1 ${isLight ? "text-slate-400" : "text-slate-600"}`}>{hourLabel(h)}</div>
                      <div className={`flex-1 border-t ${isLight ? "border-slate-200" : "border-slate-800"}`} />
                    </div>
                  ))}
                  {/* Scheduled blocks */}
                  {inGrid.map((t) => (
                    <div
                      key={t.id}
                      className={`absolute left-14 right-1 rounded-lg px-2 py-1 overflow-hidden text-white ${PRIORITY_BAR[t.priority] ?? PRIORITY_BAR.medium}`}
                      style={{ top: blockTop(t), height: Math.max(blockHeight(t), 22) }}
                    >
                      <div className="flex items-start justify-between gap-1">
                        <span className="text-xs font-medium leading-tight">{t.title}</span>
                        <button onClick={() => unschedule(t.id)} className="text-white/70 hover:text-white text-xs shrink-0" title="Unschedule">✕</button>
                      </div>
                      {t.project && <span className="text-[10px] text-white/70">{t.project.title}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Unscheduled rail — 1 col */}
          <div className={`border rounded-xl p-4 ${card}`}>
            <h3 className={`text-sm font-semibold mb-3 ${isLight ? "text-slate-900" : "text-white"}`}>
              Unscheduled <span className="text-slate-500 font-normal">({unscheduled.length})</span>
            </h3>
            {unscheduled.length === 0 ? (
              <p className="text-sm text-slate-500 text-center py-6">Nothing to schedule 🎉</p>
            ) : (
              <div className="space-y-2">
                {unscheduled.map((t) => (
                  <div key={t.id} className={`p-3 rounded-lg border ${isLight ? "bg-slate-50 border-slate-200" : "bg-slate-900/50 border-slate-800/50"}`}>
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className={`w-1.5 h-1.5 rounded-full ${PRIORITY_BAR[t.priority] ?? PRIORITY_BAR.medium}`} />
                      <span className={`text-sm font-medium flex-1 ${isLight ? "text-slate-900" : "text-slate-100"}`}>{t.title}</span>
                    </div>
                    {t.project && <p className={`text-xs mb-2 ${isLight ? "text-indigo-700" : "text-indigo-400"}`}>{t.project.title}</p>}
                    <select
                      defaultValue=""
                      onChange={(e) => { if (e.target.value) scheduleTask(t.id, Number(e.target.value)); }}
                      className={`w-full text-xs rounded-lg px-2 py-1.5 border focus:outline-none cursor-pointer ${isLight ? "bg-white border-slate-300 text-slate-700" : "bg-slate-900 border-slate-700 text-slate-300"}`}
                    >
                      <option value="">＋ Schedule at…</option>
                      {hours.map((h) => <option key={h} value={h}>{hourLabel(h)}</option>)}
                    </select>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
