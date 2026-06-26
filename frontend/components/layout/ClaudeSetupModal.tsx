"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

interface ClaudeSetupModalProps {
  userName: string;
  onDone: () => void;   // completed — saves to backend
  onSkip: () => void;   // skip for this session only
}

const BACKEND = "https://backend-production-ff8e.up.railway.app";

const STEP_DEFS = [
  {
    id: 1,
    title: "Install Claude Code",
    icon: "⬇",
    desc: "Claude Code is the CLI that connects Claude to your apps and data.",
  },
  {
    id: 2,
    title: "Connect Microsoft 365",
    icon: "🔗",
    desc: "Lets Claude read your Teams meetings, calendar and emails automatically.",
  },
  {
    id: 3,
    title: "Connect Task Planner MCP",
    icon: "⚡",
    desc: "One command — lets Claude read and update tasks directly in this app.",
  },
  {
    id: 4,
    title: "You're all set!",
    icon: "🎉",
    desc: "Claude is connected. Here's what you can now do.",
  },
];

function Step1Content() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">Open a terminal (PowerShell on Windows) and run:</p>
      <div className="bg-slate-900 rounded-lg p-3 font-mono text-sm text-green-400 select-all">
        npm install -g @anthropic-ai/claude-code
      </div>
      <p className="text-sm text-slate-600">Verify it installed:</p>
      <div className="bg-slate-900 rounded-lg p-3 font-mono text-sm text-green-400 select-all">
        claude --version
      </div>
      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
        <strong>Windows:</strong> Requires Node.js 18+. Download from{" "}
        <a href="https://nodejs.org" target="_blank" rel="noreferrer" className="underline">nodejs.org</a>
      </div>
    </div>
  );
}

function Step2Content() {
  return (
    <div className="space-y-3">
      <ol className="space-y-3 text-sm text-slate-700">
        {[
          <>Open Claude Code in your terminal: type <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">claude</code></>,
          <>In Claude Code, open the <strong>Connectors</strong> panel (plug icon in the sidebar)</>,
          <>Find <strong>Microsoft 365</strong> and click <strong>Connect</strong></>,
          <>Sign in with your <strong>@prospect33.com</strong> Microsoft account</>,
          <>Grant permissions for <strong>Calendar, Teams</strong> and <strong>Email</strong></>,
        ].map((step, i) => (
          <li key={i} className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">{i + 1}</span>
            <span>{step}</span>
          </li>
        ))}
      </ol>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
        Once connected, Claude automatically reads meeting transcripts and pulls action items — no copy-pasting.
      </div>
    </div>
  );
}

function Step3Content({ token: _jwt }: { token: string | null }) {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    authApi.getApiKey()
      .then(setApiKey)
      .catch(() => setApiKey(null))
      .finally(() => setLoading(false));
  }, []);

  const displayToken = apiKey ?? (loading ? "loading…" : "<your-token>");
  const command = `claude mcp add task-planner \\\n  --transport sse \\\n  ${BACKEND}/mcp/sse \\\n  --header "X-Token: ${displayToken}"`;

  const handleCopy = () => {
    if (!apiKey) return;
    navigator.clipboard.writeText(command.replace(/\\\n  /g, " \\\n  "));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-3">
      <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-sm text-green-800 font-medium">
        ✨ No cloning, no Python setup — just one command.
      </div>
      <p className="text-sm text-slate-600">Run this in your terminal — your token is pre-filled:</p>
      <div className="relative">
        <div className="bg-slate-900 rounded-lg p-3 font-mono text-xs text-green-400 leading-relaxed whitespace-pre select-all overflow-x-auto">
          {command}
        </div>
        <button
          onClick={handleCopy}
          disabled={!apiKey}
          className="absolute top-2 right-2 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-slate-200 px-2 py-1 rounded transition-colors"
        >
          {copied ? "✓ Copied" : loading ? "…" : "Copy"}
        </button>
      </div>
      <p className="text-sm text-slate-600">Restart Claude Code — you&apos;ll see <strong>task-planner</strong> in your MCP tools.</p>
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
        <strong>Why a token?</strong> So Claude only sees YOUR tasks. The MCP server is hosted — nothing runs on your machine.
      </div>
      <div className="space-y-1.5 pt-1">
        <p className="text-xs font-medium text-slate-600">Verify it works — say this to Claude:</p>
        <div className="bg-slate-50 border-l-2 border-indigo-400 pl-3 pr-2 py-2 rounded-r-lg text-sm text-slate-700 italic">
          &ldquo;List my tasks in the task planner&rdquo;
        </div>
      </div>
    </div>
  );
}

