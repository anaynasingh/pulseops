"use client";

import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { projectsApi, tasksApi, aiApi, usersApi } from "@/lib/api";
import { Header } from "@/components/layout/Header";
import { PRIORITY_CONFIG, HEALTH_CONFIG, KANBAN_COLUMNS } from "@/lib/types";
import { formatDate, getDaysUntil, initials } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { Project } from "@/lib/types";
import { useAuthStore } from "@/lib/store";
import { canEditTask } from "@/lib/permissions";

// ── Inline editable field ─────────────────────────────────────────────────────
function EditableText({
  value,
  onSave,
  multiline = false,
  placeholder = "Click to edit…",
  className = "",
}: {
  value: string;
  onSave: (v: string) => void;
  multiline?: boolean;
  placeholder?: string;
  className?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  const commit = () => {
    setEditing(false);
    if (draft !== value) onSave(draft);
  };

  if (editing) {
    return multiline ? (
      <textarea
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        rows={3}
        className={cn("w-full bg-slate-800 border border-indigo-500 rounded-lg px-3 py-2 text-sm text-white resize-none focus:outline-none", className)}
      />
    ) : (
      <input
        autoFocus
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === "Enter" && commit()}
        className={cn("w-full bg-slate-800 border border-indigo-500 rounded-lg px-3 py-2 text-sm text-white focus:outline-none", className)}
      />
    );
  }

  return (
    <p
      onClick={() => { setDraft(value); setEditing(true); }}
      className={cn("cursor-text hover:bg-slate-800/50 rounded px-1 -mx-1 transition-colors", className)}
      title="Click to edit"
    >
      {value || <span className="text-slate-600 italic">{placeholder}</span>}
    </p>
  );
}

