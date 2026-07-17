/**
 * PulseOps — Zustand Global Store
 */
import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { QueryClient } from "@tanstack/react-query";
import type { User, Project } from "./types";
import { aiApi } from "./api";

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

// ── AI Assistant chat ───────────────────────────────────────────────────────
//
// Chat state and the (long-running, agentic) send request live in this store
// rather than inside the AssistantChat component. Claude requests can take a
// minute or two; keeping them here means closing the slide-in panel or leaving
// the /assistant page — which unmounts the component — no longer discards the
// in-flight request or its reply. The store survives mount/unmount, so the
// answer lands whenever it's ready and is visible on reopen.

export interface ProposedTask {
  title: string;
  description?: string | null;
  priority?: string;
  assignee_name?: string | null;
  due_date_offset_days?: number | null;
}

export interface AssistantMessage {
  role: "user" | "assistant";
  content: string;
  checking?: boolean; // true while dedup is running
  proposedTasks?: ProposedTask[];
  proposedProjectId?: string | null;
  tasksConfirmed?: boolean;
  confirmedCount?: number;
}

export const ASSISTANT_GREETING =
  "Hi! I'm PulseOps AI. I can help you understand your projects, find blockers, generate summaries, and suggest priorities. What would you like to know?";

// The assistant proposes tasks by emitting a <<<PROPOSE_TASKS>>> {json} block
// instead of creating them. Parse it out so the UI can render the select + dedupe flow.
function parseProposeBlock(
  reply: string
): { tasks: ProposedTask[]; projectId: string | null; cleanedReply: string } | null {
  const m = reply.match(/<<<PROPOSE_TASKS>>>([\s\S]*?)<<<END_PROPOSE_TASKS>>>/);
  if (!m) return null;
  try {
    const parsed = JSON.parse(m[1].trim());
    const raw = Array.isArray(parsed?.tasks) ? parsed.tasks : [];
    const tasks: ProposedTask[] = raw
      .filter((t: Record<string, unknown>) => t && t.title)
      .map((t: Record<string, unknown>) => ({
        title: String(t.title),
        description: (t.description as string) ?? null,
        priority: (t.priority as string) ?? "medium",
        assignee_name: (t.assignee_name as string) ?? null,
        due_date_offset_days:
          typeof t.due_date_offset_days === "number" ? (t.due_date_offset_days as number) : null,
      }));
    return { tasks, projectId: (parsed?.project_id as string) ?? null, cleanedReply: reply.replace(m[0], "").trim() };
  } catch {
    return null;
  }
}

interface AssistantState {
  messages: AssistantMessage[];
  loading: boolean;
  claudeSession: string | null;
  dedupeResult: unknown | null;
  dedupeProjectId: string | undefined;
  sendMessage: (text: string, queryClient: QueryClient) => Promise<void>;
  patchMessage: (index: number, patch: Partial<AssistantMessage>) => void;
  clearChat: () => void;
  clearDedupe: () => void;
}

export const useAssistantStore = create<AssistantState>()(
  persist(
    (set, get) => ({
      messages: [{ role: "assistant", content: ASSISTANT_GREETING }],
      loading: false,
      claudeSession: null,
      dedupeResult: null,
      dedupeProjectId: undefined,

      patchMessage: (index, patch) =>
        set((s) => ({
          messages: s.messages.map((m, i) => (i === index ? { ...m, ...patch } : m)),
        })),

      clearChat: () =>
        set({
          messages: [{ role: "assistant", content: ASSISTANT_GREETING }],
          claudeSession: null,
        }),

      clearDedupe: () => set({ dedupeResult: null, dedupeProjectId: undefined }),

      sendMessage: async (text, queryClient) => {
        if (!text.trim() || get().loading) return;
        set((s) => ({
          messages: [...s.messages, { role: "user", content: text }],
          loading: true,
        }));

        // Helper: patch the last message in the list (the assistant reply).
        const patchLast = (patch: Partial<AssistantMessage>) =>
          set((s) => ({
            messages: s.messages.map((m, i) => (i === s.messages.length - 1 ? { ...m, ...patch } : m)),
          }));

        try {
          const res = await aiApi.claudeChat(text, get().claudeSession);
          if (res.session_id) set({ claudeSession: res.session_id });

          const proposal = parseProposeBlock(res.reply || "");
          const replyText =
            (proposal ? proposal.cleanedReply : res.reply) || "The assistant finished but returned no text.";
          set((s) => ({
            messages: [
              ...s.messages,
              { role: "assistant", content: replyText, checking: !!(proposal && proposal.tasks.length) },
            ],
          }));

          if (proposal && proposal.tasks.length > 0) {
            try {
              const dedup = await aiApi.checkDuplicates(
                proposal.tasks as unknown as Record<string, unknown>[],
                text
              );
              const hasIssues = dedup.duplicates_found > 0 || dedup.updates_suggested > 0;
              if (hasIssues) {
                set({ dedupeResult: dedup, dedupeProjectId: proposal.projectId || undefined });
                patchLast({ checking: false });
              } else {
                patchLast({
                  checking: false,
                  proposedTasks: proposal.tasks,
                  proposedProjectId: proposal.projectId,
                  tasksConfirmed: false,
                });
              }
            } catch {
              patchLast({
                checking: false,
                proposedTasks: proposal.tasks,
                proposedProjectId: proposal.projectId,
                tasksConfirmed: false,
              });
            }
          } else {
            // No proposal — the assistant may have completed/moved/deleted something. Refresh.
            queryClient.invalidateQueries({ queryKey: ["projects"] });
            queryClient.invalidateQueries({ queryKey: ["my-dashboard"] });
            queryClient.invalidateQueries({ queryKey: ["tasks"] });
          }
        } catch (e: unknown) {
          const err = e as { response?: { status?: number; data?: { detail?: string } } };
          const detail = err.response?.data?.detail;
          const content =
            err.response?.status === 503
              ? "The assistant service isn't reachable right now. Please try again in a moment."
              : detail || "Something went wrong talking to the assistant. Please try again.";
          set((s) => ({ messages: [...s.messages, { role: "assistant", content }] }));
        } finally {
          set({ loading: false });
        }
      },
    }),
    {
      name: "pulseops-assistant",
      // Persist only the conversation, never the transient in-flight flags — a
      // reload can't resume a lost request, so `loading`/`checking` must not stick.
      partialize: (s) => ({
        messages: s.messages.map((m) => ({ ...m, checking: false })),
        claudeSession: s.claudeSession,
      }),
    }
  )
);
