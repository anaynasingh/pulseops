## Discovered Capabilities

<!-- Promoted from HISTORY learnings via probe gate. -->
<!-- Format: - [date] insight - burst: <name> -->

- [2026-06-25] The AI assistant is now actionable at the individual-task level: /ai/chat builds per-user task context (open/overdue/due-today/due-week/urgent/high counts + relevance-sorted listing), so it can answer "what should I focus on today / my overdue / my top priorities" with real data, not just project summaries - burst: assistant-task-prompts
- [2026-06-26] AI Intake is now end-to-end functional: confirm classifies project-vs-task (AI suggestion + user override + parent-project picker), creates real persisted Task rows under a new or existing project, logs activity to both dashboard feeds, and busts the kanban cache so the board reflects new work without a manual reload - burst: intake-functional
- [2026-06-26] AI Intake confirm now auto-assigns ownership: a new project's owner_id and every created task's assigned_to default to the confirming user, with a three-state override contract (omit the field => creator; explicit null => ownerless/unassigned; explicit UUID => that user) via Pydantic model_fields_set. Applies to project Routes 1+3 and the task loop; an existing project's owner (Route 2) is never mutated - burst: intake-default-assignee

