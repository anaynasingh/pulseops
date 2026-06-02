"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "@/lib/api";
import type { AIInsight } from "@/lib/types";

const INSIGHT_ICONS: Record<string, string> = {
  blocker:        "⊗",
  risk:           "⚠",
  recommendation: "✦",
  next_action:    "→",
  velocity:       "◎",
};

const INSIGHT_COLORS: Record<string, string> = {
  blocker:        "border-red-800/60 bg-red-950/20",
  risk:           "border-amber-800/60 bg-amber-950/20",
  recommendation: "border-indigo-800/60 bg-indigo-950/20",
  next_action:    "border-blue-800/60 bg-blue-950/20",
  velocity:       "border-green-800/60 bg-green-950/20",
};

export function AIInsightsPanel({
  insights,
  loading,
}: {
  insights: AIInsight[];
  loading?: boolean;
}) {
  const queryClient = useQueryClient();

  const dismiss = useMutation({
    mutationFn: (id: string) => aiApi.dismissInsight(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
  });

  return (
    <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5 h-fit">
      <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
        <span className="ai-pulse text-indigo-400">✦</span>
        <span>AI Insights</span>
      </h3>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-slate-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : insights.length === 0 ? (
        <div className="text-center py-8">
          <p className="text-slate-500 text-sm">No insights yet</p>
          <p className="text-slate-600 text-xs mt-1">AI insights appear as projects progress</p>
        </div>
      ) : (
        <div className="space-y-2.5">
          {insights.map((insight) => (
            <div
              key={insight.id}
              className={`rounded-lg p-3 border ${INSIGHT_COLORS[insight.insight_type] ?? "border-slate-800 bg-slate-900/40"}`}
            >
              <div className="flex items-start gap-2">
                <span className="text-sm shrink-0 mt-0.5">
                  {INSIGHT_ICONS[insight.insight_type] ?? "•"}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-slate-300 capitalize mb-1">
                    {insight.insight_type.replace("_", " ")}
                  </p>
                  <p className="text-xs text-slate-400 leading-relaxed">{insight.body}</p>
                  <div className="flex items-center justify-between mt-2">
                    <div className="flex items-center gap-1">
                      <div className="w-12 bg-slate-700 rounded-full h-1">
                        <div
                          className="bg-indigo-500 h-1 rounded-full"
                          style={{ width: `${insight.confidence_score * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-slate-600">
                        {Math.round(insight.confidence_score * 100)}% confidence
                      </span>
                    </div>
                    <button
                      onClick={() => dismiss.mutate(insight.id)}
                      className="text-[10px] text-slate-600 hover:text-slate-400 transition-colors"
                    >
                      dismiss
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