// ── Select field ──────────────────────────────────────────────────────────────
function EditableSelect({
  value,
  options,
  onSave,
  className = "",
}: {
  value: string;
  options: { value: string; label: string }[];
  onSave: (v: string) => void;
  className?: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onSave(e.target.value)}
      className={cn("bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500 cursor-pointer", className)}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

// ── Task edit modal ───────────────────────────────────────────────────────────
function TaskModal({
  task,
  currentProjectId,
  canEdit,
  onClose,
  onSave,
  onDelete,
}: {
  task: { id: string; title: string; description?: string; priority: string; status: string; is_completed: boolean; due_date?: string; assigned_to?: string; created_by?: string; assignee?: { id: string; name: string } | null } | null;
  currentProjectId: string;
  canEdit: boolean;
  onClose: () => void;
  onSave: (id: string, data: Record<string, unknown>) => void;
  onDelete: (id: string) => void;
}) {
  const [title, setTitle] = useState(task?.title ?? "");
  const [description, setDescription] = useState(task?.description ?? "");
  const [priority, setPriority] = useState(task?.priority ?? "medium");
  const [dueDate, setDueDate] = useState(task?.due_date ?? "");
  const [assignedTo, setAssignedTo] = useState(task?.assigned_to ?? task?.assignee?.id ?? "");
  const [projectId, setProjectId] = useState(currentProjectId);
  const [isPrivate, setIsPrivate] = useState((task as any)?.is_private ?? false);

  // Load team members and all projects for dropdowns
  const { data: users = [] } = useQuery({ queryKey: ["users"], queryFn: () => usersApi.list() });
  const { data: allProjects = [] } = useQuery<any[]>({ queryKey: ["projects-all"], queryFn: () => projectsApi.list({ limit: 100 }) });

  if (!task) return null;

  const inputCls = "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed";

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#0f1629] border border-slate-700 rounded-2xl w-full max-w-lg shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
          <h2 className="text-sm font-semibold text-white">{canEdit ? "Edit Task" : "View Task"}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-xl leading-none transition-colors">×</button>
        </div>
        <div className="p-5 space-y-4">
          {!canEdit && (
            <div className="rounded-lg bg-amber-950/40 border border-amber-800/40 px-3 py-2 text-[11px] text-amber-300">
              🔒 This task is assigned to / created by someone else, so it's read-only. Only the assignee, creator, or an admin can edit it.
            </div>
          )}
          {/* Title */}
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Title</label>
            <input value={title} onChange={(e) => setTitle(e.target.value)} disabled={!canEdit} className={inputCls} />
          </div>
          {/* Description */}
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">Description</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} disabled={!canEdit} rows={3} className={`${inputCls} resize-none`} />
          </div>
          {/* Priority + Due Date */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-400 block mb-1.5">Priority</label>
              <select value={priority} onChange={(e) => setPriority(e.target.value)} disabled={!canEdit} className={inputCls}>
                {["low", "medium", "high", "urgent"].map((p) => (
                  <option key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-400 block mb-1.5">Due Date</label>
              <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} disabled={!canEdit} className={inputCls} />
            </div>
          </div>
          {/* Assignee */}
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">
              Assigned to
              {task.assignee && <span className="ml-2 text-slate-600">currently: {task.assignee.name}</span>}
            </label>
            <select value={assignedTo} onChange={(e) => setAssignedTo(e.target.value)} disabled={!canEdit} className={inputCls}>
              <option value="">Unassigned</option>
              {(users as any[]).map((u: any) => (
                <option key={u.id} value={u.id}>{u.name}</option>
              ))}
            </select>
          </div>
          {/* Private toggle */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-slate-900/40 border border-slate-700">
            <div>
              <p className="text-xs text-white font-medium">{isPrivate ? "🔒 Private task" : "👁 Visible to team"}</p>
              <p className="text-[11px] text-slate-500 mt-0.5">
                {isPrivate ? "Only you and the assignee can see this" : "All team members can see this task"}
              </p>
            </div>
            <button
              onClick={() => canEdit && setIsPrivate(!isPrivate)}
              disabled={!canEdit}
              className={`relative w-10 h-5 rounded-full transition-colors disabled:opacity-60 disabled:cursor-not-allowed ${isPrivate ? "bg-amber-500" : "bg-slate-600"}`}
            >
              <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${isPrivate ? "translate-x-5" : "translate-x-0.5"}`} />
            </button>
          </div>

          {/* Move to project */}
          <div>
            <label className="text-xs text-slate-400 block mb-1.5">
              Project
              <span className="ml-2 text-indigo-400 text-[10px] bg-indigo-950 px-1.5 py-0.5 rounded">move task</span>
            </label>
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)} disabled={!canEdit} className={inputCls}>
              {(allProjects as any[]).map((p: any) => (
                <option key={p.id} value={p.id}>{p.title}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex items-center justify-between px-5 py-4 border-t border-slate-800">
          {canEdit ? (
            <>
              <button
                onClick={() => { onDelete(task.id); onClose(); }}
                className="text-xs text-red-400 hover:text-red-300 transition-colors"
              >
                Delete task
              </button>
              <div className="flex gap-2">
                <button onClick={onClose} className="px-3 py-1.5 text-xs text-slate-400 hover:text-white transition-colors">
                  Cancel
                </button>
                <button
                  onClick={() => {
                    onSave(task.id, {
                      title,
                      description,
                      priority,
                      due_date: dueDate || null,
                      assigned_to: assignedTo || null,
                      is_private: isPrivate,
                      ...(projectId !== currentProjectId && { project_id: projectId }),
                    });
                    onClose();
                  }}
                  className="px-4 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
                >
                  Save changes
                </button>
              </div>
            </>
          ) : (
            <button onClick={onClose} className="ml-auto px-4 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors">
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user } = useAuthStore();
  const [editingTask, setEditingTask] = useState<string | null>(null);
  const [addingTask, setAddingTask] = useState(false);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskDueDate, setNewTaskDueDate] = useState("");

  const { data: project, isLoading } = useQuery<Project>({
    queryKey: ["project", id],
    queryFn: () => projectsApi.get(id),
  });

  const updateProject = useMutation({
    mutationFn: (data: Record<string, unknown>) => projectsApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", id] }),
  });

  const updateTask = useMutation({
    mutationFn: ({ taskId, data }: { taskId: string; data: Record<string, unknown> }) =>
      tasksApi.update(taskId, data),
    // Optimistic update — patch the cached task instantly so the UI never waits on the server
    onMutate: async ({ taskId, data }) => {
      await queryClient.cancelQueries({ queryKey: ["project", id] });
      const previous = queryClient.getQueryData<Project>(["project", id]);
      if (previous) {
        queryClient.setQueryData<Project>(["project", id], {
          ...previous,
          tasks: (previous.tasks ?? []).map((t) =>
            t.id === taskId ? { ...t, ...data } : t
          ),
        });
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) queryClient.setQueryData(["project", id], context.previous);
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["project", id] }),
  });

  const deleteTask = useMutation({
    mutationFn: (taskId: string) => tasksApi.delete(taskId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["project", id] }),
  });

  const createTask = useMutation({
    mutationFn: ({ title, due_date }: { title: string; due_date?: string }) =>
      tasksApi.create({ project_id: id, title, priority: "medium", status: "todo", due_date: due_date || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["project", id] });
      setNewTaskTitle("");
      setNewTaskDueDate("");
      setAddingTask(false);
    },
  });

  const deleteProject = useMutation({
    mutationFn: () => projectsApi.delete(id),
    onSuccess: () => router.push("/board"),
  });

  const nextActionsMutation = useMutation({
    mutationFn: () => aiApi.nextActions(id),
  });

  const priorityMutation = useMutation({
    mutationFn: () => aiApi.suggestPriority(id),
  });

  if (isLoading) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <Header title="Project" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-slate-500 text-sm animate-pulse">Loading project…</div>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-col h-full overflow-hidden">
        <Header title="Project not found" />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-slate-400 mb-4">This project doesn't exist or was deleted.</p>
            <button onClick={() => router.push("/board")} className="text-indigo-400 hover:text-indigo-300 text-sm">
              ← Back to board
            </button>
          </div>
        </div>
      </div>
    );
  }

  const save = (data: Record<string, unknown>) => updateProject.mutate(data);
  const priority = PRIORITY_CONFIG[project.priority];
  const latestHealth = project.health_records?.slice(-1)[0];
  const daysLeft = getDaysUntil(project.due_date);
  const isOverdue = daysLeft !== null && daysLeft < 0;
  const editingTaskObj = project.tasks?.find((t) => t.id === editingTask) ?? null;

  return (
    <>
      {editingTaskObj && (
        <TaskModal
          task={editingTaskObj}
          currentProjectId={id!}
          canEdit={canEditTask(editingTaskObj, user)}
          onClose={() => setEditingTask(null)}
          onSave={(taskId, data) => updateTask.mutate({ taskId, data })}
          onDelete={(taskId) => deleteTask.mutate(taskId)}
        />
      )}

      <div className="flex flex-col h-full overflow-hidden">
        <Header
          title={project.title}
          subtitle={`${project.status.replace("_", " ")} · ${project.priority} priority`}
          actions={
            <div className="flex items-center gap-3">
              <button
                onClick={() => { if (confirm("Delete this project?")) deleteProject.mutate(); }}
                className="text-xs text-red-400 hover:text-red-300 transition-colors"
              >
                Delete
              </button>
              <button onClick={() => router.push("/board")} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                ← Board
              </button>
            </div>
          }
        />

        <div className="flex-1 overflow-y-auto px-6 py-5">
          <div className="max-w-4xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-5">

            {/* ── Main content ── */}
            <div className="lg:col-span-2 space-y-5">

              {/* Title + Description */}
              <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Title</h3>
                <EditableText
                  value={project.title}
                  onSave={(v) => save({ title: v })}
                  className="text-base font-semibold text-white mb-4"
                />
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">Description</h3>
                <EditableText
                  value={project.description ?? ""}
                  onSave={(v) => save({ description: v })}
                  multiline
                  placeholder="Add a description…"
                  className="text-sm text-slate-300 leading-relaxed"
                />
              </div>

              {/* Progress + Status */}
              <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">Progress</h3>
                  <div className="flex items-center gap-2">
                    <input
                      type="range"
                      min={0} max={100}
                      value={project.progress_pct}
                      onChange={(e) => save({ progress_pct: Number(e.target.value) })}
                      className="w-24 accent-indigo-500"
                    />
                    <span className="text-sm font-bold text-white w-8">{project.progress_pct}%</span>
                  </div>
                </div>
                <div className="bg-slate-800 rounded-full h-2 mb-4">
                  <div className="progress-bar" style={{ width: `${project.progress_pct}%` }} />
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {KANBAN_COLUMNS.map((col) => (
                    <button
                      key={col.id}
                      onClick={() => save({ status: col.id })}
                      className={cn(
                        "text-[10px] px-2 py-1 rounded border font-medium transition-colors",
                        project.status === col.id
                          ? "border-indigo-500 text-indigo-300 bg-indigo-950/30"
                          : "border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-300"
                      )}
                    >
                      {col.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tasks */}
              <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide">
                    Tasks ({project.tasks?.length ?? 0})
                  </h3>
                  <button
                    onClick={() => setAddingTask(true)}
                    className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                  >
                    + Add task
                  </button>
                </div>

                <div className="space-y-2">
                  {project.tasks?.map((task) => {
                    const canEdit = canEditTask(task, user);
                    return (
                    <div
                      key={task.id}
                      className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-900/60 group hover:bg-slate-800/60 transition-colors cursor-pointer"
                      onClick={() => setEditingTask(task.id)}
                    >
                      <button
                        disabled={!canEdit}
                        title={canEdit ? "Toggle complete" : "Only the assignee, creator, or an admin can change this task"}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (!canEdit) return;
                          updateTask.mutate({ taskId: task.id, data: { is_completed: !task.is_completed } });
                        }}
                        className={cn(
                          "w-4 h-4 rounded-full border-2 shrink-0 flex items-center justify-center transition-colors",
                          task.is_completed ? "border-green-500 bg-green-500" : "border-slate-600 hover:border-indigo-400",
                          !canEdit && "opacity-50 cursor-not-allowed hover:border-slate-600"
                        )}
                      >
                        {task.is_completed && <span className="text-[8px] text-white">✓</span>}
                      </button>
                      <span className={cn("text-sm flex-1", task.is_completed ? "line-through text-slate-600" : "text-slate-200")}>
                        {task.title}
                      </span>
                      {task.assignee && (
                        <div className="flex items-center gap-1.5 shrink-0">
                          <div className="w-5 h-5 rounded-full bg-indigo-700 flex items-center justify-center shrink-0">
                            <span className="text-[9px] text-white font-semibold leading-none">
                              {task.assignee.name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 hidden group-hover:inline transition-all">
                            {task.assignee.name.split(" ")[0]}
                          </span>
                        </div>
                      )}
                      {task.due_date && (
                        <span className={cn(
                          "text-[10px] shrink-0",
                          task.is_completed ? "text-slate-600" : "text-amber-500"
                        )}>
                          {task.due_date}
                        </span>
                      )}
                      <span className={`text-[10px] ${(PRIORITY_CONFIG[task.priority] ?? PRIORITY_CONFIG.medium).color} opacity-0 group-hover:opacity-100 transition-opacity`}>
                        {task.priority}
                      </span>
                      <span className="text-[10px] text-slate-600 opacity-0 group-hover:opacity-100 transition-opacity">
                        {canEdit ? "Edit →" : "🔒 View"}
                      </span>
                    </div>
                  );
                  })}

                  {addingTask && (
                    <div className="flex flex-col gap-2">
                      <div className="flex items-center gap-2">
                        <input
                          autoFocus
                          value={newTaskTitle}
                          onChange={(e) => setNewTaskTitle(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && newTaskTitle.trim()) createTask.mutate({ title: newTaskTitle.trim(), due_date: newTaskDueDate });
                            if (e.key === "Escape") { setAddingTask(false); setNewTaskDueDate(""); }
                          }}
                          placeholder="Task title… (Enter to save, Esc to cancel)"
                          className="flex-1 bg-slate-900 border border-indigo-500 rounded-lg px-3 py-2 text-sm text-white focus:outline-none"
                        />
                        <input
                          type="date"
                          value={newTaskDueDate}
                          onChange={(e) => setNewTaskDueDate(e.target.value)}
                          className="bg-slate-900 border border-slate-700 rounded-lg px-2 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                          title="Due date (optional)"
                        />
                        <button
                          onClick={() => newTaskTitle.trim() && createTask.mutate({ title: newTaskTitle.trim(), due_date: newTaskDueDate })}
                          className="px-3 py-2 text-xs bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors"
                        >
                          Add
                        </button>
                      </div>
                    </div>
                  )}

                  {!project.tasks?.length && !addingTask && (
                    <p className="text-xs text-slate-600 text-center py-4">No tasks yet. Click "+ Add task" to create one.</p>
                  )}
                </div>
              </div>

              {/* Blockers & Risks */}
              <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-5">
                <h3 className="text-xs font-semibold text-red-400 uppercase tracking-wide mb-3 flex items-center gap-1">
                  <span>⊗</span> Blockers
                </h3>
                <EditableText
                  value={project.blockers ?? ""}
                  onSave={(v) => save({ blockers: v || null })}
                  multiline
                  placeholder="Describe any blockers…"
                  className="text-sm text-slate-300"
                />
                <h3 className="text-xs font-semibold text-amber-400 uppercase tracking-wide mb-3 mt-4 flex items-center gap-1">
                  <span>⚠</span> Risks
                </h3>
                <EditableText
                  value={project.risks ?? ""}
                  onSave={(v) => save({ risks: v || null })}
                  multiline
                  placeholder="Describe any risks…"
                  className="text-sm text-slate-300"
                />
              </div>
            </div>

            {/* ── Sidebar ── */}
            <div className="space-y-4">
              {/* Meta fields */}
              <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Priority</span>
                  <EditableSelect
                    value={project.priority}
                    options={["low","medium","high","urgent"].map((p) => ({ value: p, label: p.charAt(0).toUpperCase() + p.slice(1) }))}
                    onSave={(v) => save({ priority: v })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Status</span>
                  <EditableSelect
                    value={project.status}
                    options={KANBAN_COLUMNS.map((c) => ({ value: c.id, label: c.label }))}
                    onSave={(v) => save({ status: v })}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Due date</span>
                  <input
                    type="date"
                    defaultValue={project.due_date ?? ""}
                    onBlur={(e) => save({ due_date: e.target.value || null })}
                    className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Next action</span>
                </div>
                <EditableText
                  value={project.next_action ?? ""}
                  onSave={(v) => save({ next_action: v || null })}
                  placeholder="Add next action…"
                  className="text-xs text-indigo-300"
                />
                {project.tags?.length > 0 && (
                  <div>
                    <span className="text-xs text-slate-500 block mb-1.5">Tags</span>
                    <div className="flex flex-wrap gap-1">
                      {project.tags.map((t) => (
                        <span key={t} className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">{t}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Health */}
              {latestHealth && (
                <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-4">
                  <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">Health</h3>
                  <div className="flex items-center gap-2 mb-3">
                    <div className={cn("w-2.5 h-2.5 rounded-full", HEALTH_CONFIG[latestHealth.health_status].dot)} />
                    <span className={cn("text-sm font-medium", HEALTH_CONFIG[latestHealth.health_status].color)}>
                      {HEALTH_CONFIG[latestHealth.health_status].label}
                    </span>
                  </div>
                  {[
                    { label: "Health", value: latestHealth.health_score, color: "bg-green-500" },
                    { label: "Risk", value: latestHealth.risk_score, color: "bg-red-500" },
                    { label: "Confidence", value: latestHealth.delivery_confidence, color: "bg-blue-500" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="mb-2">
                      <div className="flex justify-between text-[11px] mb-0.5">
                        <span className="text-slate-500">{label}</span>
                        <span className="text-slate-300">{value}</span>
                      </div>
                      <div className="bg-slate-800 rounded-full h-1">
                        <div className={`${color} h-1 rounded-full`} style={{ width: `${value}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* AI Actions */}
              <div className="bg-[#0f1629] border border-slate-800 rounded-xl p-4 space-y-2">
                <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3 flex items-center gap-1">
                  <span className="text-indigo-400 ai-pulse">✦</span> AI Actions
                </h3>
                <button
                  onClick={() => nextActionsMutation.mutate()}
                  disabled={nextActionsMutation.isPending}
                  className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:text-white bg-slate-900/60 hover:bg-slate-800 rounded-lg transition-colors border border-slate-800"
                >
                  {nextActionsMutation.isPending ? "Generating…" : "→ Suggest next actions"}
                </button>
                {nextActionsMutation.data && (
                  <div className="bg-indigo-950/30 border border-indigo-900/40 rounded-lg p-2.5">
                    <p className="text-[11px] text-slate-400 leading-relaxed whitespace-pre-line">
                      {nextActionsMutation.data.next_actions}
                    </p>
                  </div>
                )}
                <button
                  onClick={() => priorityMutation.mutate()}
                  disabled={priorityMutation.isPending}
                  className="w-full text-left px-3 py-2 text-xs text-slate-300 hover:text-white bg-slate-900/60 hover:bg-slate-800 rounded-lg transition-colors border border-slate-800"
                >
                  {priorityMutation.isPending ? "Analyzing…" : "⚑ Suggest priority"}
                </button>
                {priorityMutation.data && (
                  <div className="bg-amber-950/30 border border-amber-800/40 rounded-lg p-2.5">
                    <p className="text-xs text-amber-300 font-medium mb-1">
                      Suggested: {priorityMutation.data.suggested_priority?.toUpperCase()}
                    </p>
                    <p className="text-[11px] text-slate-400">{priorityMutation.data.reasoning}</p>
                    <button
                      onClick={() => save({ priority: priorityMutation.data.suggested_priority })}
                      className="mt-2 text-[10px] text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      Apply this priority →
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
