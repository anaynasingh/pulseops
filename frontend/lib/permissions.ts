import type { Task, User } from "./types";

/**
 * Mirror of the backend guardrail `_can_edit_task`: a task may be edited only by
 * its assignee, its creator, or an admin. Used to gate edit controls in the UI so
 * users don't attempt edits the API would reject with 403.
 */
export function canEditTask(
  task: Pick<Task, "assigned_to" | "created_by">,
  user: Pick<User, "id" | "role"> | null | undefined,
): boolean {
  if (!user) return false;
  if (user.role === "admin") return true;
  return task.assigned_to === user.id || task.created_by === user.id;
}
