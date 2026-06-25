/**
 * PulseOps — Zustand Global Store
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, Project } from "./types";

interface AuthState {
  user: User | null;
  token: string | null;
  _hasHydrated: boolean;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
  setHasHydrated: (v: boolean) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      _hasHydrated: false,
      setAuth: (user, token) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("pulseops_token", token);
        }
        set({ user, token });
      },
      clearAuth: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("pulseops_token");
        }
        set({ user: null, token: null });
      },
      setHasHydrated: (v) => set({ _hasHydrated: v }),
    }),
    {
      name: "pulseops-auth",
      onRehydrateStorage: () => (state) => {
        // Fires once localStorage has been read — safe to check user now
        state?.setHasHydrated(true);
      },
    }
  )
);

interface UIState {
  sidebarOpen: boolean;
  commandPaletteOpen: boolean;
  aiAssistantOpen: boolean;
  activeProjectId: string | null;
  theme: "dark" | "light";
  claudeSetupSeen: boolean;
  setSidebarOpen: (v: boolean) => void;
  toggleCommandPalette: () => void;
  toggleAIAssistant: () => void;
  setActiveProject: (id: string | null) => void;
  toggleTheme: () => void;
  setClaudeSetupSeen: () => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      commandPaletteOpen: false,
      aiAssistantOpen: false,
      activeProjectId: null,
      theme: "light",
      claudeSetupSeen: false,
      setSidebarOpen: (v) => set({ sidebarOpen: v }),
      toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
      toggleAIAssistant: () => set((s) => ({ aiAssistantOpen: !s.aiAssistantOpen })),
      setActiveProject: (id) => set({ activeProjectId: id }),
      toggleTheme: () => set((s) => ({ theme: s.theme === "dark" ? "light" : "dark" })),
      setClaudeSetupSeen: () => set({ claudeSetupSeen: true }),
    }),
    { name: "pulseops-ui", partialize: (s) => ({ theme: s.theme, claudeSetupSeen: s.claudeSetupSeen }) }
  )
);

interface ReminderState {
  enabled: boolean;
  intervalMin: number;
  snoozedUntil: number | null;
  visible: boolean;
  setEnabled: (v: boolean) => void;
  setIntervalMin: (v: number) => void;
  show: () => void;
  dismiss: () => void;
  snooze: (minutes: number) => void;
}

export const useReminderStore = create<ReminderState>()(
  persist(
    (set) => ({
      enabled: false,
      intervalMin: 60,
      snoozedUntil: null,
      visible: false,
      setEnabled: (v) => set({ enabled: v }),
      setIntervalMin: (v) => set({ intervalMin: v }),
      show: () => set({ visible: true }),
      dismiss: () => set({ visible: false, snoozedUntil: null }),
      snooze: (minutes) =>
        set({ visible: false, snoozedUntil: Date.now() + minutes * 60 * 1000 }),
    }),
    { name: "pulseops-reminder", partialize: (s) => ({ enabled: s.enabled, intervalMin: s.intervalMin }) }
  )
);

interface BoardState {
  projects: Project[];
  setProjects: (projects: Project[]) => void;
  updateProject: (id: string, data: Partial<Project>) => void;
  moveProject: (id: string, newStatus: Project["status"]) => void;
}

export const useBoardStore = create<BoardState>((set) => ({
  projects: [],
  setProjects: (projects) => set({ projects }),
  updateProject: (id, data) =>
    set((state) => ({
      projects: state.projects.map((p) => (p.id === id ? { ...p, ...data } : p)),
    })),
  moveProject: (id, newStatus) =>
    set((state) => ({
      projects: state.projects.map((p) =>
        p.id === id ? { ...p, status: newStatus } : p
      ),
    })),
}));
