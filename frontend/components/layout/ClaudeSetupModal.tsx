"use client";

import { useState } from "react";

interface ClaudeSetupModalProps {
  userName: string;
  onDismiss: () => void;
}

const STEPS = [
  {
    id: 1,
    title: "Install Claude Code",
    icon: "⬇",
    desc: "Claude Code is the CLI tool that connects Claude to your apps and data.",
    content: (
      <div className="space-y-3">
        <p className="text-sm text-slate-600">Open a terminal (PowerShell on Windows, Terminal on Mac) and run:</p>
        <div className="bg-slate-900 rounded-lg p-3 font-mono text-sm text-green-400 select-all">
          npm install -g @anthropic-ai/claude-code
        </div>
        <p className="text-sm text-slate-600">Then verify it installed:</p>
        <div className="bg-slate-900 rounded-lg p-3 font-mono text-sm text-green-400 select-all">
          claude --version
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
          <strong>Windows users:</strong> You need Node.js 18+ installed first.
          Download from <a href="https://nodejs.org" target="_blank" rel="noreferrer" className="underline">nodejs.org</a>
        </div>
      </div>
    ),
  },
  {
    id: 2,
    title: "Connect Microsoft 365",
    icon: "🔗",
    desc: "This lets Claude read your Teams meetings, calendar, and emails to auto-create tasks.",
    content: (
      <div className="space-y-3">
        <ol className="space-y-3 text-sm text-slate-700">
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">1</span>
            <span>Open <strong>Claude Code</strong> in your terminal by typing <code className="bg-slate-100 px-1 rounded">claude</code></span>
          </li>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">2</span>
            <span>In Claude Code, open the <strong>Connectors</strong> panel (look for the plug icon or type <code className="bg-slate-100 px-1 rounded">/connectors</code>)</span>
          </li>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">3</span>
            <span>Find <strong>Microsoft 365</strong> in the list and click <strong>Connect</strong></span>
          </li>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">4</span>
            <span>Sign in with your <strong>@prospect33.com</strong> Microsoft account</span>
          </li>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">5</span>
            <span>Grant permissions for Calendar, Teams, and Email access</span>
          </li>
        </ol>
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
          Once connected, Claude can automatically read your dev meeting transcripts and extract tasks — no copy-pasting needed.
        </div>
      </div>
    ),
  },
  {
    id: 3,
    title: "Connect Task Planner MCP",
    icon: "⚡",
    desc: "This lets Claude directly create tasks in this app from your meetings and chats.",
    content: (
      <div className="space-y-3">
        <p className="text-sm text-slate-600">Add the Task Planner MCP server to Claude Code:</p>
        <ol className="space-y-3 text-sm text-slate-700">
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">1</span>
            <span>In Claude Code, run:</span>
          </li>
        </ol>
        <div className="bg-slate-900 rounded-lg p-3 font-mono text-xs text-green-400 select-all leading-relaxed">
          claude mcp add task-planner --url https://backend-production-ff8e.up.railway.app/mcp
        </div>
        <ol className="space-y-3 text-sm text-slate-700" start={2}>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">2</span>
            <span>When prompted for your API token, use your Task Planner email and password to get one from:</span>
          </li>
        </ol>
        <div className="bg-slate-900 rounded-lg p-3 font-mono text-xs text-green-400 select-all">
          https://backend-production-ff8e.up.railway.app/api/v1/auth/login
        </div>
        <ol className="space-y-3 text-sm text-slate-700" start={3}>
          <li className="flex gap-3">
            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">3</span>
            <span>Restart Claude Code. You'll see <strong>"task-planner"</strong> in your MCP tools list.</span>
          </li>
        </ol>
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-xs text-green-800">
          Now you can say to Claude: <em>"Summarise today's dev meeting and add the action items to the task planner"</em> — Claude will do it automatically.
        </div>
      </div>
    ),
  },
  {
    id: 4,
    title: "You're all set!",
    icon: "🎉",
    desc: "Here's what you can now ask Claude to do.",
    content: (
      <div className="space-y-3">
        <p className="text-sm text-slate-600 font-medium">Try saying these to Claude Code:</p>
        <div className="space-y-2">
          {[
            "Summarise today's dev meeting and add the action items to my task planner",
            "What are my overdue tasks in the task planner?",
            "Add a high priority task: Fix the CORS bug in Task Planner",
            "Pull the transcript from this morning's meeting and create tasks for each action item",
            "Mark the 'Fix session persistence' task as complete",
          ].map((ex, i) => (
            <div key={i} className="flex gap-2 items-start bg-indigo-50 border border-indigo-100 rounded-lg p-2.5">
              <span className="text-indigo-500 text-xs mt-0.5">✦</span>
              <p className="text-xs text-indigo-800 italic">&ldquo;{ex}&rdquo;</p>
            </div>
          ))}
        </div>
      </div>
    ),
  },
];

export function ClaudeSetupModal({ userName, onDismiss }: ClaudeSetupModalProps) {
  const [step, setStep] = useState(0);
  const firstName = userName.split(" ")[0];
  const current = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">

        {/* Header */}
        <div className="p-6 pb-4 border-b border-slate-100">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                {step === 0 ? `Welcome, ${firstName}! 👋` : "Connect Claude to Task Planner"}
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                {step === 0
                  ? "Set up Claude to auto-pull meetings and add tasks for you."
                  : `Step ${step + 1} of ${STEPS.length} — ${current.desc}`}
              </p>
            </div>
            <button onClick={onDismiss} className="text-slate-400 hover:text-slate-600 transition-colors text-lg leading-none ml-4 mt-0.5">✕</button>
          </div>

          {/* Progress bar */}
          <div className="mt-4 flex gap-1.5">
            {STEPS.map((s, i) => (
              <div key={s.id} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? "bg-indigo-600" : "bg-slate-200"}`} />
            ))}
          </div>
        </div>

        {/* Step content */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">{current.icon}</span>
            <h3 className="text-base font-semibold text-slate-900">{current.title}</h3>
          </div>
          {current.content}
        </div>

        {/* Footer */}
        <div className="p-6 pt-4 border-t border-slate-100 flex items-center justify-between">
          <button
            onClick={onDismiss}
            className="text-sm text-slate-400 hover:text-slate-600 transition-colors"
          >
            {isLast ? "Close" : "Skip for now"}
          </button>
          <div className="flex gap-2">
            {step > 0 && (
              <button
                onClick={() => setStep(s => s - 1)}
                className="px-4 py-2 text-sm border border-slate-300 text-slate-600 rounded-lg hover:bg-slate-50 transition-colors"
              >
                Back
              </button>
            )}
            <button
              onClick={() => isLast ? onDismiss() : setStep(s => s + 1)}
              className="px-5 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
            >
              {isLast ? "Done" : step === 0 ? "Let's set it up →" : "Next →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
