"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { aiApi } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { PRIORITY_CONFIG } from "@/lib/types";
import type { EmailResult } from "@/lib/types";

export default function EmailsPage() {
  const [subject, setSubject] = useState("");
  const [sender, setSender] = useState("");
  const [body, setBody] = useState("");
  const [result, setResult] = useState<EmailResult | null>(null);

  const analyzeMutation = useMutation({
    mutationFn: () => aiApi.extractEmail({ subject, sender, body }),
    onSuccess: (data: EmailResult) => setResult(data),
  });

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header title="Email Intelligence" subtitle="Extract tasks, people, and deadlines from emails" />

      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="max-w-3xl mx-auto space-y-5">
          {/* Input */}
          <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-slate-400">✉</span>
              <h2 className="text-sm font-semibold text-white">Paste Email Content</h2>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-slate-500 mb-1.5">Subject</label>
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="Re: API Deployment Timeline"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs text-slate-500 mb-1.5">From</label>
                <input
                  value={sender}
                  onChange={(e) => setSender(e.target.value)}
                  placeholder="manager@company.com"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs text-slate-500 mb-1.5">Email Body</label>
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder={`Paste email body here...\n\nExample:\n"Stephen, can you finish the API deployment by Friday? Tom also wants analytics integrated before the stakeholder review on Monday."`}
                rows={7}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white placeholder-slate-500 resize-none focus:outline-none focus:border-indigo-500 transition-colors leading-relaxed"
              />
            </div>

            <button
              onClick={() => analyzeMutation.mutate()}
              disabled={body.length < 20 || analyzeMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              {analyzeMutation.isPending ? (
                <><span className="ai-pulse">✦</span><span>Analyzing…</span></>
              ) : (
                <><span>✦</span><span>Extract with AI</span></>
              )}
            </button>
          </div>

          {/* Results */}
          {result && (
            <div className="bg-[#0f1629] border border-indigo-800/40 rounded-xl p-6 space-y-5">
              <h2 className="text-sm font-semibold text-white border-b border-slate-800 pb-4">
                Email Analysis Results
              </h2>

              {/* Summary */}
              <div className="bg-indigo-950/30 border border-indigo-900/40 rounded-lg p-3">
                <p className="text-[11px] text-indigo-400 uppercase tracking-wide mb-1">Summary</p>
                <p className="text-sm text-slate-300 leading-relaxed">{result.summary}</p>
              </div>

              {/* Extracted tasks */}
              {result.extracted_tasks?.length > 0 && (
                <div>
                  <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-2">
                    Extracted Tasks ({result.extracted_tasks.length})
                  </p>
                  <div className="space-y-2">
                    {result.extracted_tasks.map((task, i) => (
                      <div key={i} className="bg-slate-900/60 rounded-lg p-3 flex items-start gap-3">
                        <span className="text-indigo-400 mt-0.5 shrink-0">○</span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-slate-200">{task.title}</p>
                          <div className="flex flex-wrap items-center gap-3 mt-1">
                            {task.assignee && (
                              <span className="text-[11px] text-slate-500">→ {task.assignee}</span>
                            )}
                            {task.due_date && (
                              <span className="text-[11px] text-amber-500">Due: {task.due_date}</span>
                            )}
                            {task.context && (
                              <span className="text-[11px] text-slate-600 italic">{task.context}</span>
                            )}
                          </div>
                        </div>
                        <span className={`text-[10px] font-medium shrink-0 ${(PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium).color}`}>
                          {(PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium).label}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* People mentioned */}
              {result.extracted_people?.length > 0 && (
                <div>
                  <p className="text-[11px] text-slate-500 uppercase tracking-wide mb-2">People Mentioned</p>
                  <div className="flex flex-wrap gap-2">
                    {result.extracted_people.map((person, i) => (
                      <span key={i} className="text-xs bg-slate-800 text-slate-300 px-2 py-0.5 rounded-full border border-slate-700">
                        {person}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
