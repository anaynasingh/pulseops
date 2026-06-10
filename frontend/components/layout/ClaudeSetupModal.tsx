"use client";

import { useState } from "react";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

interface ClaudeSetupModalProps {
  userName: string;
  onDone: () => void;   // completed — saves to backend
  onSkip: () => void;   // skip for this session only
}

const STEPS = [
  {
    id: 1,
    title: "Install Claude Code",
    icon: "⬇",
    desc: "Claude Code is the CLI that connects Claude to your apps and data.",
    content: (
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
    ),
  },
  {
    id: 2,
    title: "Connect Microsoft 365",
    icon: "🔗",
    desc: "Lets Claude read your Teams meetings, calendar and emails automatically.",
    content: (
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
          Once connected, Claude automatically reads dev meeting transcripts and pulls action items — no copy-pasting.
        </div>
      </div>
    ),
  },
  {
    id: 3,
    title: "Connect Task Planner MCP",
    icon: "⚡",
    desc: "Lets Claude create, update and read tasks directly in this app — runs locally on your machine.",
    content: (
      <div className="space-y-3">
        <p className="text-sm text-slate-600 font-medium">The MCP server is a small Python script that runs on your machine. 4 steps:</p>
        <ol className="space-y-3 text-sm text-slate-700">
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">1</span>
            <div>
              <p>Clone the repo (if not already done):</p>
              <div className="bg-slate-900 rounded p-2 font-mono text-xs text-green-400 mt-1 select-all">
                git clone https://github.com/P33-AI/ai-task-management-and-workflow-intelligence-system.git
              </div>
            </div>
          </li>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">2</span>
            <div>
              <p>Install the dependencies:</p>
              <div className="bg-slate-900 rounded p-2 font-mono text-xs text-green-400 mt-1 select-all">
                cd mcp-servers/pulseops{"\n"}
                pip install mcp httpx python-dotenv
              </div>
            </div>
          </li>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">3</span>
            <div>
              <p>Create a <code className="bg-slate-100 px-1 rounded text-xs">.env</code> file in the <code className="bg-slate-100 px-1 rounded text-xs">mcp-servers/pulseops</code> folder:</p>
              <div className="bg-slate-900 rounded p-2 font-mono text-xs text-green-400 mt-1 select-all leading-relaxed">
                PULSEOPS_API_URL=https://backend-production-ff8e.up.railway.app/api/v1{"\n"}
                PULSEOPS_EMAIL=your@prospect33.com{"\n"}
                PULSEOPS_PASSWORD=YourPassword
              </div>
            </div>
          </li>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">4</span>
            <div>
              <p>Register it with Claude Code (use the <strong>full path</strong> to server.py):</p>
              <div className="bg-slate-900 rounded p-2 font-mono text-xs text-green-400 mt-1 select-all">
                claude mcp add task-planner python C:\path\to\mcp-servers\pulseops\server.py
              </div>
              <p className="text-xs text-slate-500 mt-1">Then restart Claude Code — you&apos;ll see <strong>task-planner</strong> in your tools.</p>
            </div>
          </li>
        </ol>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
          <strong>Need the full path?</strong> In the mcp-servers/pulseops folder, run <code className="bg-amber-100 px-1 rounded">cd</code> (Windows) or <code className="bg-amber-100 px-1 rounded">pwd</code> (Mac/Linux) to get it.
        </div>
      </div>
    ),
  },
  {
    id: 4,
    title: "You're all set!",
    icon: "🎉",
    desc: "Claude is connected. Here's what you can now do.",
    content: (
      <div className="space-y-3">
        <p className="text-sm text-slate-600 font-medium">Try saying these to Claude Code:</p>
        <div className="space-y-2">
          {[
            "Summarise today's dev meeting and add action items to my task planner",
            "What are my overdue tasks in the task planner?",
            "Add a high priority task: Fix the CORS bug in Task Planner",
            "Mark the 'Fix session persistence' task as complete",
            "Which Forage tasks are due this week?",
          ].map((ex, i) => (
            <div key={i} className="flex gap-2 items-start bg-indigo-50 border border-indigo-100 rounded-lg p-2.5">
              <span className="text-indigo-500 text-xs mt-0.5">✦</span>
              <p className="text-xs text-indigo-800 italic">&ldquo;{ex}&rdquo;</p>
            </div>
          ))}
        </div>
        <p className="text-xs text-slate-400 text-center pt-1">
          Click <strong>Done</strong> to mark your Claude as connected — the status indicator in the sidebar will turn green.
        </p>
      </div>
    ),
  },
];

export function ClaudeSetupModal({ userName, onDone, onSkip }: ClaudeSetupModalProps) {
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const { setAuth, user, token } = useAuthStore();
  const firstName = userName.split(" ")[0];
  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  const handleDone = async () => {
    setSaving(true);
    try {
      const updated = await authApi.mcpComplete();
      if (user && token) setAuth({ ...user, mcp_setup_done: true }, token);
    } catch (_) { /* ignore */ }
    setSaving(false);
    onDone();
  };

  return (
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
                  : `Step ${step + 1} of ${STEPS.length} — ${current.desc}`}
              </p>
            </div>
            <button onClick={onSkip} className="text-slate-400 hover:text-slate-600 transition-colors text-xl leading-none ml-4 mt-0.5" title="Skip for now">✕</button>
          </div>
          {/* Progress */}
          <div className="mt-4 flex gap-1.5">
            {STEPS.map((s, i) => (
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
          {current.content}
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
    </div>
  );
}
