"use client";

import Link from "next/link";
import { PRIORITY_CONFIG, HEALTH_CONFIG } from "@/lib/types";
import { formatDate, getDaysUntil } from "@/lib/utils";
import type { Project } from "@/lib/types";

export function HighPriorityList({
  projects,
  loading,
}: {
  projects: Project[];
  loading?: boolean;
}) {
  return (
    <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        <span>🔥</span>
        <span>High Priority Work</span>
      </h3>

      {loading ? (
        <div className="space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-12 bg-slate-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : projects.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-6">No high priority projects</p>
      ) : (
        <div className="space-y-2">
          {projects.map((p) => {
            const daysLeft = getDaysUntil(p.due_date);
            const isOverdue = daysLeft !== null && daysLeft < 0;
            const latestHealth = p.health_records?.[0];

            return (
              <Link
                key={p.id}
                href={`/projects/${p.id}`}
                className="flex items-center gap-3 p-3 rounded-lg bg-slate-900/50 hover:bg-slate-800/60 transition-colors group"
              >
                {/* Priority badge */}
                <span
                  className={`text-[10px] font-semibold px-1.5 py-0.5 rounded shrink-0 ${PRIORITY_CONFIG[p.priority].color} ${PRIORITY_CONFIG[p.priority].bg}`}
                >
                  {PRIORITY_CONFIG[p.priority].label.toUpperCase()}
                </span>

                {/* Title */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 truncate group-hover:text-white transition-colors">
                    {p.title}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-slate-500">
                      {p.status.replace("_", " ")}
                    </span>
                    {p.blockers && (
                      <span className="text-[11px] text-red-400">• blocked</span>
                    )}
                  </div>
                </div>

                {/* Progress */}
                <div className="flex items-center gap-2 shrink-0">
                  <div className="w-16 bg-slate-700 rounded-full h-1">
                    <div
                      className="bg-indigo-500 h-1 rounded-full"
                      style={{ width: `${p.progress_pct}%` }}
                    />
                  </div>
                  <span className="text-[11px] text-slate-500 w-8 text-right">
                    {p.progress_pct}%
                  </span>
                </div>

                {/* Health dot */}
                {latestHealth && (
                  <div
                    className={`w-2 h-2 rounded-full shrink-0 ${HEALTH_CONFIG[latestHealth.health_status].dot}`}
                    title={latestHealth.health_status}
                  />
                )}

                {/* Due date */}
                {p.due_date && (
                  <span
                    className={`text-[11px] shrink-0 ${
                      isOverdue ? "text-red-400" : daysLeft! <= 3 ? "text-amber-400" : "text-slate-500"
                    }`}
                  >
                    {isOverdue ? `${Math.abs(daysLeft!)}d overdue` : `${daysLeft}d left`}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
