"use client";

import type { TaskBalanceResponse, PersonTaskBalance } from "@/lib/types";

interface Props {
  data: TaskBalanceResponse;
}

const OVERDUE_COLORS = {
  high:   "bg-red-600",
  medium: "bg-orange-500",
  low:    "bg-amber-400",
};

const UPCOMING_COLORS = {
  high:   "bg-indigo-600",
  medium: "bg-purple-500",
  low:    "bg-slate-500",
};

function PersonRow({ person, maxCount }: { person: PersonTaskBalance; maxCount: number }) {
  const pct = (n: number) => `${Math.max(Math.round((n / maxCount) * 100), n > 0 ? 2 : 0)}%`;

  return (
    <div className="flex items-center gap-1 h-7">
      {/* Overdue side — grows right-to-left from centre */}
      <div className="flex flex-1 flex-row-reverse items-center gap-0.5">
        {(["high", "medium", "low"] as const).map((p) =>
          person.overdue[p] > 0 ? (
            <div
              key={p}
              className={`h-4 rounded-sm ${OVERDUE_COLORS[p]} transition-all`}
              style={{ width: pct(person.overdue[p]) }}
              title={`${p} overdue: ${person.overdue[p]}`}
            />
          ) : null
        )}
      </div>

      {/* Centre label */}
      <div className="w-24 shrink-0 text-center text-xs text-slate-400 truncate px-1">
        {person.name.split(" ")[0]}
      </div>

      {/* Upcoming side — grows left-to-right from centre */}
      <div className="flex flex-1 flex-row items-center gap-0.5">
        {(["high", "medium", "low"] as const).map((p) =>
          person.upcoming[p] > 0 ? (
            <div
              key={p}
              className={`h-4 rounded-sm ${UPCOMING_COLORS[p]} transition-all`}
              style={{ width: pct(person.upcoming[p]) }}
              title={`${p} upcoming: ${person.upcoming[p]}`}
            />
          ) : null
        )}
      </div>
    </div>
  );
}

export function TaskBalanceChart({ data }: Props) {
  const { people, max_count } = data;

  return (
    <div className="space-y-4">
      {/* Legend */}
      <div className="flex items-center justify-between text-[10px] text-slate-500">
        <div className="flex items-center gap-3">
          <span className="font-medium text-slate-400 uppercase tracking-wide">← Overdue</span>
          {(["high", "medium", "low"] as const).map((p) => (
            <span key={p} className="flex items-center gap-1">
              <span className={`w-2.5 h-2.5 rounded-sm inline-block ${OVERDUE_COLORS[p]}`} />
              {p}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-3">
          {(["high", "medium", "low"] as const).map((p) => (
            <span key={p} className="flex items-center gap-1">
              <span className={`w-2.5 h-2.5 rounded-sm inline-block ${UPCOMING_COLORS[p]}`} />
              {p}
            </span>
          ))}
          <span className="font-medium text-slate-400 uppercase tracking-wide">Upcoming →</span>
        </div>
      </div>

      {/* Centre axis line */}
      <div className="relative">
        <div className="absolute left-1/2 top-0 bottom-0 w-px bg-slate-700" />
        <div className="space-y-1.5">
          {people.map((person) => (
            <PersonRow key={person.name} person={person} maxCount={max_count} />
          ))}
        </div>
      </div>
    </div>
  );
}
