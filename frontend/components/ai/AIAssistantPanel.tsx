"use client";

import { useState, useRef, useEffect } from "react";
import { useUIStore } from "@/lib/store";
import { aiApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useQueryClient } from "@tanstack/react-query";
import { PRIORITY_CONFIG } from "@/lib/types";
import type { PriorityLevel } from "@/lib/types";

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
  // for propose_tasks action
  proposedTasks?: ProposedTask[];
  proposedProjectId?: string | null;
  tasksConfirmed?: boolean;
  confirmedCount?: number;
}

const QUICK_PROMPTS = [
  "What projects are blocked?",
  "Summarize today's activity",
  "What should I prioritize?",
  "Show overdue projects",
];

export function AIAssistantPanel() {
  const { toggleAIAssistant } = useUIStore();
  const queryClient = useQueryClient();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm PulseOps AI. I can help you understand your projects, find blockers, generate summaries, and suggest priorities. What would you like to know?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (text: string = input) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await aiApi.chat(text);

      if (res.action === "propose_tasks" && res.proposed_tasks?.length > 0) {
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            content: res.reply,
            proposedTasks: res.proposed_tasks,
            proposedProjectId: res.project_id || null,
            tasksConfirmed: false,
          },
        ]);
      } else {
        const answer = res.reply || "I analyzed your workspace but couldn't generate a response.";
        setMessages((m) => [...m, { role: "assistant", content: answer }]);
        // If AI created something, refresh the board/projects data
        if (res.action === "created_project" || res.action === "created_task") {
          queryClient.invalidateQueries({ queryKey: ["projects"] });
        }
      }
    } catch {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "I'm having trouble connecting to the AI service. Please check your API configuration." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed right-0 top-0 bottom-0 w-80 bg-[#080f20] border-l border-slate-800 flex flex-col z-20 shadow-2xl">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3.5 border-b border-slate-800">
        <span className="text-indigo-400 ai-pulse">âœ¦</span>
        <span className="text-sm font-semibold text-white flex-1">AI Assistant</span>
        <span className="text-[10px] text-green-400 bg-green-900/30 border border-green-800/40 px-1.5 py-0.5 rounded">
          GPT-4o
        </span>
        <button onClick={toggleAIAssistant} className="text-slate-500 hover:text-white transition-colors ml-1">
          Ã—
        </button>
      </div>

      {/* Quick prompts */}
      <div className="px-3 py-2 border-b border-slate-800/60 flex flex-wrap gap-1.5">
        {QUICK_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => handleSend(p)}
            disabled={loading}
            className="text-[10px] bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 px-2 py-1 rounded transition-colors"
          >
            {p}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {messages.map((msg, i) => (
          <div key={i}>
            <div
              className={cn(
                "rounded-xl px-3 py-2.5 text-xs leading-relaxed max-w-[90%]",
                msg.role === "user"
                  ? "bg-indigo-600/20 border border-indigo-600/30 text-slate-200 ml-auto"
                  : "bg-slate-900/60 border border-slate-800 text-slate-300"
              )}
            >
              {msg.role === "assistant" && (
                <span className="text-indigo-400 mr-1">âœ¦</span>
              )}
              {msg.content}
            </div>

            {/* Task proposal UI */}
            {msg.proposedTasks && msg.proposedTasks.length > 0 && !msg.tasksConfirmed && (
              <ProposedTasksCard
                tasks={msg.proposedTasks}
                projectId={msg.proposedProjectId}
                onConfirm={(count) => {
                  setMessages((prev) =>
                    prev.map((m, idx) =>
                      idx === i ? { ...m, tasksConfirmed: true, confirmedCount: count } : m
                    )
                  );
                  queryClient.invalidateQueries({ queryKey: ["projects"] });
                }}
              />
            )}

            {/* Success state after confirmation */}
            {msg.tasksConfirmed && msg.confirmedCount !== undefined && (
              <div className="mt-2 text-[11px] text-green-400 font-medium px-1">
                âœ“ Created {msg.confirmedCount} task{msg.confirmedCount !== 1 ? "s" : ""}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-500 max-w-[90%]">
            <span className="ai-pulse text-indigo-400">âœ¦</span>{" "}
            Thinkingâ€¦
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-3 py-3 border-t border-slate-800">
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 focus-within:border-indigo-500 transition-colors">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder="Ask anything about your projectsâ€¦"
            className="flex-1 bg-transparent text-xs text-white placeholder-slate-600 focus:outline-none"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || loading}
            className="text-indigo-400 disabled:opacity-30 hover:text-indigo-300 transition-colors"
          >
            â†’
          </button>
        </div>
      </div>
    </div>
  );
}

// â”€â”€ Proposed Tasks Card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

function ProposedTasksCard({
  tasks,
  projectId,
  onConfirm,
}: {
  tasks: ProposedTask[];
  projectId?: string | null;
  onConfirm: (count: number) => void;
}) {
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
    new Set(tasks.map((_, i) => i))
  );
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
      const result = await aiApi.confirmTasks(
        selectedTasks as unknown as Record<string, unknown>[],
        projectId || null
      );
      onConfirm(result.tasks_created);
    } catch (e) {
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
          <button
            onClick={() => setSelectedIndices(new Set(tasks.map((_, i) => i)))}
            className="text-[10px] text-indigo-400 hover:text-indigo-300"
          >
            All
          </button>
          <button
            onClick={() => setSelectedIndices(new Set())}
            className="text-[10px] text-slate-500 hover:text-slate-300"
          >
            None
          </button>
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
              className={cn(
                "flex items-start gap-2.5 px-3 py-2.5 cursor-pointer transition-colors",
                selected ? "bg-indigo-950/20" : "hover:bg-slate-800/30"
              )}
            >
              <div
                className={cn(
                  "w-3.5 h-3.5 rounded border-2 shrink-0 mt-0.5 flex items-center justify-center",
                  selected ? "border-indigo-500 bg-indigo-500" : "border-slate-600"
                )}
              >
                {selected && <span className="text-[7px] text-white font-bold">âœ“</span>}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] text-slate-200 leading-snug">{task.title}</p>
                <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                  {task.assignee_name && (
                    <span className="text-[10px] text-slate-500">{task.assignee_name}</span>
                  )}
                  {task.due_date_offset_days != null && (
                    <span className="text-[10px] text-amber-600">
                      +{task.due_date_offset_days}d
                    </span>
                  )}
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
          {creating ? "Creatingâ€¦" : `Create ${selectedIndices.size} Task${selectedIndices.size !== 1 ? "s" : ""}`}
        </button>
      </div>
    </div>
  );
}

