"use client";

import { useState, useCallback, useEffect } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
  rectIntersection,
  closestCenter,
  type CollisionDetection,
} from "@dnd-kit/core";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { projectsApi, kanbanApi } from "@/lib/api";
import { useBoardStore } from "@/lib/store";
import { KANBAN_COLUMNS } from "@/lib/types";
import { KanbanColumn } from "./KanbanColumn";
import { ProjectCard } from "./ProjectCard";
import type { Project, ProjectStatus } from "@/lib/types";

interface KanbanBoardProps {
  searchQuery?: string;
  filterPriority?: string;
  filterOwner?: string;
}

// Custom collision: pointer position wins over corner proximity.
// Columns always take priority over cards so you can't accidentally
// drop in the wrong column.
const kanbanCollision: CollisionDetection = (args) => {
  // 1. Check if pointer is directly over a column first
  const columnIds = new Set(KANBAN_COLUMNS.map((c) => c.id));
  const columnContainers = args.droppableContainers.filter((c) =>
    columnIds.has(String(c.id))
  );
  const overColumn = pointerWithin({ ...args, droppableContainers: columnContainers });
  if (overColumn.length > 0) return overColumn;

  // 2. Fall back to rect intersection for empty columns
  return rectIntersection(args);
};

export function KanbanBoard({ searchQuery, filterPriority, filterOwner }: KanbanBoardProps) {
  const queryClient = useQueryClient();
  const { projects, setProjects, moveProject } = useBoardStore();
  const [activeProject, setActiveProject] = useState<Project | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  // Fetch projects
  const { data: fetchedProjects } = useQuery<Project[]>({
    queryKey: ["projects", searchQuery, filterPriority, filterOwner],
    queryFn: () =>
      projectsApi.list({
        q: searchQuery || undefined,
        priority: filterPriority || undefined,
        owner_id: filterOwner || undefined,
        limit: 200,
      }),
  });

  // Sync fetched projects into the board store
  useEffect(() => {
    if (fetchedProjects) setProjects(fetchedProjects);
  }, [fetchedProjects, setProjects]);

  // Kanban move mutation
  const moveMutation = useMutation({
    mutationFn: ({ projectId, newStatus }: { projectId: string; newStatus: string }) =>
      kanbanApi.move(projectId, newStatus),
    onError: () => {
      // Refetch to revert optimistic update on error
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const getProjectsForColumn = useCallback(
    (status: ProjectStatus) => projects.filter((p) => p.status === status),
    [projects]
  );

  const handleDragStart = (event: DragStartEvent) => {
    const project = projects.find((p) => p.id === event.active.id);
    setActiveProject(project ?? null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveProject(null);

    if (!over) return;

    // Determine target column (over.id is either a column id or a card id)
    const targetColumnId = KANBAN_COLUMNS.find((col) => col.id === over.id)?.id
      ?? projects.find((p) => p.id === over.id)?.status;

    if (!targetColumnId || active.id === over.id) return;

    const draggedProject = projects.find((p) => p.id === active.id);
    if (!draggedProject || draggedProject.status === targetColumnId) return;

    // Optimistic update
    moveProject(String(active.id), targetColumnId as ProjectStatus);

    // API call
    moveMutation.mutate({ projectId: String(active.id), newStatus: targetColumnId });
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={kanbanCollision}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-3 h-full pb-4">
        {KANBAN_COLUMNS.map((col) => (
          <KanbanColumn
            key={col.id}
            id={col.id}
            label={col.label}
            color={col.color}
            projects={getProjectsForColumn(col.id)}
          />
        ))}
      </div>

      {/* Drag overlay — the floating card being dragged */}
      <DragOverlay>
        {activeProject && (
          <ProjectCard project={activeProject} isDragging />
        )}
      </DragOverlay>
    </DndContext>
  );
}
