/**
 * PulseOps — Typed API Client
 * Thin wrapper around axios pointing at FastAPI backend.
 */
import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT from localStorage on every request
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("pulseops_token");
    if (token) config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  microsoftLogin: () => {
    window.location.href = `${API_URL}/api/v1/auth/microsoft/login`;
  },
  exchangeCode: (code: string) =>
    api.post("/auth/microsoft/token", { code }).then((r) => r.data),
  me: () => api.get("/auth/me").then((r) => r.data),
};

// ── Projects ──────────────────────────────────────────────────────────────────

export const projectsApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/projects", { params }).then((r) => r.data),
  get: (id: string) => api.get(`/projects/${id}`).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    api.post("/projects", data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/projects/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/projects/${id}`),
};

// ── Kanban ────────────────────────────────────────────────────────────────────

export const kanbanApi = {
  move: (project_id: string, new_status: string, new_order?: number) =>
    api.patch("/kanban/move", { project_id, new_status, new_order }).then((r) => r.data),
};

// ── Tasks ─────────────────────────────────────────────────────────────────────

export const tasksApi = {
  list: (params?: Record<string, unknown>) =>
    api.get("/tasks", { params }).then((r) => r.data),
  create: (data: Record<string, unknown>) =>
    api.post("/tasks", data).then((r) => r.data),
  update: (id: string, data: Record<string, unknown>) =>
    api.patch(`/tasks/${id}`, data).then((r) => r.data),
  delete: (id: string) => api.delete(`/tasks/${id}`),
};

// ── AI ────────────────────────────────────────────────────────────────────────

export const aiApi = {
  chat: (message: string, project_id?: string) =>
    api.post("/ai/chat", { message, project_id }).then((r) => r.data),
  intake: (raw_input: string, team_id?: string) =>
    api.post("/ai/intake", { raw_input, team_id }).then((r) => r.data),
  confirmIntake: (intake_id: string, data: Record<string, unknown>) =>
    api.post(`/ai/intake/${intake_id}/confirm`, data).then((r) => r.data),
  extractEmail: (data: Record<string, unknown>) =>
    api.post("/ai/extract-email", data).then((r) => r.data),
  extractTranscript: (data: Record<string, unknown>) =>
    api.post("/ai/extract-transcript", data).then((r) => r.data),
  transcriptCreateTasks: (transcript_id: string, selected_indices: number[], project_id: string) =>
    api.post(`/ai/transcript/${transcript_id}/create-tasks`, { selected_indices, project_id }).then((r) => r.data),
  confirmTasks: (tasks: Record<string, unknown>[], project_id?: string | null) =>
    api.post("/ai/confirm-tasks", { tasks, project_id }).then((r) => r.data),
  summarize: (data: Record<string, unknown>) =>
    api.post("/ai/summarize", data).then((r) => r.data),
  suggestPriority: (project_id: string) =>
    api.post("/ai/suggest-priority", { project_id }).then((r) => r.data),
  nextActions: (project_id: string) =>
    api.post("/ai/next-actions", { project_id }).then((r) => r.data),
  insights: (project_id: string) =>
    api.get(`/ai/insights/${project_id}`).then((r) => r.data),
  dismissInsight: (insight_id: string) =>
    api.delete(`/ai/insights/${insight_id}/dismiss`),
};

// ── Search ────────────────────────────────────────────────────────────────────

export const searchApi = {
  keyword: (q: string) => api.get("/search/keyword", { params: { q } }).then((r) => r.data),
  semantic: (query: string, content_types?: string[], limit = 10) =>
    api.post("/search/semantic", { query, content_types, limit }).then((r) => r.data),
};

// ── Analytics ─────────────────────────────────────────────────────────────────

export const analyticsApi = {
  dashboard: () => api.get("/analytics/dashboard").then((r) => r.data),
  health: (project_id: string) =>
    api.get(`/analytics/health/${project_id}`).then((r) => r.data),
  gantt: () => api.get("/analytics/gantt").then((r) => r.data),
};

// ── Notifications ─────────────────────────────────────────────────────────────

export const notificationsApi = {
  list: (params?: { limit?: number; unread?: boolean }) =>
    api.get("/notifications", { params }).then((r) => r.data),
  markRead: (id: string) =>
    api.patch(`/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () => api.patch("/notifications/read-all").then((r) => r.data),
};
