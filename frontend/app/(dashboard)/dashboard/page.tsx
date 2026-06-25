"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { analyticsApi } from "@/lib/api";
import { useAuthStore, useUIStore } from "@/lib/store";
import { Header } from "@/components/layout/Header";
import { StatsGrid } from "@/components/dashboard/StatsGrid";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { AIInsightsPanel } from "@/components/dashboard/AIInsightsPanel";
import { HighPriorityList } from "@/components/dashboard/HighPriorityList";
import { MyTasksList } from "@/components/dashboard/MyTasksList";
import { TaskBalanceChart } from "@/components/dashboard/TaskBalanceChart";
import type { DashboardStats, TaskBalanceResponse } from "@/lib/types";

export default function DashboardPage() {
  const { user } = useAuthStore();
  const { theme } = useUIStore();
  const isLight = theme === "light";
  const [view, setView] = useState<"mine" | "team">("mine");

  // Personal dashboard — cache for 2 min, refetch every 2 min (not 30s)
  const { data: myData, isLoading: myLoading } = useQuery({
    queryKey: ["my-dashboard"],
    queryFn: () => analyticsApi.myDashboard(),
    staleTime: 2 * 60_000,
    refetchInterval: 2 * 60_000,
  });

  // Team dashboard
  const { data: teamStats, isLoading: teamLoading } = useQuery<DashboardStats>({
    queryKey: ["dashboard"],
    queryFn: () => analyticsApi.dashboard(),
    refetchInterval: 30_000,
    enabled: view === "team",
  });

  // Task balance — team-wide overdue vs upcoming per person
  const { data: taskBalance, isLoading: balanceLoading } = useQuery<TaskBalanceResponse>({
    queryKey: ["task-balance"],
    queryFn: () => analyticsApi.taskBalance(),
    enabled: view === "team",
  });

  const isLoading = view === "mine" ? myLoading : teamLoading;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title={view === "mine" ? `My Dashboard` : "Team Dashboard"}
        subtitle={view === "mine" ? `Welcome back, ${user?.name?.split(" ")[0] ?? ""}` : "Full team overview"}
        actions={
          <div className="flex items-center gap-2">
            {/* Mine / Team toggle */}
            <div className="flex items-center bg-slate-900 border border-slate-700 rounded-lg p-0.5 shrink-0">
              <button
                onClick={() => setView("mine")}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                  view === "mine"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                My Tasks
              </button>
              <button
                onClick={() => setView("team")}
                className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                  view === "team"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                Team View
              </button>
            </div>
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto px-3 md:px-6 py-4 md:py-5 space-y-4 md:space-y-6">

        {/* ── MY VIEW ── */}
        {view === "mine" && (
          <>
            {/* Personal stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
              {[
                { label: "My Tasks",      value: myData?.stats?.my_total_tasks    ?? 0, icon: "✓", color: "bg-indigo-500" },
                { label: "High Priority", value: myData?.stats?.my_high_priority  ?? 0, icon: "🔥", color: "bg-red-500" },
                { label: "Overdue",       value: myData?.stats?.my_overdue        ?? 0, icon: "⚠", color: "bg-amber-500" },
                { label: "My Projects",   value: myData?.stats?.my_projects       ?? 0, icon: "◈", color: "bg-blue-500" },
              ].map((s) => (
                <div key={s.label} className={`border rounded-xl p-5 relative overflow-hidden ${isLight ? "bg-white border-slate-200" : "bg-[#0f1629] border-slate-800"}`}>
                  <div className={`absolute top-0 left-0 right-0 h-1 rounded-t-xl ${s.color}`} />
                  <div className="flex items-start justify-between mt-1">
                    <div>
                      <p className={`text-sm font-medium mb-1.5 ${isLight ? "text-slate-600" : "text-slate-400"}`}>{s.label}</p>
                      {myLoading ? (
                        <div className={`h-9 w-12 rounded animate-pulse ${isLight ? "bg-slate-200" : "bg-slate-800"}`} />
                      ) : (
                        <p className={`text-3xl font-bold ${
                          s.label === "Overdue" && (myData?.stats?.my_overdue ?? 0) > 0
                            ? isLight ? "text-amber-700" : "text-amber-400"
                            : isLight ? "text-slate-900" : "text-white"
                        }`}>
                          {s.value}
                        </p>
                      )}
                    </div>
                    <span className="text-2xl">{s.icon}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Overdue alert */}
            {(myData?.stats?.my_overdue ?? 0) > 0 && (
              <div className={`border rounded-xl p-5 flex items-start gap-4 ${
                isLight ? "bg-red-50 border-red-300" : "bg-red-950/30 border-red-800/40"
              }`}>
                <span className={`text-xl mt-0.5 ${isLight ? "text-red-600" : "text-red-400"}`}>⚠</span>
                <div>
                  <p className={`text-base font-bold ${isLight ? "text-red-800" : "text-red-300"}`}>
                    You have {myData.stats.my_overdue} overdue task{myData.stats.my_overdue > 1 ? "s" : ""}
                  </p>
                  <p className={`text-sm mt-1 ${isLight ? "text-red-700" : "text-red-400"}`}>These tasks are past their due date — tackle them first.</p>
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 md:gap-5">
              {/* My tasks — 2 cols */}
              <div className="xl:col-span-2 space-y-4 md:space-y-5">
                <MyTasksList tasks={myData?.my_tasks ?? []} loading={myLoading} />
                <ActivityFeed activities={myData?.my_activity ?? []} loading={myLoading} title="My Recent Activity" />
              </div>

              {/* My projects + insights — 1 col */}
              <div className="space-y-5">
                <HighPriorityList
                  projects={myData?.my_projects ?? []}
                  loading={myLoading}
                  title="My Projects"
                  emptyMessage="No active projects assigned to you"
                />
              </div>
            </div>
          </>
        )}

        {/* ── TEAM VIEW ── */}
        {view === "team" && (
          <>
            <StatsGrid stats={teamStats} loading={teamLoading} />

            {/* Task Balance — overdue (left) vs upcoming (right) per person */}
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

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
              <div className="lg:col-span-2 space-y-5">
                <HighPriorityList
                  projects={teamStats?.high_priority_projects ?? []}
                  loading={teamLoading}
                />
                {(teamStats?.stale_projects?.length ?? 0) > 0 && (
                  <div className="bg-amber-950/30 border border-amber-800/40 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <span className="text-amber-400 text-sm">⚠</span>
                      <h3 className="text-sm font-medium text-amber-300">Stale Projects</h3>
                      <span className="text-xs text-amber-600 bg-amber-900/50 px-1.5 py-0.5 rounded">
                        {teamStats!.stale_projects.length} inactive
                      </span>
                    </div>
                    <div className="space-y-2">
                      {teamStats!.stale_projects.map((p) => (
                        <div key={p.id} className="flex items-center gap-3 text-sm">
                          <span className="text-slate-300 truncate flex-1">{p.title}</span>
                          <span className="text-slate-500 text-xs shrink-0">{p.status.replace("_", " ")}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <ActivityFeed activities={teamStats?.recent_activity ?? []} loading={teamLoading} />
              </div>
              <div className="space-y-5">
                <AIInsightsPanel insights={teamStats?.ai_insights ?? []} loading={teamLoading} />
                {(teamStats?.team_workload?.length ?? 0) > 0 && (
                  <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
                    <h3 className="text-sm font-semibold text-white mb-4">Team Workload</h3>
                    <div className="space-y-3">
                      {teamStats!.team_workload.map((m) => (
                        <div key={m.user_id} className="bg-slate-900/60 rounded-lg p-3">
                          <div className="flex items-center justify-between mb-1.5">
                            <p className="text-xs font-medium text-slate-300 truncate">{m.name}</p>
                            <span className="text-xs text-slate-400">{m.project_count} projects</span>
                          </div>
                          <div className="w-full bg-slate-800 rounded-full h-1.5">
                            <div
                              className="bg-indigo-500 h-1.5 rounded-full transition-all"
                              style={{ width: `${Math.min((m.project_count / 10) * 100, 100)}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

      </div>
    </div>
  );
}
