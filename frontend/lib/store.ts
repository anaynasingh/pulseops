/**
 * PulseOps — Zustand Global Store
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, Project } from "./types";

interface AuthState {
  user: User | null;
  token: string | null;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
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
    }),
    { name: "pulseops-auth" }
  )
);

interface UIState {
  sidebarOpen: boolean;
  commandPaletteOpen: boolean;
  aiAssistantOpen: boolean;
  activeProjectId: string | null;
  setSidebarOpen: (v: boolean) => void;
  toggleCommandPalette: () => void;
  toggleAIAssistant: () => void;
  setActiveProject: (id: string | null) => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  commandPaletteOpen: false,
  aiAssistantOpen: false,
  activeProjectId: null,
  setSidebarOpen: (v) => set({ sidebarOpen: v }),
  toggleCommandPalette: () => set((s) => ({ commandPaletteOpen: !s.commandPaletteOpen })),
  toggleAIAssistant: () => set((s) => ({ aiAssistantOpen: !s.aiAssistantOpen })),
  setActiveProject: (id) => set({ activeProjectId: id }),
}));

interface ReminderState {
  enabled: boolean;
  intervalMin: number;       // minutes between reminders
  snoozedUntil: number | null; // epoch ms; null = not snoozed
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
