"use client";

import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { AIInsightsPanel } from "@/components/dashboard/AIInsightsPanel";
import { HighPriorityList } from "@/components/dashboard/HighPriorityList";
import type { DashboardStats } from "@/lib/types";

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard"],
    queryFn: () => analyticsApi.dashboard(),
    refetchInterval: 30_000,
  });

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title="Dashboard"
        subtitle="Operational overview"
        actions={
          <button className="text-xs text-slate-400 hover:text-white transition-colors px-2 py-1 rounded border border-slate-700 hover:border-slate-600">
            Generate Report
          </button>
        }
      />

      <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
        {/* Stats */}
        <StatsGrid stats={stats} loading={isLoading} />

        {/* Main grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Activity feed — 2 cols */}
          <div className="lg:col-span-2 space-y-5">
            {/* High priority work */}
            <HighPriorityList
              projects={stats?.high_priority_projects ?? []}
              loading={isLoading}
            />
            {/* Stale projects warning */}
            {(stats?.stale_projects?.length ?? 0) > 0 && (
              <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-amber-400 text-sm">⚠</span>
                  <h3 className="text-sm font-medium text-amber-300">Stale Projects</h3>
                  <span className="text-xs text-amber-600 bg-amber-900/50 px-1.5 py-0.5 rounded">
                    {stats!.stale_projects.length} inactive
                  </span>
                </div>
                <div className="space-y-2">
                  {stats!.stale_projects.map((p) => (
                    <div key={p.id} className="flex items-center gap-3 text-sm">
                      <span className="text-slate-300 truncate flex-1">{p.title}</span>
                      <span className="text-slate-500 text-xs shrink-0">
                        {p.status.replace("_", " ")}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <ActivityFeed activities={stats?.recent_activity ?? []} loading={isLoading} />
          </div>

          {/* AI Insights — 1 col */}
          <div>
            <AIInsightsPanel insights={stats?.ai_insights ?? []} loading={isLoading} />
          </div>
        </div>

        {/* Team workload */}
        {(stats?.team_workload?.length ?? 0) > 0 && (
          <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-white mb-4">Team Workload</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {stats!.team_workload.map((m) => (
                <div key={m.user_id} className="bg-slate-900/60 rounded-lg p-3">
                  <p className="text-xs font-medium text-slate-300 mb-1 truncate">{m.name}</p>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-slate-800 rounded-full h-1.5">
                      <div
                        className="bg-indigo-500 h-1.5 rounded-full"
                        style={{ width: `${Math.min((m.project_count / 10) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-400 shrink-0">{m.project_count}</span>
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
