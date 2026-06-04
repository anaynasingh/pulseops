"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore, useUIStore } from "@/lib/store";
import { Sidebar } from "@/components/layout/Sidebar";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { AIAssistantPanel } from "@/components/ai/AIAssistantPanel";
import { CommandPalette } from "@/components/layout/CommandPalette";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user } = useAuthStore();
  const { aiAssistantOpen, commandPaletteOpen, toggleCommandPalette } = useUIStore();

  // Auth guard
  useEffect(() => {
    if (!user) {
      router.replace("/login");
    }
  }, [user, router]);

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
        <div className="absolute top-3 right-4 z-40">
          <NotificationBell />
        </div>
        {children}
      </main>

      {/* AI Assistant Panel */}
      {aiAssistantOpen && <AIAssistantPanel />}

      {/* Command Palette */}
      {commandPaletteOpen && <CommandPalette />}
    </div>
  );
}
