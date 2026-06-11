"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { useRouter } from "next/navigation";
import { PRIORITY_CONFIG, HEALTH_CONFIG } from "@/lib/types";
import { formatDate, getDaysUntil, initials } from "@/lib/utils";
import { cn } from "@/lib/utils";
import type { Project } from "@/lib/types";

// Collect all people on this project (assignees + owner, deduplicated)
function ProjectAssignees({ project }: { project: Project }) {
  const seen = new Set<string>();
  const members: { id: string; name: string }[] = [];

  // Use the dedicated assignees field from the kanban endpoint
  for (const a of (project as any).assignees ?? []) {
    if (!seen.has(a.id)) {
      seen.add(a.id);
      members.push({ id: a.id, name: a.name });
    }
  }

  // Fall back to task assignees (for project detail view where tasks are loaded)
  for (const task of project.tasks ?? []) {
    if (task.assignee && !seen.has(task.assignee.id)) {
      seen.add(task.assignee.id);
      members.push({ id: task.assignee.id, name: task.assignee.name });
    }
  }

  // Include owner if not already shown
  if (project.owner && !seen.has(project.owner.id)) {
    members.unshift({ id: project.owner.id, name: project.owner.name });
  }

  if (members.length === 0) {
    return <span className="text-[11px] text-slate-600">Unassigned</span>;
  }

  const visible = members.slice(0, 3);
  const overflow = members.length - visible.length;
  const label = members.map((m) => m.name.split(" ")[0]).join(", ");

  return (
    <div className="flex items-center gap-1.5" title={members.map((m) => m.name).join(", ")}>
      <div className="flex -space-x-1.5">
        {visible.map((m) => (
          <div
            key={m.id}
            className="w-5 h-5 rounded-full bg-indigo-700 border border-[#0f1629] flex items-center justify-center"
          >
            <span className="text-[9px] text-white font-medium leading-none">{initials(m.name)}</span>
          </div>
        ))}
        {overflow > 0 && (
          <div className="w-5 h-5 rounded-full bg-slate-700 border border-[#0f1629] flex items-center justify-center">
            <span className="text-[8px] text-slate-300 font-medium leading-none">+{overflow}</span>
          </div>
        )}
      </div>
      <span className="text-[11px] text-slate-500 truncate max-w-[80px]">{label}</span>
    </div>
  );
}

interface ProjectCardProps {
  project: Project;
  isDragging?: boolean;
}

export function ProjectCard({ project, isDragging }: ProjectCardProps) {
  const router = useRouter();
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: project.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isSortableDragging ? 0.4 : 1,
  };

  const latestHealth = project.health_records?.[project.health_records.length - 1];
  const daysLeft = getDaysUntil(project.due_date);
  const isOverdue = daysLeft !== null && daysLeft < 0;
  const priority = PRIORITY_CONFIG[project.priority];

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      className={cn(
        "bg-[#0f1629] border border-slate-800 rounded-xl p-3.5",
        "card-glow transition-smooth select-none",
        isDragging && "shadow-2xl shadow-indigo-900/30 rotate-1 scale-105 border-indigo-700/50",
        project.priority === "urgent" && "priority-urgent",
        project.priority === "high" && "priority-high"
      )}
    >
      {/* Top row: priority + drag handle */}
      <div className="flex items-center justify-between mb-2">
        <span className={cn("text-[10px] font-bold px-1.5 py-0.5 rounded", priority.color, priority.bg)}>
          {priority.label.toUpperCase()}
        </span>
        <div className="flex items-center gap-2">
          {latestHealth && (
            <div className={cn("w-1.5 h-1.5 rounded-full", HEALTH_CONFIG[latestHealth.health_status].dot)} />
          )}
          {project.blockers && <span className="text-red-400 text-[10px]">BLOCKED</span>}
          {/* Drag handle — only this area initiates drag */}
          <div
            {...listeners}
            className="cursor-grab active:cursor-grabbing text-slate-600 hover:text-slate-400 transition-colors px-0.5 touch-none"
            title="Drag to move"
          >
            <svg width="10" height="14" viewBox="0 0 10 14" fill="currentColor">
              <circle cx="2" cy="2" r="1.5" />
              <circle cx="8" cy="2" r="1.5" />
              <circle cx="2" cy="7" r="1.5" />
              <circle cx="8" cy="7" r="1.5" />
              <circle cx="2" cy="12" r="1.5" />
              <circle cx="8" cy="12" r="1.5" />
            </svg>
          </div>
        </div>
      </div>

      {/* Clickable card body — navigates to project detail */}
      <div
        className="cursor-pointer"
        onClick={() => router.push(`/projects/${project.id}`)}
      >
        {/* Title */}
        <p className="text-sm font-medium text-slate-100 hover:text-indigo-300 transition-colors mb-1.5 line-clamp-2">
          {project.title}
        </p>

        {/* Description */}
        {project.description && (
          <p className="text-[11px] text-slate-500 line-clamp-2 mb-2 leading-relaxed">
            {project.description}
          </p>
        )}

        {/* Progress bar */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-slate-600">Progress</span>
            <span className="text-[10px] text-slate-400">{project.progress_pct}%</span>
          </div>
          <div className="bg-slate-800 rounded-full h-1">
            <div className="progress-bar" style={{ width: `${project.progress_pct}%` }} />
          </div>
        </div>

        {/* Tags */}
        {project.tags?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2.5">
            {project.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                {tag}
              </span>
            ))}
            {project.tags.length > 3 && (
              <span className="text-[10px] text-slate-600">+{project.tags.length - 3}</span>
            )}
          </div>
        )}

        {/* Bottom row: assignees + due date */}
        <div className="flex items-center justify-between">
          <ProjectAssignees project={project} />

          {project.due_date && (
            <span className={cn(
              "text-[11px]",
              isOverdue ? "text-red-400 font-medium" : daysLeft! <= 3 ? "text-amber-400" : "text-slate-500"
            )}>
              {isOverdue ? `${Math.abs(daysLeft!)}d overdue` : formatDate(project.due_date)}
            </span>
          )}
        </div>

        {/* AI next action hint */}
        {project.next_action && (
          <div className="mt-2.5 pt-2.5 border-t border-slate-800">
            <p className="text-[10px] text-indigo-400 flex items-center gap-1">
              <span className="ai-pulse">✦</span>
              <span className="line-clamp-1">{project.next_action}</span>
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
