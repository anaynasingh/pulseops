// ── PulseOps — Shared TypeScript Types ───────────────────────────────────────

export type UserRole = "admin" | "contributor" | "viewer" | "requester";
export type ProjectStatus =
  | "intake" | "todo" | "in_progress" | "blocked" | "review" | "done" | "potential" | "cancelled";
export type PriorityLevel = "low" | "medium" | "high" | "urgent";
export type HealthStatus = "healthy" | "at_risk" | "delayed" | "blocked";
export type IntakeStatus = "pending" | "confirmed" | "rejected";
export type SummaryType = "daily" | "weekly" | "executive" | "blocker";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  avatar_url?: string;
  is_active: boolean;
  mcp_setup_done: boolean;
  created_at: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description?: string;
  status: ProjectStatus;
  priority: PriorityLevel;
  assigned_to?: string;
  due_date?: string;
  is_completed: boolean;
  completed_at?: string;
  created_at: string;
  assignee?: User;
  project?: { id: string; title: string; status: ProjectStatus; priority: PriorityLevel };
}

export interface AIInsight {
  id: string;
  project_id?: string;
  insight_type: string;
  body: string;
  confidence_score: number;
  is_dismissed: boolean;
  created_at: string;
}

export interface ProjectHealth {
  id: string;
  project_id: string;
  health_status: HealthStatus;
  health_score: number;
  risk_score: number;
  delivery_confidence: number;
  reasoning?: string;
  evaluated_at: string;
}

export interface Project {
  id: string;
  title: string;
  description?: string;
  status: ProjectStatus;
  priority: PriorityLevel;
  owner_id?: string;
  team_id?: string;
  progress_pct: number;
  due_date?: string;
  tags: string[];
  stakeholders: string[];
  next_action?: string;
  risks?: string;
  blockers?: string;
  health_score: number;
  latest_update?: string;
  kanban_order: number;
  created_by?: string;
  created_at: string;
  updated_at: string;
  owner?: User;
  tasks: Task[];
  insights: AIInsight[];
  health_records: ProjectHealth[];
}

export interface ActivityLog {
  id: string;
  entity_type: string;
  entity_id: string;
  user_id?: string;
  action: string;
  old_value?: string;
  new_value?: string;
  metadata: Record<string, unknown>;
  created_at: string;
  user?: User;
}

export interface IntakeResult {
  id: string;
  raw_input: string;
  generated_title?: string;
  generated_description?: string;
  project_type?: string;
  suggested_tags: string[];
  suggested_subtasks: string[];
  suggested_next_steps: string[];
  suggested_due_date?: string;
  suggested_priority?: PriorityLevel;
  suggested_owners: string[];
  ai_reasoning?: string;
  user_confirmed_priority?: PriorityLevel;
  intake_status: IntakeStatus;
  project_id?: string;
  created_at: string;
}

export interface TranscriptResult {
  id: string;
  project_id?: string;
  title: string;
  source: string;
  summary?: string;
  action_items: Array<{
    task: string;
    owner?: string;
    deadline?: string;
    priority: PriorityLevel;
  }>;
  decisions: string[];
  blockers: string[];
  attendees: string[];
  meeting_date?: string;
  tasks_created: boolean;
  created_at: string;
}

export interface EmailResult {
  id: string;
  subject?: string;
  sender?: string;
  summary?: string;
  extracted_tasks: Array<{
    title: string;
    assignee?: string;
    due_date?: string;
    priority: PriorityLevel;
    context?: string;
  }>;
  extracted_people: string[];
  tasks_created: boolean;
  created_at: string;
}

export interface DashboardStats {
  total_projects: number;
  active_projects: number;
  blocked_projects: number;
  done_this_week: number;
  intake_queue: number;
  overdue_projects: number;
  team_workload: Array<{ user_id: string; name: string; project_count: number }>;
  recent_activity: ActivityLog[];
  high_priority_projects: Project[];
  stale_projects: Project[];
  ai_insights: AIInsight[];
  priority_distribution: Record<string, number>;
}

// Kanban column definitions
export const KANBAN_COLUMNS: { id: ProjectStatus; label: string; color: string }[] = [
  { id: "intake",      label: "Intake",     color: "border-slate-500" },
  { id: "todo",        label: "To Do",      color: "border-blue-500" },
  { id: "in_progress", label: "In Progress", color: "border-indigo-500" },
  { id: "blocked",     label: "Blocked",    color: "border-red-500" },
  { id: "review",      label: "Review",     color: "border-amber-500" },
  { id: "done",        label: "Done",       color: "border-green-500" },
  { id: "potential",   label: "Potential",  color: "border-purple-500" },
];

export const PRIORITY_CONFIG: Record<PriorityLevel, { label: string; color: string; bg: string }> = {
  low:    { label: "Low",    color: "text-slate-400",  bg: "bg-slate-800" },
  medium: { label: "Medium", color: "text-blue-400",   bg: "bg-blue-900/30" },
  high:   { label: "High",   color: "text-amber-400",  bg: "bg-amber-900/30" },
  urgent: { label: "Urgent", color: "text-red-400",    bg: "bg-red-900/30" },
};

// Light mode — solid coloured backgrounds with white text for maximum contrast
export const PRIORITY_CONFIG_LIGHT: Record<PriorityLevel, { label: string; color: string; bg: string }> = {
  low:    { label: "Low",    color: "text-white", bg: "bg-slate-500" },
  medium: { label: "Medium", color: "text-white", bg: "bg-blue-600" },
  high:   { label: "High",   color: "text-white", bg: "bg-amber-500" },
  urgent: { label: "Urgent", color: "text-white", bg: "bg-red-600" },
};

export const HEALTH_CONFIG: Record<HealthStatus, { label: string; color: string; dot: string }> = {
  healthy:  { label: "Healthy",  color: "text-green-400",  dot: "bg-green-400" },
  at_risk:  { label: "At Risk",  color: "text-amber-400",  dot: "bg-amber-400" },
  delayed:  { label: "Delayed",  color: "text-orange-400", dot: "bg-orange-400" },
  blocked:  { label: "Blocked",  color: "text-red-400",    dot: "bg-red-400" },
};
