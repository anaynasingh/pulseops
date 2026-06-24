"use client";

import { Suspense } from "react";
import { useEffect, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setAuth = useAuthStore((s) => s.setAuth);
  const called = useRef(false);

  useEffect(() => {
    if (called.current) return;
    called.current = true;

    const code = searchParams.get("code");
    if (!code) {
      router.replace("/login?error=auth_failed");
      return;
    }

    authApi
      .exchangeCode(code)
      .then((res) => {
        setAuth(res.user, res.access_token);
        router.replace("/dashboard");
      })
      .catch(() => {
        router.replace("/login?error=auth_failed");
      });
  }, [searchParams, setAuth, router]);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      <p className="text-slate-400 text-sm">Completing sign-in…</p>
    </div>
  );
}

export default function CallbackPage() {
  return (
    <div className="min-h-screen bg-[#020817] flex items-center justify-center">
      <Suspense fallback={null}>
        <CallbackContent />
      </Suspense>
    </div>
  );
}