function Step4Content() {
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600 font-medium">Try saying these to Claude Code:</p>
      <div className="space-y-2">
        {[
          "Summarise today's meeting, add action items to my task planner, then log whether you got the right transcript",
          "What are my overdue tasks in the task planner?",
          "Add a high priority task: Fix the CORS bug in Task Planner",
          "Mark the 'Fix session persistence' task as complete",
          "Which Forage tasks are due this week?",
        ].map((ex, i) => (
          <div key={i} className="flex gap-2 items-start bg-slate-50 border-l-2 border-indigo-400 pl-3 pr-2 py-2 rounded-r-lg">
            <p className="text-sm text-slate-700 italic">&ldquo;{ex}&rdquo;</p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-400 text-center pt-1">
        Click <strong>Done</strong> to mark your Claude as connected — the status indicator in the sidebar will turn green.
      </p>
    </div>
  );
}

export function ClaudeSetupModal({ userName, onDone, onSkip }: ClaudeSetupModalProps) {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const { setAuth, user, token } = useAuthStore();
  const firstName = userName.split(" ")[0];
  const current = STEP_DEFS[step];
  const isLast = step === STEP_DEFS.length - 1;

  const handleDone = async () => {
    setSaving(true);
    try {
      await authApi.mcpComplete();
      if (user && token) setAuth({ ...user, mcp_setup_done: true }, token);
    } catch (_) { /* ignore */ }
    setSaving(false);
    onDone();
  };

  const renderContent = () => {
    switch (step) {
      case 0: return <Step1Content />;
      case 1: return <Step2Content />;
      case 2: return <Step3Content token={token} />;
      case 3: return <Step4Content />;
      default: return null;
    }
  };

  // Client-only: `document` is unavailable during SSR. Both call sites render
  // this modal post-hydration (sidebar click; layout gated on _hasHydrated),
  // so this never produces a hydration mismatch.
  if (typeof document === "undefined") return null;

  // Render into document.body so the overlay escapes the sidebar wrapper's
  // CSS transform (layout.tsx), which would otherwise make `fixed` resolve
  // against the 256px sidebar box and clamp the modal to the left pane.
  return createPortal(
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="p-6 pb-4 border-b border-slate-100">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                {step === 0 ? `Connect Claude, ${firstName} 🔌` : "Connect Claude to Task Planner"}
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                {step === 0
                  ? "4 quick steps to auto-pull meetings and manage tasks with Claude."
                  : `Step ${step + 1} of ${STEP_DEFS.length} — ${current.desc}`}
              </p>
            </div>
            <button onClick={onSkip} className="text-slate-400 hover:text-slate-600 transition-colors text-xl leading-none ml-4 mt-0.5" title="Skip for now">✕</button>
          </div>
          {/* Progress */}
          <div className="mt-4 flex gap-1.5">
            {STEP_DEFS.map((s, i) => (
              <div key={s.id} className={`h-1.5 flex-1 rounded-full transition-all ${i < step ? "bg-indigo-600" : i === step ? "bg-indigo-400" : "bg-slate-200"}`} />
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">{current.icon}</span>
            <h3 className="text-base font-semibold text-slate-900">{current.title}</h3>
          </div>
          {renderContent()}
        </div>

        {/* Footer */}
        <div className="p-6 pt-4 border-t border-slate-100 flex items-center justify-between">
          <button onClick={onSkip} className="text-sm text-slate-400 hover:text-slate-600 transition-colors">
            Skip for now
          </button>
          <div className="flex gap-2">
            {step > 0 && (
              <button onClick={() => setStep(s => s - 1)} className="px-4 py-2 text-sm border border-slate-300 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors">
                Back
              </button>
            )}
            <button
              onClick={isLast ? handleDone : () => setStep(s => s + 1)}
              disabled={saving}
              className="px-5 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium disabled:opacity-60"
            >
              {saving ? "Saving…" : isLast ? "✓ Done — I'm connected!" : step === 0 ? "Let's set it up →" : "Next →"}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
