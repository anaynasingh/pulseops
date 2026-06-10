"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { aiApi } from "@/lib/api";

interface DedupeMatch {
  proposed_title: string;
  match_type: "duplicate" | "update" | "new";
  existing_task_id?: string;
  existing_task_title?: string;
  existing_task_status?: string;
  confidence: number;
  suggestion: string;
  suggested_action: string;
  suggested_status?: string;
}

interface DedupeResult {
  matches: DedupeMatch[];
  summary: string;
  duplicates_found: number;
  updates_suggested: number;
}

interface DedupeModalProps {
  result: DedupeResult;
  projectId?: string;
  onDone: () => void;
  onCancel: () => void;
}

const ACTION_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  skip:          { label: "Skip — already exists",  color: "text-slate-600", bg: "bg-slate-100" },
  create:        { label: "Create as new task",      color: "text-green-700", bg: "bg-green-50" },
  update_status: { label: "Mark existing as done",   color: "text-indigo-700", bg: "bg-indigo-50" },
  merge:         { label: "Merge with existing",     color: "text-amber-700", bg: "bg-amber-50" },
};

const MATCH_ICONS: Record<string, string> = {
  duplicate: "⚠",
  update:    "✎",
  new:       "✚",
};

const MATCH_COLORS: Record<string, string> = {
  duplicate: "border-amber-200 bg-amber-50/50",
  update:    "border-indigo-200 bg-indigo-50/50",
  new:       "border-green-200 bg-green-50/50",
};

export function DedupeModal({ result, projectId, onDone, onCancel }: DedupeModalProps) {
  const queryClient = useQueryClient();

  // Local decision state — user can change each suggestion
  const [decisions, setDecisions] = useState<Record<string, string>>(
    Object.fromEntries(result.matches.map((m) => [m.proposed_title, m.suggested_action]))
  );

  const applyMutation = useMutation({
    mutationFn: () => {
      const confirmations = result.matches.map((m) => ({
        proposed_title: m.proposed_title,
        action: decisions[m.proposed_title] ?? m.suggested_action,
        task_id: m.existing_task_id,
        new_status: m.suggested_status ?? "done",
      }));
      return aiApi.applyDedupDecisions(confirmations, projectId);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["my-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      onDone();
    },
  });

  const hasActions = result.matches.some(m => decisions[m.proposed_title] !== "skip");

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">

        {/* Header */}
        <div className="p-6 pb-4 border-b border-slate-100">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <span className="text-indigo-600">✦</span>
                Smart Task Check
              </h2>
              <p className="text-sm text-slate-500 mt-1">{result.summary}</p>
            </div>
            <button onClick={onCancel} className="text-slate-400 hover:text-slate-600 text-xl ml-4">✕</button>
          </div>

          {/* Stats */}
          {(result.duplicates_found > 0 || result.updates_suggested > 0) && (
            <div className="flex gap-3 mt-3">
              {result.duplicates_found > 0 && (
                <span className="text-xs px-2 py-1 bg-amber-100 text-amber-700 rounded-full font-medium">
                  ⚠ {result.duplicates_found} duplicate{result.duplicates_found > 1 ? "s" : ""} found
                </span>
              )}
              {result.updates_suggested > 0 && (
                <span className="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded-full font-medium">
                  ✎ {result.updates_suggested} update suggestion{result.updates_suggested > 1 ? "s" : ""}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Task list */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          {result.matches.map((match) => {
            const decision = decisions[match.proposed_title] ?? match.suggested_action;
            const actionConfig = ACTION_LABELS[decision] ?? ACTION_LABELS.create;

            return (
              <div
                key={match.proposed_title}
                className={`rounded-xl border p-4 ${MATCH_COLORS[match.match_type] ?? "border-slate-200 bg-white"}`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-base mt-0.5 shrink-0">
                    {MATCH_ICONS[match.match_type]}
                  </span>
                  <div className="flex-1 min-w-0">
                    {/* Proposed task */}
                    <p className="text-sm font-semibold text-slate-900">{match.proposed_title}</p>

                    {/* AI suggestion */}
                    <p className="text-xs text-slate-500 mt-1 italic">{match.suggestion}</p>

                    {/* Existing task match */}
                    {match.existing_task_title && (
                      <div className="mt-2 flex items-center gap-2">
                        <span className="text-[11px] text-slate-400">Matches:</span>
                        <span className="text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded truncate max-w-xs">
                          {match.existing_task_title}
                          {match.existing_task_status && (
                            <span className="text-slate-400 ml-1">({match.existing_task_status})</span>
                          )}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {Math.round((match.confidence ?? 0) * 100)}% match
                        </span>
                      </div>
                    )}

                    {/* Action selector */}
                    <div className="mt-3 flex items-center gap-2 flex-wrap">
                      {Object.entries(ACTION_LABELS).map(([action, config]) => (
                        <button
                          key={action}
                          onClick={() => setDecisions(d => ({ ...d, [match.proposed_title]: action }))}
                          className={`text-xs px-2.5 py-1 rounded-lg border transition-all font-medium ${
                            decision === action
                              ? `${config.bg} ${config.color} border-current`
                              : "bg-white text-slate-400 border-slate-200 hover:border-slate-300"
                          }`}
                        >
                          {config.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="p-6 pt-4 border-t border-slate-100 flex items-center justify-between">
          <button onClick={onCancel} className="text-sm text-slate-400 hover:text-slate-600 transition-colors">
            Cancel
          </button>
          <div className="flex gap-2">
            <button
              onClick={() => setDecisions(Object.fromEntries(result.matches.map(m => [m.proposed_title, "skip"])))}
              className="px-4 py-2 text-sm border border-slate-300 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors"
            >
              Skip all
            </button>
            <button
              onClick={() => applyMutation.mutate()}
              disabled={applyMutation.isPending || !hasActions}
              className="px-5 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-50"
            >
              {applyMutation.isPending ? "Applying…" : "Confirm & Apply"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
