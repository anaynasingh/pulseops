"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useUIStore, useReminderStore } from "@/lib/store";
import { Sidebar } from "@/components/layout/Sidebar";
import { AIAssistantPanel } from "@/components/ai/AIAssistantPanel";
import { CommandPalette } from "@/components/layout/CommandPalette";
import { ReminderModal } from "@/components/layout/ReminderModal";
import { ClaudeSetupModal } from "@/components/layout/ClaudeSetupModal";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, _hasHydrated } = useAuthStore();
  const { aiAssistantOpen, commandPaletteOpen, toggleCommandPalette, theme, sidebarOpen, setSidebarOpen, claudeSetupSeen, setClaudeSetupSeen } = useUIStore();
  const { enabled: reminderEnabled, intervalMin, snoozedUntil, show: showReminder } = useReminderStore();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auth guard — wait for Zustand to rehydrate from localStorage before redirecting.
  useEffect(() => {
    if (!_hasHydrated) return;
    if (!user) router.replace("/login");
  }, [user, _hasHydrated, router]);

  // On small screens, default sidebar to closed
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 768) setSidebarOpen(false);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [setSidebarOpen]);

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

  // Global Cmd+K / Ctrl+K
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

  // Loading spinner while Zustand rehydrates
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

  const isMobileOpen = sidebarOpen;

  return (
    <div className="flex h-screen overflow-hidden" data-theme={theme}>

      {/* Mobile backdrop — tap to close sidebar */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — off-canvas on mobile, fixed on desktop */}
      <div className={`
        fixed md:relative inset-y-0 left-0 z-30
        transition-transform duration-300 ease-in-out
        ${isMobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        ${!isMobileOpen ? "md:flex" : "flex"}
      `}>
        <Sidebar onNavClick={() => { if (window.innerWidth < 768) setSidebarOpen(false); }} />
      </div>

      {/* Main content */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        {children}
      </main>

      {aiAssistantOpen && <AIAssistantPanel />}
      {commandPaletteOpen && <CommandPalette />}
      <ReminderModal />

      {/* Claude setup onboarding — shown once per device after first login */}
      {_hasHydrated && user && !claudeSetupSeen && (
        <ClaudeSetupModal
          userName={user.name}
          onDismiss={setClaudeSetupSeen}
        />
      )}
    </div>
  );
}
