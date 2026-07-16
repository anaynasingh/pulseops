"use client";

import { useState, useRef, useEffect } from "react";
import { authApi, aiApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { PRIORITY_CONFIG } from "@/lib/types";
import type { PriorityLevel } from "@/lib/types";
import { DedupeModal } from "@/components/ai/DedupeModal";
import { ChatMarkdown } from "@/components/ai/ChatMarkdown";

interface ProposedTask {
  title: string;
  description?: string | null;
  priority?: string;
  assignee_name?: string | null;
  due_date_offset_days?: number | null;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  checking?: boolean;   // true while dedup is running
  proposedTasks?: ProposedTask[];
  proposedProjectId?: string | null;
  tasksConfirmed?: boolean;
  confirmedCount?: number;
}

const GREETING = "Hi! I'm PulseOps AI. I can help you understand your projects, find blockers, generate summaries, and suggest priorities. What would you like to know?";

const QUICK_PROMPTS = [
  "What should I focus on today?",
  "What are my overdue tasks?",
  "What are my top priorities right now?",
  "What's due this week?",
];

// Friendly text for the ?m365=<code> the OAuth callback redirects back with.
const M365_ERRORS: Record<string, string> = {
  error: "Microsoft sign-in was cancelled or failed.",
  invalid_state: "The sign-in link expired — please try again.",
  exchange_failed: "Couldn't complete Microsoft sign-in — please try again.",
  user_not_found: "Your PulseOps session wasn't found — sign in again, then retry.",
};

// The assistant proposes tasks by emitting a <<<PROPOSE_TASKS>>> {json} block instead
// of creating them. Parse it out so we can render the select + dedupe UI.
function parseProposeBlock(
  reply: string
): { tasks: ProposedTask[]; projectId: string | null; cleanedReply: string } | null {
  const m = reply.match(/<<<PROPOSE_TASKS>>>([\s\S]*?)<<<END_PROPOSE_TASKS>>>/);
  if (!m) return null;
  try {
    const parsed = JSON.parse(m[1].trim());
    const raw = Array.isArray(parsed?.tasks) ? parsed.tasks : [];
    const tasks: ProposedTask[] = raw
      .filter((t: Record<string, unknown>) => t && t.title)
      .map((t: Record<string, unknown>) => ({
        title: String(t.title),
        description: (t.description as string) ?? null,
        priority: (t.priority as string) ?? "medium",
        assignee_name: (t.assignee_name as string) ?? null,
        due_date_offset_days:
          typeof t.due_date_offset_days === "number" ? (t.due_date_offset_days as number) : null,
      }));
    return { tasks, projectId: (parsed?.project_id as string) ?? null, cleanedReply: reply.replace(m[0], "").trim() };
  } catch {
    return null;
  }
}

/**
 * Shared AI Assistant chat. Rendered both as the slide-in side panel
 * (variant="panel", with an onClose) and as the full-page view (variant="page").
 * Same functionality either way — only layout/spacing differ.
 */
export function AssistantChat({
  variant = "panel",
  onClose,
}: {
  variant?: "panel" | "page";
  onClose?: () => void;
}) {
  const isPage = variant === "page";
  const queryClient = useQueryClient();
  const STORAGE_KEY = "pulseops_chat_history";
  const CLAUDE_SESSION_KEY = "pulseops_claude_session";
  const [claudeSession, setClaudeSession] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(CLAUDE_SESSION_KEY);
  });
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window === "undefined") return [{ role: "assistant", content: GREETING }];
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) return JSON.parse(saved);
    } catch {}
    return [{ role: "assistant", content: GREETING }];
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [dedupeResult, setDedupeResult] = useState<any>(null);
  const [dedupeProjectId, setDedupeProjectId] = useState<string | undefined>();
  const [m365Connected, setM365Connected] = useState<boolean | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Whether this user has connected their own Microsoft account (for the assistant's
  // mail/calendar/transcript tools).
  useEffect(() => {
    let cancelled = false;
    authApi.m365Status()
      .then((s) => { if (!cancelled) setM365Connected(s.connected); })
      .catch(() => { if (!cancelled) setM365Connected(null); });
    return () => { cancelled = true; };
  }, []);

  // Reflect the OAuth callback result (?m365=connected|<error>) once, then clean the URL.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const r = params.get("m365");
    if (!r) return;
    if (r === "connected") { setM365Connected(true); setConnectError(null); }
    else setConnectError(M365_ERRORS[r] || "Couldn't connect Microsoft. Please try again.");
    params.delete("m365");
    const qs = params.toString();
    window.history.replaceState({}, "", window.location.pathname + (qs ? `?${qs}` : ""));
  }, []);

  // Kick off the Microsoft connect flow. On success this redirects the browser to
  // Microsoft (so the "connecting" state shows until it navigates away); on a fetch
  // failure we surface an error instead of silently doing nothing.
  const startConnect = async () => {
    setConnectError(null);
    setConnecting(true);
    try {
      await authApi.m365Connect();
    } catch {
      setConnecting(false);
      setConnectError("Couldn't start Microsoft sign-in. Please try again.");
    }
  };

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(messages)); } catch {}
  }, [messages]);

  useEffect(() => {
    try {
      if (claudeSession) localStorage.setItem(CLAUDE_SESSION_KEY, claudeSession);
      else localStorage.removeItem(CLAUDE_SESSION_KEY);
    } catch {}
  }, [claudeSession]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const clearChat = () => {
    setMessages([{ role: "assistant", content: GREETING }]);
    setClaudeSession(null);
    try { localStorage.removeItem(STORAGE_KEY); } catch {}
  };

  const handleSend = async (text: string = input) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await aiApi.claudeChat(text, claudeSession);
      if (res.session_id) setClaudeSession(res.session_id);

      // The assistant proposes new tasks via a structured block rather than
      // creating them — route those into the select + dedupe flow.
      const proposal = parseProposeBlock(res.reply || "");
      const replyText = (proposal ? proposal.cleanedReply : res.reply) || "The assistant finished but returned no text.";
      setMessages((m) => [...m, { role: "assistant", content: replyText, checking: !!(proposal && proposal.tasks.length) }]);

      if (proposal && proposal.tasks.length > 0) {
        try {
          const dedup = await aiApi.checkDuplicates(proposal.tasks as unknown as Record<string, unknown>[], text);
          const hasIssues = dedup.duplicates_found > 0 || dedup.updates_suggested > 0;
          if (hasIssues) {
            setDedupeResult(dedup);
            setDedupeProjectId(proposal.projectId || undefined);
            setMessages((m) => m.map((msg, i) => (i === m.length - 1 ? { ...msg, checking: false } : msg)));
          } else {
            setMessages((m) => m.map((msg, i) => (i === m.length - 1
              ? { ...msg, checking: false, proposedTasks: proposal.tasks, proposedProjectId: proposal.projectId, tasksConfirmed: false }
              : msg)));
          }
        } catch {
          setMessages((m) => m.map((msg, i) => (i === m.length - 1
            ? { ...msg, checking: false, proposedTasks: proposal.tasks, proposedProjectId: proposal.projectId, tasksConfirmed: false }
            : msg)));
        }
      } else {
        // No proposal — the assistant may have completed/moved/deleted something. Refresh.
        queryClient.invalidateQueries({ queryKey: ["projects"] });
        queryClient.invalidateQueries({ queryKey: ["my-dashboard"] });
        queryClient.invalidateQueries({ queryKey: ["tasks"] });
      }
    } catch (e: unknown) {
      const err = e as { response?: { status?: number; data?: { detail?: string } } };
      const detail = err.response?.data?.detail;
      const content =
        err.response?.status === 503
          ? "The assistant service isn't reachable right now. Please try again in a moment."
          : detail || "Something went wrong talking to the assistant. Please try again.";
      setMessages((m) => [...m, { role: "assistant", content }]);
    } finally {
      setLoading(false);
    }
  };

  const bubble = (role: "user" | "assistant") =>
    cn(
      "rounded-xl leading-relaxed",
      isPage ? "px-4 py-3 text-sm max-w-[85%]" : "px-3 py-2.5 text-xs max-w-[90%]",
      role === "user"
        ? "bg-indigo-600/20 border border-indigo-600/30 text-slate-200 ml-auto"
        : "bg-slate-900/60 border border-slate-800 text-slate-300"
    );
  const col = isPage ? "max-w-3xl mx-auto w-full" : "";

  return (
    <>
      {dedupeResult && (
        <DedupeModal
          result={dedupeResult}
          projectId={dedupeProjectId}
          onDone={() => { setDedupeResult(null); queryClient.invalidateQueries({ queryKey: ["my-dashboard"] }); }}
          onCancel={() => setDedupeResult(null)}
        />
      )}
      <div className="flex flex-col h-full min-h-0 bg-[#080f20]">
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3.5 border-b border-slate-800 shrink-0">
          <span className="text-indigo-400 ai-pulse">✦</span>
          <span className={cn("font-semibold text-white flex-1", isPage ? "text-base" : "text-sm")}>AI Assistant</span>
          <button
            onClick={clearChat}
            className="text-slate-500 hover:text-slate-300 transition-colors text-[10px] uppercase tracking-wide"
            title="Start a new chat"
          >
            {isPage ? "New chat" : "clear"}
          </button>
          {onClose && (
            <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors ml-1 text-lg leading-none">
              ×
            </button>
          )}
        </div>

        {/* Microsoft connect prompt — lets the assistant read the user's own mail/meetings */}
        {m365Connected === false && (
          <div className={cn("px-4 py-2 border-b border-slate-800/60 shrink-0", connectError ? "bg-red-950/20" : "bg-indigo-950/20")}>
            <div className={cn("flex items-center gap-2", col)}>
              <span className={cn("text-[11px] flex-1 leading-snug", connectError ? "text-red-300" : "text-slate-300")}>
                {connectError ? (
                  connectError
                ) : connecting ? (
                  "Connecting to Microsoft…"
                ) : (
                  <>Connect Microsoft so the assistant can read <b>your</b> emails &amp; meetings.</>
                )}
              </span>
              <button
                onClick={startConnect}
                disabled={connecting}
                className="text-[10px] px-2 py-1 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-medium whitespace-nowrap flex items-center gap-1.5"
              >
                {connecting && <span className="w-2.5 h-2.5 border border-white/40 border-t-white rounded-full animate-spin" />}
                {connecting ? "Connecting…" : connectError ? "Try again" : "Connect"}
              </button>
            </div>
          </div>
        )}
        {m365Connected === true && (
          <div className="px-4 py-1.5 border-b border-slate-800/60 shrink-0">
            <div className={cn("flex items-center gap-2", col)}>
              <span className="text-[10px] text-green-400 flex-1">✓ Microsoft connected</span>
              <button
                onClick={async () => { try { await authApi.m365Disconnect(); } finally { setM365Connected(false); } }}
                className="text-[10px] text-slate-500 hover:text-slate-300"
              >
                Disconnect
              </button>
            </div>
          </div>
        )}

        {/* Messages */}
        <div className={cn("flex-1 overflow-y-auto", isPage ? "px-4 py-6" : "px-3 py-3")}>
          <div className={cn("space-y-3", isPage && "space-y-4", col)}>
            {messages.map((msg, i) => (
              <div key={i}>
                <div className={bubble(msg.role)}>
                  {msg.role === "assistant" ? (
                    <div className="flex gap-1.5">
                      <span className="text-indigo-400 shrink-0">✦</span>
                      <div className="flex-1 min-w-0">
                        <ChatMarkdown content={msg.content} />
                      </div>
                    </div>
                  ) : (
                    msg.content
                  )}
                </div>

                {msg.checking && (
                  <div className="mt-2 flex items-center gap-2 px-1">
                    <div className="flex gap-0.5">
                      {[0, 1, 2].map((d) => (
                        <div key={d} className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style={{ animationDelay: `${d * 150}ms` }} />
                      ))}
                    </div>
                    <span className="text-[11px] text-indigo-400">Checking for duplicates…</span>
                  </div>
                )}

                {msg.proposedTasks && msg.proposedTasks.length > 0 && !msg.tasksConfirmed && (
                  <ProposedTasksCard
                    tasks={msg.proposedTasks}
                    projectId={msg.proposedProjectId}
                    onConfirm={(count) => {
                      setMessages((prev) =>
                        prev.map((m, idx) => (idx === i ? { ...m, tasksConfirmed: true, confirmedCount: count } : m))
                      );
                      queryClient.invalidateQueries({ queryKey: ["projects"] });
                    }}
                  />
                )}

                {msg.tasksConfirmed && msg.confirmedCount !== undefined && (
                  <div className="mt-2 text-[11px] text-green-400 font-medium px-1">
                    ✓ Created {msg.confirmedCount} task{msg.confirmedCount !== 1 ? "s" : ""}
                  </div>
                )}
              </div>
            ))}

            {/* Quick prompts — only on a fresh chat (no user messages yet). */}
            {!messages.some((m) => m.role === "user") && !loading && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {QUICK_PROMPTS.map((p) => (
                  <button
                    key={p}
                    onClick={() => handleSend(p)}
                    className={cn(
                      "bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 rounded transition-colors",
                      isPage ? "text-xs px-3 py-1.5" : "text-[10px] px-2 py-1"
                    )}
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}

            {loading && (
              <div className={cn("bg-slate-900/60 border border-slate-800 rounded-xl text-slate-500", isPage ? "px-4 py-3 text-sm max-w-[85%]" : "px-3 py-2.5 text-xs max-w-[90%]")}>
                <span className="ai-pulse text-indigo-400">✦</span>{" "}
                Working on it… this can take a minute or two
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        </div>

        {/* Input */}
        <div className={cn("border-t border-slate-800 shrink-0", isPage ? "px-4 py-4" : "px-3 py-3")}>
          <div className={col}>
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 focus-within:border-indigo-500 transition-colors">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder="Ask anything about your projects…"
                className={cn("flex-1 bg-transparent text-white placeholder-slate-600 focus:outline-none", isPage ? "text-sm" : "text-xs")}
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading}
                className="text-indigo-400 disabled:opacity-30 hover:text-indigo-300 transition-colors"
              >
                →
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

// ── Proposed Tasks Card ───────────────────────────────────────────────────────

function ProposedTasksCard({
  tasks,
  projectId,
  onConfirm,
}: {
  tasks: ProposedTask[];
  projectId?: string | null;
  onConfirm: (count: number) => void;
}) {
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set(tasks.map((_, i) => i)));
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleIdx = (i: number) => {
    setSelectedIndices((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const handleCreate = async () => {
    if (selectedIndices.size === 0) return;
    setCreating(true);
    setError(null);
    try {
      const selectedTasks = Array.from(selectedIndices).map((i) => tasks[i]);
      const result = await aiApi.confirmTasks(selectedTasks as unknown as Record<string, unknown>[], projectId || null);
      onConfirm(result.tasks_created);
    } catch {
      setError("Failed to create tasks. Please try again.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="mt-2 bg-slate-900/80 border border-slate-700 rounded-xl overflow-hidden">
      <div className="px-3 py-2 border-b border-slate-800 flex items-center justify-between">
        <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wide">
          {selectedIndices.size}/{tasks.length} selected
        </span>
        <div className="flex gap-2">
          <button onClick={() => setSelectedIndices(new Set(tasks.map((_, i) => i)))} className="text-[10px] text-indigo-400 hover:text-indigo-300">All</button>
          <button onClick={() => setSelectedIndices(new Set())} className="text-[10px] text-slate-500 hover:text-slate-300">None</button>
        </div>
      </div>
      <div className="divide-y divide-slate-800/50 max-h-60 overflow-y-auto">
        {tasks.map((task, i) => {
          const selected = selectedIndices.has(i);
          const priority = (task.priority as PriorityLevel) || "medium";
          const cfg = PRIORITY_CONFIG[priority] ?? PRIORITY_CONFIG.medium;
          return (
            <div
              key={i}
              onClick={() => toggleIdx(i)}
              className={cn("flex items-start gap-2.5 px-3 py-2.5 cursor-pointer transition-colors", selected ? "bg-indigo-950/20" : "hover:bg-slate-800/30")}
            >
              <div className={cn("w-3.5 h-3.5 rounded border-2 shrink-0 mt-0.5 flex items-center justify-center", selected ? "border-indigo-500 bg-indigo-500" : "border-slate-600")}>
                {selected && <span className="text-[7px] text-white font-bold">✓</span>}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-slate-200 leading-snug">{task.title}</p>
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  {task.assignee_name && <span className="text-[10px] text-slate-500">{task.assignee_name}</span>}
                  {task.due_date_offset_days != null && <span className="text-[10px] text-amber-600">+{task.due_date_offset_days}d</span>}
                  <span className={`text-[9px] font-medium ${cfg.color}`}>{cfg.label}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      {error && <p className="px-3 py-1.5 text-[10px] text-red-400">{error}</p>}
      <div className="px-3 py-2 border-t border-slate-800">
        <button
          onClick={handleCreate}
          disabled={selectedIndices.size === 0 || creating}
          className="w-full py-1.5 text-[11px] bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
        >
          {creating ? "Creating…" : `Create ${selectedIndices.size} Task${selectedIndices.size !== 1 ? "s" : ""}`}
        </button>
      </div>
    </div>
  );
}
