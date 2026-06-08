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
  const { user } = useAuthStore();
  const { aiAssistantOpen, commandPaletteOpen, toggleCommandPalette } = useUIStore();
  const { enabled: reminderEnabled, intervalMin, snoozedUntil, show: showReminder } = useReminderStore();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auth guard
  useEffect(() => {
    if (!user) {
      router.replace("/login");
    }
  }, [user, router]);

  // Hourly reminder timer
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (!reminderEnabled) return;

    const ms = intervalMin * 60 * 1000;
    intervalRef.current = setInterval(() => {
      // Skip if currently snoozed
      if (snoozedUntil && Date.now() < snoozedUntil) return;
      showReminder();
    }, ms);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [reminderEnabled, intervalMin, snoozedUntil, showReminder]);

  // Global Cmd+K / Ctrl+K shortcut — registered here so it works even when palette is closed
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

  if (!user) return null;

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {children}
      </main>

      {/* AI Assistant Panel */}
      {aiAssistantOpen && <AIAssistantPanel />}

      {/* Command Palette */}
      {commandPaletteOpen && <CommandPalette />}

      {/* Hourly reminder modal */}
      <ReminderModal />
    </div>
  );
}
