"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { aiApi, projectsApi } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { cn } from "@/lib/utils";
import type { IntakeResult, PriorityLevel, Project } from "@/lib/types";
import { PRIORITY_CONFIG } from "@/lib/types";

const PRIORITY_OPTIONS: PriorityLevel[] = ["low", "medium", "high", "urgent"];

type ItemType = "project" | "task";
type ProjectMode = "existing" | "new";

export default function IntakePage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [rawInput, setRawInput] = useState("");
  const [result, setResult] = useState<IntakeResult | null>(null);
  const [confirmedPriority, setConfirmedPriority] = useState<PriorityLevel | null>(null);
  const [confirming, setConfirming] = useState(false);

  // Routing state (Option C): is this a project or a task, and where does a task go?
  const [itemType, setItemType] = useState<ItemType>("project");
  const [projectMode, setProjectMode] = useState<ProjectMode>("existing");
  const [targetProjectId, setTargetProjectId] = useState("");
  const [newProjectTitle, setNewProjectTitle] = useState("");

  // Existing projects for the task→existing picker. Only fetched when needed.
  const {
    data: projects = [],
    isLoading: projectsLoading,
    isError: projectsError,
  } = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: () => projectsApi.list({ limit: 200 }),
    enabled: itemType === "task" && projectMode === "existing",
  });

  const resetRouting = (data?: IntakeResult | null) => {
    setItemType(data?.suggested_item_type ?? "project");
    setProjectMode("existing");
    setTargetProjectId("");
    setNewProjectTitle(data?.generated_title ?? "");
  };

  const analyzeMutation = useMutation({
    mutationFn: (input: string) => aiApi.intake(input),
    onSuccess: (data: IntakeResult) => {
      setResult(data);
      setConfirmedPriority(data.suggested_priority ?? "medium");
      resetRouting(data);
    },
  });

  const confirmMutation = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = {
        confirmed_priority: confirmedPriority,
        item_type: itemType,
      };
      if (itemType === "task") {
        if (projectMode === "existing") {
          body.target_project_id = targetProjectId;
        } else {
          body.new_project_title = newProjectTitle || result?.generated_title;
        }
      }
      return aiApi.confirmIntake(result!.id, body);
    },
    onSuccess: () => {
      // The board uses ["projects-kanban", ...] and the dashboard uses
      // ["dashboard"] / ["my-dashboard"] — invalidate all so the new
      // project/tasks and activity appear without a manual reload.
      queryClient.invalidateQueries({
        predicate: (q) =>
          ["projects", "projects-kanban", "dashboard", "my-dashboard"].includes(
            q.queryKey[0] as string
          ),
      });
      router.push("/board");
    },
  });

  const handleAnalyze = (e: React.FormEvent) => {
    e.preventDefault();
    if (rawInput.trim().length >= 10) {
      analyzeMutation.mutate(rawInput.trim());
    }
  };

  const handleConfirm = () => {
    setConfirming(true);
    confirmMutation.mutate();
  };

  const handleDiscard = () => {
    setResult(null);
    setRawInput("");
    resetRouting(null);
  };

  // Dynamic button label + gating (no more hardcoded "Create Project").
  const selectedProject = projects.find((p) => p.id === targetProjectId);
  const taskExistingNeedsProject =
    itemType === "task" && projectMode === "existing" && !targetProjectId;

  const confirmLabel =
    itemType === "project"
      ? "✓ Create Project"
      : projectMode === "existing"
      ? `✓ Add to ${selectedProject?.title ?? "project"}`
      : "✓ Create Project + Task(s)";
  const pendingLabel =
    itemType === "project"
      ? "Creating project…"
      : projectMode === "existing"
      ? "Adding tasks…"
      : "Creating…";

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header
        title="AI Request Intake"
        subtitle="Describe your project or request in plain language"
      />

      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="max-w-3xl mx-auto space-y-5">
          {/* Input form */}
          <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-6">
            <div className="flex items-center gap-2 mb-4">
              <span className="text-indigo-400 ai-pulse">✦</span>
              <h2 className="text-sm font-semibold text-white">Describe your request</h2>
            </div>

            <form onSubmit={handleAnalyze} className="space-y-4">
              <textarea
                value={rawInput}
                onChange={(e) => setRawInput(e.target.value)}
                placeholder={`Example:\n"Can we build an accounting AI agent that classifies expenses and detects anomalies? Tom wants it ready by end of month."`}
                rows={5}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-indigo-500 transition-colors leading-relaxed"
              />

              <div className="flex items-center justify-between">
                <p className="text-xs text-slate-600">
                  Paste emails, meeting notes, Slack messages, or any unstructured text
                </p>
                <button
                  type="submit"
                  disabled={rawInput.length < 10 || analyzeMutation.isPending}
                  className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  {analyzeMutation.isPending ? (
                    <>
                      <span className="ai-pulse">✦</span>
                      <span>Analyzing…</span>
                    </>
                  ) : (
                    <>
                      <span>✦</span>
                      <span>Analyze with AI</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* AI Result */}
          {result && (
            <div className="bg-[#0f1629] border border-indigo-800/40 rounded-xl p-6 space-y-5">
              <div className="flex items-center gap-2 pb-4 border-b border-slate-800">
                <span className="text-indigo-400">✦</span>
                <h2 className="text-sm font-semibold text-white">AI Analysis</h2>
                <span className="text-[10px] bg-indigo-900/50 border border-indigo-800 text-indigo-400 px-1.5 py-0.5 rounded ml-auto">
                  Review & confirm
                </span>
              </div>

              {/* Generated title + description */}
              <div>
                <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-1">Generated Title</p>
                <p className="text-base font-semibold text-white">{result.generated_title}</p>
              </div>

              <div>
                <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-1">Description</p>
                <p className="text-sm text-slate-300 leading-relaxed">{result.generated_description}</p>
              </div>

              {/* Tags + type */}
              <div className="flex flex-wrap gap-2">
                {result.suggested_tags.map((tag) => (
                  <span key={tag} className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">
                    {tag}
                  </span>
                ))}
                {result.project_type && (
                  <span className="text-xs bg-indigo-900/40 text-indigo-400 px-2 py-0.5 rounded-full border border-indigo-800">
                    {result.project_type}
                  </span>
                )}
              </div>

              {/* Suggested subtasks */}
              {result.suggested_subtasks?.length > 0 && (
                <div>
                  <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-2">
                    {itemType === "task" ? "Task(s) to create" : "Suggested Subtasks"}
                  </p>
                  <ul className="space-y-1.5">
                    {(Array.isArray(result.suggested_subtasks) ? result.suggested_subtasks : []).map((task: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                        <span className="text-indigo-500 mt-0.5 shrink-0">○</span>
                        <span>{task}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* AI reasoning */}
              {result.ai_reasoning && (
                <div className="bg-indigo-950/30 border border-indigo-900/50 rounded-lg p-3">
                  <p className="text-[11px] text-indigo-400 uppercase tracking-wide mb-1">AI Reasoning</p>
                  <p className="text-xs text-slate-400 leading-relaxed">{result.ai_reasoning}</p>
                </div>
              )}

              {/* ═══════════════════════════════════════════════════════════
                  WHAT TO CREATE — project vs task routing (Option C).
                  AI suggests a type; the human can override and choose where
                  a task lands (existing project or a new one).
              ═══════════════════════════════════════════════════════════ */}
              <div className="bg-slate-900/60 border border-slate-700 rounded-xl p-4 space-y-3">
                <p className="text-sm font-semibold text-white">What should this become?</p>
                <div className="grid grid-cols-2 gap-2">
                  {(["project", "task"] as ItemType[]).map((t) => {
                    const isSelected = itemType === t;
                    const isSuggested = result.suggested_item_type === t;
                    return (
                      <button
                        key={t}
                        onClick={() => setItemType(t)}
                        className={cn(
                          "py-2 px-3 rounded-lg border text-xs font-medium transition-smooth",
                          isSelected
                            ? "bg-indigo-900/40 text-indigo-300 border-indigo-600"
                            : "border-slate-700 text-slate-500 hover:border-slate-600"
                        )}
                      >
                        {t === "project" ? "Project" : "Task"}
                        {isSuggested && !isSelected && (
                          <span className="block text-[9px] text-slate-600 mt-0.5">AI suggests</span>
                        )}
                        {isSelected && (
                          <span className="block text-[9px] mt-0.5 opacity-80">Selected ✓</span>
                        )}
                      </button>
                    );
                  })}
                </div>

                {itemType === "task" && (
                  <div className="space-y-2 pt-1">
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={() => setProjectMode("existing")}
                        className={cn(
                          "py-2 px-3 rounded-lg border text-xs font-medium transition-smooth",
                          projectMode === "existing"
                            ? "bg-slate-800 text-white border-slate-500"
                            : "border-slate-700 text-slate-500 hover:border-slate-600"
                        )}
                      >
                        Add to existing project
                      </button>
                      <button
                        onClick={() => setProjectMode("new")}
                        className={cn(
                          "py-2 px-3 rounded-lg border text-xs font-medium transition-smooth",
                          projectMode === "new"
                            ? "bg-slate-800 text-white border-slate-500"
                            : "border-slate-700 text-slate-500 hover:border-slate-600"
                        )}
                      >
                        Create new project
                      </button>
                    </div>

                    {projectMode === "existing" ? (
                      <div>
                        <select
                          value={targetProjectId}
                          onChange={(e) => setTargetProjectId(e.target.value)}
                          disabled={projectsLoading || projectsError}
                          className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 disabled:opacity-50"
                        >
                          <option value="">
                            {projectsLoading
                              ? "Loading projects…"
                              : projectsError
                              ? "Could not load projects"
                              : "Select a project…"}
                          </option>
                          {projects.map((p) => (
                            <option key={p.id} value={p.id}>{p.title}</option>
                          ))}
                        </select>
                        {projectsError && (
                          <p className="text-[11px] text-red-400 mt-1">
                            Failed to load projects. Switch to &ldquo;Create new project&rdquo; or retry.
                          </p>
                        )}
                      </div>
                    ) : (
                      <input
                        value={newProjectTitle}
                        onChange={(e) => setNewProjectTitle(e.target.value)}
                        placeholder="New project title"
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    )}
                  </div>
                )}
              </div>

              {/* ═══════════════════════════════════════════════════════════
                  HUMAN PRIORITY CONFIRMATION — CRITICAL UX REQUIREMENT
                  AI never auto-sets priority. User MUST confirm.
              ═══════════════════════════════════════════════════════════ */}
              <div className="bg-slate-900/60 border border-slate-700 rounded-xl p-4">
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-amber-400">⚠</span>
                  <p className="text-sm font-semibold text-white">Confirm Priority</p>
                  <span className="text-[10px] text-amber-600 bg-amber-950/40 border border-amber-800/40 px-1.5 py-0.5 rounded">
                    Human review required
                  </span>
                </div>

                <p className="text-xs text-slate-400 mb-3">
                  AI suggests{" "}
                  <span className={cn("font-semibold", PRIORITY_CONFIG[result.suggested_priority ?? "medium"].color)}>
                    {result.suggested_priority?.toUpperCase() ?? "MEDIUM"}
                  </span>
                  . You must confirm or adjust before creating.
                </p>

                <div className="grid grid-cols-4 gap-2">
                  {PRIORITY_OPTIONS.map((p) => {
                    const cfg = PRIORITY_CONFIG[p];
                    const isSelected = confirmedPriority === p;
                    const isSuggested = result.suggested_priority === p;
                    return (
                      <button
                        key={p}
                        onClick={() => setConfirmedPriority(p)}
                        className={cn(
                          "py-2 px-3 rounded-lg border text-xs font-medium transition-smooth",
                          isSelected
                            ? `${cfg.bg} ${cfg.color} border-current`
                            : "border-slate-700 text-slate-500 hover:border-slate-600"
                        )}
                      >
                        {cfg.label}
                        {isSuggested && !isSelected && (
                          <span className="block text-[9px] text-slate-600 mt-0.5">AI suggests</span>
                        )}
                        {isSelected && (
                          <span className="block text-[9px] mt-0.5 opacity-80">Selected ✓</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={handleConfirm}
                  disabled={!confirmedPriority || confirmMutation.isPending || taskExistingNeedsProject}
                  className="flex-1 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium text-sm rounded-lg transition-colors"
                >
                  {confirmMutation.isPending ? pendingLabel : confirmLabel}
                </button>
                <button
                  onClick={handleDiscard}
                  className="px-4 py-2.5 border border-slate-700 text-slate-400 hover:text-white text-sm rounded-lg transition-colors"
                >
                  Discard
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
