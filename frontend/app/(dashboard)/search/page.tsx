"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { searchApi } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import Link from "next/link";

interface KeywordResults {
  projects: Array<{ id: string; title: string; status: string; priority: string; description?: string }>;
  tasks: Array<{ id: string; project_id: string; title: string; status: string }>;
  query: string;
}

interface SemanticResult {
  content_id: string;
  content_type: string;
  similarity: number;
  metadata: Record<string, unknown>;
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"keyword" | "semantic">("keyword");
  const [keywordResults, setKeywordResults] = useState<KeywordResults | null>(null);
  const [semanticResults, setSemanticResults] = useState<SemanticResult[] | null>(null);

  const keywordMutation = useMutation({
    mutationFn: (q: string) => searchApi.keyword(q),
    onSuccess: (data) => setKeywordResults(data),
  });

  const semanticMutation = useMutation({
    mutationFn: (q: string) => searchApi.semantic(q, undefined, 15),
    onSuccess: (data) => setSemanticResults(data),
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setKeywordResults(null);
    setSemanticResults(null);
    if (mode === "keyword") keywordMutation.mutate(query);
    else semanticMutation.mutate(query);
  };

  const isLoading = keywordMutation.isPending || semanticMutation.isPending;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <Header title="Search" subtitle="Find projects, tasks, meetings, and emails" />

      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="max-w-3xl mx-auto space-y-5">
          {/* Search bar */}
          <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
            <div className="flex items-center gap-3 mb-4">
              <div className="flex gap-1 bg-slate-900 rounded-lg p-1">
                {(["keyword", "semantic"] as const).map((m) => (
                  <button
                    key={m}
                    onClick={() => setMode(m)}
                    className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                      mode === m
                        ? "bg-indigo-600 text-white"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {m === "keyword" ? "Keyword" : "✦ Semantic AI"}
                  </button>
                ))}
              </div>
              {mode === "semantic" && (
                <span className="text-[11px] text-indigo-400 bg-indigo-950/40 border border-indigo-900/40 px-2 py-0.5 rounded">
                  pgvector powered
                </span>
              )}
            </div>

            <form onSubmit={handleSearch} className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={
                  mode === "semantic"
                    ? "What projects are blocked because of APIs?"
                    : "Search project title or description…"
                }
                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <button
                type="submit"
                disabled={!query.trim() || isLoading}
                className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors whitespace-nowrap"
              >
                {isLoading ? "Searching…" : "Search"}
              </button>
            </form>

            {mode === "semantic" && (
              <p className="text-[11px] text-slate-600 mt-2">
                Try: "blocked API projects", "AI accounting tasks", "meetings with action items"
              </p>
            )}
          </div>

          {/* Keyword results */}
          {keywordResults && (
            <div className="space-y-4">
              {/* Projects */}
              {keywordResults.projects.length > 0 && (
                <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                    Projects ({keywordResults.projects.length})
                  </h3>
                  <div className="space-y-2">
                    {keywordResults.projects.map((p) => (
                      <Link
                        key={p.id}
                        href={`/projects/${p.id}`}
                        className="block bg-slate-900/60 hover:bg-slate-800/60 rounded-lg p-3 transition-colors"
                      >
                        <p className="text-sm text-slate-200 font-medium">{p.title}</p>
                        {p.description && (
                          <p className="text-xs text-slate-500 mt-0.5 line-clamp-1">{p.description}</p>
                        )}
                        <div className="flex gap-2 mt-1">
                          <span className="text-[10px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">
                            {p.status.replace("_", " ")}
                          </span>
                          <span className="text-[10px] text-slate-600 bg-slate-800 px-1.5 py-0.5 rounded">
                            {p.priority}
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Tasks */}
              {keywordResults.tasks.length > 0 && (
                <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                    Tasks ({keywordResults.tasks.length})
                  </h3>
                  <div className="space-y-2">
                    {keywordResults.tasks.map((t) => (
                      <Link
                        key={t.id}
                        href={`/projects/${t.project_id}`}
                        className="block bg-slate-900/60 hover:bg-slate-800/60 rounded-lg p-3 transition-colors"
                      >
                        <p className="text-sm text-slate-200">{t.title}</p>
                        <span className="text-[10px] text-slate-600">{t.status.replace("_", " ")}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {keywordResults.projects.length === 0 && keywordResults.tasks.length === 0 && (
                <p className="text-center text-slate-500 py-8">No results for "{keywordResults.query}"</p>
              )}
            </div>
          )}

          {/* Semantic results */}
          {semanticResults && (
            <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 flex items-center gap-2">
                <span className="text-indigo-400 ai-pulse">✦</span>
                Semantic Results ({semanticResults.length})
              </h3>
              {semanticResults.length === 0 ? (
                <p className="text-slate-500 text-sm text-center py-6">No semantically similar content found</p>
              ) : (
                <div className="space-y-2">
                  {semanticResults.map((r, i) => (
                    <div key={i} className="bg-slate-900/60 rounded-lg p-3 flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-[10px] text-indigo-400 bg-indigo-950/40 border border-indigo-900/40 px-1.5 py-0.5 rounded uppercase">
                            {r.content_type}
                          </span>
                          <span className="text-[11px] text-slate-500 truncate">
                            {String(r.metadata?.title ?? r.content_id).slice(0, 50)}
                          </span>
                        </div>
                      </div>
                      <div className="shrink-0 text-right">
                        <div className="flex items-center gap-1.5">
                          <div className="w-16 bg-slate-700 rounded-full h-1">
                            <div className="bg-indigo-500 h-1 rounded-full" style={{ width: `${r.similarity * 100}%` }} />
                          </div>
                          <span className="text-[11px] text-slate-500">{Math.round(r.similarity * 100)}%</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
