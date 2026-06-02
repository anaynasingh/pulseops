"use client";

import type { DashboardStats } from "@/lib/types";

interface StatCardProps {
  label: string;
  value: number | string;
  icon: string;
  color: string;
  loading?: boolean;
}

function StatCard({ label, value, icon, color, loading }: StatCardProps) {
  return (
    <div className={`bg-[#0f1629] border border-slate-800 rounded-xl p-4 relative overflow-hidden`}>
      <div className={`absolute top-0 left-0 right-0 h-0.5 ${color}`} />
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-500 mb-1">{label}</p>
          {loading ? (
            <div className="h-7 w-12 bg-slate-800 rounded animate-pulse" />
          ) : (
            <p className="text-2xl font-bold text-white">{value}</p>
          )}
        </div>
        <span className="text-xl opacity-60">{icon}</span>
      </div>
    </div>
  );
}

export function StatsGrid({ stats, loading }: { stats?: DashboardStats; loading?: boolean }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      <StatCard label="Total Projects"  value={stats?.total_projects ?? 0}  icon="◈" color="bg-indigo-500" loading={loading} />
      <StatCard label="Active"          value={stats?.active_projects ?? 0}  icon="▶" color="bg-blue-500"   loading={loading} />
      <StatCard label="Blocked"         value={stats?.blocked_projects ?? 0} icon="⊗" color="bg-red-500"    loading={loading} />
      <StatCard label="Done This Week"  value={stats?.done_this_week ?? 0}   icon="✓" color="bg-green-500"  loading={loading} />
      <StatCard label="Intake Queue"    value={stats?.intake_queue ?? 0}     icon="✦" color="bg-purple-500" loading={loading} />
      <StatCard label="Overdue"         value={stats?.overdue_projects ?? 0} icon="⚠" color="bg-amber-500"  loading={loading} />
    </div>
  );
}
