"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { aiApi, projectsApi, api } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { PRIORITY_CONFIG } from "@/lib/types";
import type { TranscriptResult, Project } from "@/lib/types";

export default function MeetingsPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [transcript, setTranscript] = useState("");
  const [source, setSource] = useState("manual");
  const [result, setResult] = useState<TranscriptResult | null>(null);
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [tasksCreated, setTasksCreated] = useState(false);
  const [createdCount, setCreatedCount] = useState(0);
  const [feedbackGiven, setFeedbackGiven] = useState<boolean | null>(null);
  const [searchLogId, setSearchLogId] = useState<string | null>(null);

  const { data: projects } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list(),
  });

  // Transcript search diagnostics
  const { data: diagnostics, refetch: refetchDiagnostics } = useQuery({
    queryKey: ["transcript-diagnostics"],
    queryFn: () => api.get("/ai/transcript-search-diagnostics").then(r => r.data),
    staleTime: 30_000,
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      aiApi.extractTranscript({ title, raw_transcript: transcript, source }),
    onSuccess: (data: TranscriptResult & { log_id?: string }) => {
      setResult(data);
      setSelectedIndices(new Set(data.action_items.map((_, i) => i)));
      setTasksCreated(false);
      setCreatedCount(0);
      setFeedbackGiven(null);
      setSearchLogId(data.log_id ?? null);
    },
  });

  const feedbackMutation = useMutation({
    mutationFn: ({ correct, note }: { correct: boolean; note?: string }) =>
      api.post("/ai/transcript-feedback", { log_id: searchLogId, was_correct: correct, correction_note: note || null }).then(r => r.data),
    onSuccess: (_, vars) => setFeedbackGiven(vars.correct),
  });

  const createTasksMutation = useMutation({
    mutationFn: () => {
      if (!result) throw new Error("No result");
      const indices = Array.from(selectedIndices);
      // If no project selected, use transcript's linked project or prompt user
      const projectId = selectedProjectId || result.project_id || "";
      if (!projectId) throw new Error("Please select a project");
      return aiApi.transcriptCreateTasks(result.id, indices, projectId);
    },
    onSuccess: (data) => {
      setTasksCreated(true);
      setCreatedCount(data.tasks_created);
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const toggleIndex = (i: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const selectAll = () => {
    if (!result) return;
    setSelectedIndices(new Set(result.action_items.map((_, i) => i)));
  };

  const deselectAll = () => setSelectedIndices(new Set());

  const canCreate = result && selectedIndices.size > 0 && (selectedProjectId || result.project_id);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header title="Meeting Intelligence" subtitle="Extract action items and decisions from transcripts" />

      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="max-w-3xl mx-auto space-y-5">

          {/* ── Graph API Diagnostics panel — always shown ── */}
          {true && (
            <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <span className="text-indigo-400 text-sm">◈</span>
                  <h2 className="text-sm font-semibold text-white">Transcript Search Performance</h2>
                  <span className="text-[10px] text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">Microsoft Graph</span>
                </div>
                <button
                  onClick={() => refetchDiagnostics()}
                  className="text-[11px] text-slate-500 hover:text-slate-300 transition-colors"
                >
                  Refresh
                </button>
              </div>

              {/* Stats row */}
              <div className="grid grid-cols-4 gap-3 mb-4">
                {[
                  { label: "Total searches", value: diagnostics?.summary?.total ?? 0, color: "text-white" },
                  { label: "Correct", value: diagnostics?.summary?.correct ?? 0, color: "text-green-400" },
                  { label: "Wrong", value: diagnostics?.summary?.wrong ?? 0, color: "text-red-400" },
                  { label: "Accuracy", value: `${diagnostics?.accuracy_pct ?? 0}%`, color: (diagnostics?.accuracy_pct ?? 0) >= 80 ? "text-green-400" : (diagnostics?.accuracy_pct ?? 0) >= 50 ? "text-amber-400" : "text-red-400" },
                ].map(s => (
                  <div key={s.label} className="bg-slate-900/60 rounded-lg p-3 text-center">
                    <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{s.label}</p>
                  </div>
                ))}
              </div>

              {/* Accuracy bar */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[11px] text-slate-500">Accuracy rate</span>
                  <span className="text-[11px] text-slate-400">{diagnostics.accuracy_pct ?? 0}%</span>
                </div>
                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-2 rounded-full transition-all ${
                      (diagnostics.accuracy_pct ?? 0) >= 80 ? "bg-green-500" :
                      (diagnostics.accuracy_pct ?? 0) >= 50 ? "bg-amber-500" : "bg-red-500"
                    }`}
                    style={{ width: `${diagnostics?.accuracy_pct ?? 0}%` }}
                  />
                </div>
              </div>

              {/* Wrong cases */}
              {(diagnostics?.wrong_cases?.length ?? 0) > 0 ? (
                <div>
                  <p className="text-[11px] text-red-400 uppercase tracking-wide font-medium mb-2">
                    Wrong cases ({diagnostics?.wrong_cases?.length})
                  </p>
                  <div className="space-y-2">
                    {diagnostics?.wrong_cases?.map((c: any, i: number) => (
                      <div key={i} className="bg-red-950/20 border border-red-900/30 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <span className="text-red-400 text-xs shrink-0 mt-0.5">✗</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-xs text-slate-300">
                              <span className="text-slate-500">Searched:</span> {c.searched_for}
                            </p>
                            <p className="text-xs text-slate-300 mt-0.5">
                              <span className="text-slate-500">Got back:</span> {c.got_back}
                              {c.date_returned && <span className="text-slate-600 ml-1">({c.date_returned})</span>}
                            </p>
                            {c.note && (
                              <p className="text-xs text-amber-400 mt-0.5 italic">Note: {c.note}</p>
                            )}
                            <p className="text-[10px] text-slate-600 mt-1">{new Date(c.at).toLocaleString()}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {(diagnostics?.wrong_cases?.length ?? 0) >= 3 && (
                    <p className="text-[11px] text-indigo-400 mt-3">
                      💡 Ask Claude: <em>"Look at the transcript diagnostics and find the pattern in these wrong results"</em>
                    </p>
                  )}
                </div>
              ) : (diagnostics?.summary?.total ?? 0) > 0 ? (
                <p className="text-xs text-green-400 flex items-center gap-1.5">
                  <span>✓</span> All transcript searches have been correct so far
                </p>
              ) : (
                <p className="text-xs text-slate-600 text-center py-2">
                  No searches logged yet. Once you fetch transcripts via Claude, accuracy will appear here.
                </p>
              )}
            </div>
          )}

          {/* Input */}
          <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-indigo-400">◎</span>
              <h2 className="text-sm font-semibold text-white">Paste Meeting Transcript</h2>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1.5">Meeting Title</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Q2 Sprint Planning"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1.5">Source</label>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
                >
                  <option value="manual">Manual paste</option>
                  <option value="zoom">Zoom</option>
                  <option value="teams">Microsoft Teams</option>
                  <option value="google_meet">Google Meet</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-500 mb-1.5">Transcript</label>
              <textarea
                value={transcript}
                onChange={(e) => setTranscript(e.target.value)}
                placeholder={`Paste your meeting transcript here...\n\nExample:\n"Anayna: Let's discuss the API timeline.\nStephen: I'll finish the auth system by Wednesday.\nTom: I'll take the database schema."`}
                rows={8}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-indigo-500 transition-colors leading-relaxed"
              />
            </div>

            <button
              onClick={() => analyzeMutation.mutate()}
              disabled={!title || transcript.length < 50 || analyzeMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {analyzeMutation.isPending ? (
                <><span className="ai-pulse">✦</span><span>Analyzing…</span></>
              ) : (
                <><span>✦</span><span>Analyze Transcript</span></>
              )}
            </button>
          </div>

          {/* Result */}
          {result && (
            <div className="bg-[#0f1629] border border-indigo-800/40 rounded-xl p-6 space-y-5">
              <h2 className="text-sm font-semibold text-white border-b border-slate-800 pb-4">
                📋 Meeting Analysis — {result.title}
              </h2>

              {/* Summary */}
              <div>
                <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-2">Summary</p>
                <p className="text-sm text-slate-300 leading-relaxed">{result.summary}</p>
              </div>

              {/* ── Transcript accuracy feedback ── */}
              {searchLogId && (
                <div className="flex items-center gap-3 py-2 px-3 rounded-lg border border-slate-700/60 bg-slate-900/40">
                  <span className="text-xs text-slate-400 shrink-0">Was this the right meeting?</span>
                  {feedbackGiven === null ? (
                    <>
                      <button
                        onClick={() => feedbackMutation.mutate({ correct: true })}
                        className="px-2.5 py-1 text-xs rounded-md bg-green-900/40 text-green-400 hover:bg-green-900/60 border border-green-800/40 transition-colors"
                      >
                        ✓ Yes
                      </button>
                      <button
                        onClick={() => {
                          const note = window.prompt("What was wrong? (e.g. 'wrong date', 'pulled last week meeting')");
                          feedbackMutation.mutate({ correct: false, note: note ?? undefined });
                        }}
                        className="px-2.5 py-1 text-xs rounded-md bg-red-900/40 text-red-400 hover:bg-red-900/60 border border-red-800/40 transition-colors"
                      >
                        ✗ Wrong meeting
                      </button>
                    </>
                  ) : feedbackGiven ? (
                    <span className="text-xs text-green-400">✓ Logged as correct</span>
                  ) : (
                    <span className="text-xs text-amber-400">⚠ Logged as wrong — helps us fix Graph search</span>
                  )}
                </div>
              )}

              {/* Attendees */}
              {result.attendees.length > 0 && (
                <div>
                  <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-2">Attendees</p>
                  <div className="flex flex-wrap gap-2">
                    {result.attendees.map((a) => (
                      <span key={a} className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full">
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Items — selectable */}
              {result.action_items.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-[11px] text-slate-500 uppercase tracking-wide">
                      Action Items ({selectedIndices.size}/{result.action_items.length} selected)
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={selectAll}
                        className="text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        Select All
                      </button>
                      <span className="text-slate-700">·</span>
                      <button
                        onClick={deselectAll}
                        className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
                      >
                        Deselect All
                      </button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    {result.action_items.map((item, i) => {
                      const selected = selectedIndices.has(i);
                      const priorityCfg = PRIORITY_CONFIG[item.priority] ?? PRIORITY_CONFIG.medium;
                      return (
                        <div
                          key={i}
                          onClick={() => toggleIndex(i)}
                          className={`flex items-start gap-3 rounded-lg p-3 cursor-pointer transition-colors border ${
                            selected
                              ? "bg-indigo-950/30 border-indigo-700/50"
                              : "bg-slate-900/60 border-transparent hover:border-slate-700"
                          }`}
                        >
                          {/* Checkbox */}
                          <div className={`w-4 h-4 rounded border-2 shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                            selected ? "border-indigo-500 bg-indigo-500" : "border-slate-600"
                          }`}>
                            {selected && <span className="text-[8px] text-white font-bold">✓</span>}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-slate-200">{item.task}</p>
                            <div className="flex items-center gap-3 mt-1 flex-wrap">
                              {item.owner && (
                                <span className="text-[11px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded-full">
                                  {item.owner}
                                </span>
                              )}
                              {item.deadline && (
                                <span className="text-[11px] text-amber-500">Due: {item.deadline}</span>
                              )}
                            </div>
                          </div>
                          <span className={`text-[10px] font-medium shrink-0 px-1.5 py-0.5 rounded ${priorityCfg.color} ${priorityCfg.bg}`}>
                            {priorityCfg.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Decisions */}
              {result.decisions.length > 0 && (
                <div>
                  <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-2">Decisions</p>
                  <ul className="space-y-1.5">
                    {result.decisions.map((d, i) => (
                      <li key={i} className="text-sm text-slate-300 flex items-start gap-2">
                        <span className="text-green-500 shrink-0 mt-0.5">✓</span>
                        <span>{d}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Blockers */}
              {result.blockers.length > 0 && (
                <div className="bg-red-950/20 border border-red-800/30 rounded-lg p-3">
                  <p className="text-[11px] text-red-400 uppercase tracking-wide mb-2">Blockers Mentioned</p>
                  {result.blockers.map((b, i) => (
                    <p key={i} className="text-sm text-slate-300 flex items-start gap-2">
                      <span className="text-red-400">⊗</span> {b}
                    </p>
                  ))}
                </div>
              )}

              {/* Project picker + Create tasks */}
              {!tasksCreated ? (
                <div className="border-t border-slate-800 pt-4 space-y-3">
                  <div>
                    <label className="block text-xs text-slate-500 mb-1.5">Assign tasks to project</label>
                    <select
                      value={selectedProjectId || result.project_id || ""}
                      onChange={(e) => setSelectedProjectId(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-300 focus:outline-none focus:border-indigo-500"
                    >
                      <option value="">Select a project…</option>
                      {projects?.map((p) => (
                        <option key={p.id} value={p.id}>{p.title}</option>
                      ))}
                    </select>
                  </div>
                  {createTasksMutation.isError && (
                    <p className="text-xs text-red-400">
                      {(createTasksMutation.error as Error)?.message || "Failed to create tasks"}
                    </p>
                  )}
                  <button
                    onClick={() => createTasksMutation.mutate()}
                    disabled={!canCreate || createTasksMutation.isPending}
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium text-sm rounded-lg transition-colors"
                  >
                    {createTasksMutation.isPending
                      ? "Creating tasks…"
                      : `Create ${selectedIndices.size} Selected Task${selectedIndices.size !== 1 ? "s" : ""}`}
                  </button>
                </div>
              ) : (
                <div className="text-center py-3 text-green-400 text-sm font-medium border-t border-slate-800 pt-4">
                  ✓ {createdCount} task{createdCount !== 1 ? "s" : ""} created successfully
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
