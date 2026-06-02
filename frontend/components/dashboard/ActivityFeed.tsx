"use client";

import { relativeTime, initials } from "@/lib/utils";
import type { ActivityLog } from "@/lib/types";

const ACTION_LABELS: Record<string, string> = {
  created: "created project",
  moved: "moved to",
  status_changed: "changed status to",
  priority_changed: "changed priority to",
  commented: "commented on",
};

export function ActivityFeed({
  activities,
  loading,
}: {
  activities: ActivityLog[];
  loading?: boolean;
}) {
  return (
    <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
      <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        <span>Recent Activity</span>
        <span className="w-1.5 h-1.5 rounded-full bg-green-400 ai-pulse" />
      </h3>

      {loading ? (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex gap-3 animate-pulse">
              <div className="w-7 h-7 rounded-full bg-slate-800 shrink-0" />
              <div className="flex-1 space-y-1.5">
                <div className="h-3 bg-slate-800 rounded w-3/4" />
                <div className="h-2.5 bg-slate-800 rounded w-1/3" />
              </div>
            </div>
          ))}
        </div>
      ) : activities.length === 0 ? (
        <p className="text-slate-500 text-sm text-center py-8">No recent activity</p>
      ) : (
        <div className="space-y-3">
          {activities.map((log) => (
            <div key={log.id} className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-indigo-800 flex items-center justify-center shrink-0 text-xs font-medium text-white">
                {log.user ? initials(log.user.name) : "?"}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-slate-300">
                  <span className="font-medium text-white">{log.user?.name ?? "System"}</span>{" "}
                  <span className="text-slate-400">{ACTION_LABELS[log.action] ?? log.action}</span>{" "}
                  {log.new_value && (
                    <span className="font-medium text-indigo-400">
                      {log.new_value.replace("_", " ")}
                    </span>
                  )}
                </p>
                <p className="text-[11px] text-slate-600 mt-0.5">{relativeTime(log.created_at)}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
