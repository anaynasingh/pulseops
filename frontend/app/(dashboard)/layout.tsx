"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useUIStore, useReminderStore } from "@/lib/store";
import { Sidebar } from "@/components/layout/Sidebar";
import { AIAssistantPanel } from "@/components/ai/AIAssistantPanel";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { ReminderModal } from "@/components/layout/ReminderModal";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, _hasHydrated } = useAuthStore();
  const { aiAssistantOpen, commandPaletteOpen, toggleCommandPalette, theme } = useUIStore();
  const { enabled: reminderEnabled, intervalMin, snoozedUntil, show: showReminder } = useReminderStore();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auth guard — wait for Zustand to rehydrate from localStorage before redirecting.
  // Without this check, on page refresh user is briefly null while the stored token
  // loads, causing a spurious redirect to /login.
  useEffect(() => {
    if (!_hasHydrated) return;   // still loading from localStorage — wait
    if (!user) {
      router.replace("/login");
    }
  }, [user, _hasHydrated, router]);

  // Hourly reminder timer
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (!reminderEnabled) return;
    const ms = intervalMin * 60 * 1000;
    intervalRef.current = setInterval(() => {
      if (snoozedUntil && Date.now() < snoozedUntil) return;
      showReminder();
    }, ms);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [reminderEnabled, intervalMin, snoozedUntil, showReminder]);

  // Global Cmd+K / Ctrl+K shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        toggleCommandPalette();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggleCommandPalette]);

  // Show spinner while Zustand rehydrates — prevents flash redirect
  if (!_hasHydrated) {
    return (
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="flex h-screen overflow-hidden" data-theme={theme}>
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {children}
      </main>

      {aiAssistantOpen && <AIAssistantPanel />}
      {commandPaletteOpen && <CommandPalette />}
      <ReminderModal />
    </div>
  );
}
