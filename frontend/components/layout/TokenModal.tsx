"use client";

import { useState, useEffect, useSyncExternalStore } from "react";
import { createPortal } from "react-dom";
import { authApi } from "@/lib/api";

interface TokenModalProps {
  onClose: () => void;
}

// Stable references for useSyncExternalStore (client-only detection, hydration-safe).
const emptySubscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

export function TokenModal({ onClose }: TokenModalProps) {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    authApi.getApiKey()
      .then(setApiKey)
      .catch(() => setApiKey(null))
      .finally(() => setLoading(false));
  }, []);

  const copyToken = () => {
    if (!apiKey) return;
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isClient = useSyncExternalStore(emptySubscribe, getClientSnapshot, getServerSnapshot);
  if (!isClient) return null;

  return createPortal(
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md flex flex-col">
        {/* Header */}
        <div className="p-6 pb-4 border-b border-slate-100 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold text-slate-900">🔑 Your Task Planner token</h2>
            <p className="text-sm text-slate-500 mt-1">This key tells Claude which tasks are yours. Keep it private.</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors text-xl leading-none ml-4 mt-0.5" title="Close">✕</button>
        </div>

        {/* Token */}
        <div className="p-6 space-y-2">
          <div className="relative">
            <div className="bg-slate-900 rounded-lg p-3 pr-16 font-mono text-xs text-green-400 break-all select-all">
              {loading ? "loading…" : (apiKey ?? "unavailable — reload the page")}
            </div>
            <button
              onClick={copyToken}
              disabled={!apiKey}
              className="absolute top-2 right-2 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-40 text-slate-200 px-2 py-1 rounded transition-colors"
            >
              {copied ? "✓ Copied" : loading ? "…" : "Copy"}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
