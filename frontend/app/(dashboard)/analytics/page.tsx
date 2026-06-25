"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { PRIORITY_CONFIG } from "@/lib/types";
import type { DashboardStats, TaskBalanceResponse } from "@/lib/types";
import { TaskBalanceChart } from "@/components/dashboard/TaskBalanceChart";

export default function AnalyticsPage() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard"],
    queryFn: () => analyticsApi.dashboard(),
  });

  const { data: taskBalance, isLoading: balanceLoading } = useQuery<TaskBalanceResponse>({
    queryKey: ["task-balance"],
    queryFn: () => analyticsApi.taskBalance(),
  });

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header title="Analytics" subtitle="Operational health and team performance" />

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {/* Overview KPIs */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Total Projects", value: stats?.total_projects ?? 0, icon: "◈" },
            { label: "Active", value: stats?.active_projects ?? 0, icon: "▶" },
            { label: "Blocked", value: stats?.blocked_projects ?? 0, icon: "⊗" },
            { label: "Done This Week", value: stats?.done_this_week ?? 0, icon: "✓" },
          ].map((kpi) => (
            <div key={kpi.label} className="bg-[#0f1629] border border-slate-800 rounded-xl p-4">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-slate-500">{kpi.label}</p>
                <span className="text-lg opacity-50">{kpi.icon}</span>
              </div>
              {isLoading ? (
                <div className="h-8 bg-slate-800 rounded animate-pulse w-12" />
              ) : (
                <p className="text-3xl font-bold text-white">{kpi.value}</p>
              )}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Team workload */}
          <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Team Workload</h3>
            {isLoading ? (
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-8 bg-slate-800 rounded animate-pulse" />
                ))}
              </div>
            ) : (stats?.team_workload?.length ?? 0) === 0 ? (
              <p className="text-slate-500 text-sm text-center py-6">No team data</p>
            ) : (
              <div className="space-y-3">
                {stats!.team_workload.map((m) => (
                  <div key={m.user_id}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-slate-300">{m.name}</span>
                      <span className="text-xs text-slate-500">{m.project_count} projects</span>
                    </div>
                    <div className="bg-slate-800 rounded-full h-2">
                      <div
                        className="bg-gradient-to-r from-indigo-600 to-purple-600 h-2 rounded-full transition-all"
                        style={{ width: `${Math.min((m.project_count / 8) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Priority distribution */}
          <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Priority Distribution</h3>
            {(() => {
              const dist = stats?.priority_distribution ?? {};
              const counts: Record<string, number> = {
                urgent: dist["urgent"] ?? 0,
                high: dist["high"] ?? 0,
                medium: dist["medium"] ?? 0,
                low: dist["low"] ?? 0,
              };
              const total = Object.values(counts).reduce((a, b) => a + b, 0);
              return (
                <div className="space-y-3">
                  {(["urgent", "high", "medium", "low"] as const).map((p) => {
                    const cfg = PRIORITY_CONFIG[p];
                    const pct = total > 0 ? Math.round((counts[p] / total) * 100) : 0;
                    return (
                      <div key={p}>
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-xs font-medium ${cfg.color}`}>{cfg.label}</span>
                          <span className="text-xs text-slate-500">{counts[p]} ({pct}%)</span>
                        </div>
                        <div className="bg-slate-800 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full transition-all"
                            style={{
                              width: `${pct}%`,
                              background: p === "urgent" ? "#ef4444" : p === "high" ? "#f59e0b" : p === "medium" ? "#6366f1" : "#64748b",
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })()}
          </div>
        </div>

        {/* Task Balance Chart */}
        <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-white mb-1">Task Balance</h3>
          <p className="text-xs text-slate-500 mb-4">Overdue vs upcoming tasks per person — High / Medium / Low priority</p>
          {balanceLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-7 bg-slate-800 rounded animate-pulse" />
              ))}
            </div>
          ) : !taskBalance || taskBalance.people.length === 0 ? (
            <p className="text-slate-500 text-sm text-center py-6">No task data</p>
          ) : (
            <TaskBalanceChart data={taskBalance} />
          )}
        </div>

        {/* AI Insights */}
        {(stats?.ai_insights?.length ?? 0) > 0 && (
          <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
              <span className="ai-pulse text-indigo-400">✦</span>
              AI Operational Insights
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {stats!.ai_insights.slice(0, 4).map((ins) => (
                <div key={ins.id} className="bg-slate-900/60 border border-slate-800 rounded-lg p-3">
                  <p className="text-[10px] text-indigo-400 uppercase tracking-wide mb-1">
                    {ins.insight_type.replace("_", " ")}
                  </p>
                  <p className="text-xs text-slate-300 leading-relaxed line-clamp-3">{ins.body}</p>
                  <div className="mt-2 flex items-center gap-1">
                    <div className="w-12 bg-slate-700 rounded-full h-1">
                      <div className="bg-indigo-500 h-1 rounded-full" style={{ width: `${ins.confidence_score * 100}%` }} />
                    </div>
                    <span className="text-[10px] text-slate-600">{Math.round(ins.confidence_score * 100)}%</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
