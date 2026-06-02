"use client";

import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { ProjectCard } from "./ProjectCard";
import { cn } from "@/lib/utils";
import type { Project, ProjectStatus } from "@/lib/types";

interface KanbanColumnProps {
  id: ProjectStatus;
  label: string;
  color: string;
  projects: Project[];
  onAddProject?: () => void;
}

export function KanbanColumn({ id, label, color, projects, onAddProject }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex flex-col w-72 shrink-0 bg-[#080f20]/80 rounded-xl border transition-smooth",
        isOver ? "border-indigo-600/60 shadow-lg shadow-indigo-900/20" : "border-slate-800/60"
      )}
    >
      {/* Column header */}
      <div className={cn("flex items-center justify-between px-3.5 py-3 border-b border-slate-800/60 rounded-t-xl", `border-l-2 ${color}`)}>
        <div className="flex items-center gap-2">
          <h3 className="text-xs font-semibold text-slate-300 uppercase tracking-wide">
            {label}
          </h3>
          <span className="text-[10px] font-medium text-slate-600 bg-slate-800 rounded-full px-1.5 py-0.5 min-w-[20px] text-center">
            {projects.length}
          </span>
        </div>
        {onAddProject && (
          <button
            onClick={onAddProject}
            className="text-slate-600 hover:text-indigo-400 transition-colors text-lg leading-none"
          >
            +
          </button>
        )}
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-2.5 space-y-2 min-h-[200px]">
        <SortableContext
          items={projects.map((p) => p.id)}
          strategy={verticalListSortingStrategy}
        >
          {projects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </SortableContext>

        {projects.length === 0 && (
          <div className="flex items-center justify-center h-24 text-slate-700 text-xs border border-dashed border-slate-800 rounded-lg">
            Drop cards here
          </div>
        )}
      </div>
    </div>
  );
}
