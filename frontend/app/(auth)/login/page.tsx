"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";

const ERROR_MESSAGES: Record<string, string> = {
  invalid_state: "Sign-in session expired. Please try again.",
  token_exchange_failed: "Could not complete sign-in. Please try again.",
  graph_fetch_failed: "Could not retrieve your Microsoft profile. Please try again.",
  missing_user_claims: "Your Microsoft account is missing required information.",
  account_disabled: "Your account has been disabled. Contact your administrator.",
  auth_failed: "Sign-in failed. Please try again.",
};

export default function LoginPage() {
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const errorKey = searchParams.get("error") ?? "";
  const errorMessage = ERROR_MESSAGES[errorKey] ?? (errorKey ? "Sign-in failed. Please try again." : "");

  const handleMicrosoftLogin = () => {
    setLoading(true);
    authApi.microsoftLogin();
  };

  return (
    <div className="min-h-screen bg-[#020817] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <span className="text-white font-bold text-sm">P</span>
            </div>
            <span className="text-2xl font-bold text-white">PulseOps</span>
          </div>
          <p className="text-slate-400 text-sm">AI-Powered Team Operations</p>
        </div>

        {/* Card */}
        <div className="bg-[#0f1629] border border-slate-800 rounded-2xl p-8">
          <h1 className="text-xl font-semibold text-white mb-6">Sign in to PulseOps</h1>

          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-red-900/30 border border-red-800 text-red-400 text-sm">
              {errorMessage}
            </div>
          )}

          <button
            onClick={handleMicrosoftLogin}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 bg-white hover:bg-slate-100 disabled:opacity-50 text-slate-900 font-medium py-2.5 rounded-lg transition-colors text-sm"
          >
            <MicrosoftIcon />
            {loading ? "Redirecting…" : "Sign in with Microsoft"}
          </button>

          <p className="mt-6 text-center text-xs text-slate-600">
            Access is managed by your organisation&apos;s Microsoft account.
          </p>
        </div>
      </div>
    </div>
  );
}

function MicrosoftIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
    </svg>
  );
}
