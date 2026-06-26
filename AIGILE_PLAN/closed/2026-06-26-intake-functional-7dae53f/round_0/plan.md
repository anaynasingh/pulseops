## Burst Plan
**Goal:** Make AI Intake confirm fully functional by classifying intake as project-vs-task, routing the confirm to create real persisted Task rows under a new/existing project with user override, refreshing board and dashboard, and logging activity.

**CHARTER alignment:** Advances O3 "AI Intake flow working end-to-end" — intake now produces visible, correct work items on the Kanban board, project detail page, and dashboard activity feed.

**Streams:** Two parallel streams (A backend, B frontend) bound by a frozen confirm request/response contract. The classification field on `_IntakeAIOutput`/`IntakeOut` is owned entirely by Stream A and surfaced through the existing `IntakeOut`/`IntakeResult` shape; Stream B reads it as an optional field, so no sequencing dependency is created — both streams build against the contract below. Stream B can stub the new `item_type` field as optional until A lands; integration gate verifies the wired result.

---

### Stream A - Backend: classification, migration, confirm routing, task creation, activity, cache-bust

- Scope (files WRITTEN):
  - `backend/app/services/ai_service.py` (extend `INTAKE_SYSTEM` prompt with project-vs-task classification instructions)
  - `backend/app/api/v1/ai.py` (add `suggested_item_type` to `_IntakeAIOutput`; persist it on `RequestIntake`; rewrite `confirm_intake` routing + task creation + `_log_activity` calls + `_kanban_cache.clear()`)
  - `backend/app/models/models.py` (add `suggested_item_type: Mapped[Optional[str]]` column to `RequestIntake`)
  - `backend/app/schemas/schemas.py` (add `suggested_item_type` to `IntakeOut`; extend `IntakeConfirmRequest` with the new optional routing fields; add a `ConfirmIntakeResult` response wrapper — see Exports)
  - `backend/app/main.py` (add idempotent `ALTER TABLE request_intake ADD COLUMN IF NOT EXISTS suggested_item_type TEXT` to the `run_migrations()` startup block)
  - `backend/migrations/002_intake_item_type.sql` (numbered idempotent migration mirroring the startup ALTER)
  - `backend/tests/test_regression.py` (add intake-confirm route + negative-path tests; live-backend httpx style matching existing file)

- Excluded: all `frontend/**`, `backend/app/api/v1/projects.py` (reuse its `_log_activity` and `_kanban_cache` via import; do NOT edit), `backend/app/api/v1/tasks.py`, `backend/app/api/v1/kanban.py`.

- Exports (interface contract — FROZEN):

  Endpoint unchanged: `POST /api/v1/ai/intake/{intake_id}/confirm`, status 201.

  Request body `IntakeConfirmRequest` (extended; `confirmed_priority` stays REQUIRED for human sign-off):
  ```
  {
    "confirmed_priority": "low|medium|high|urgent",   // REQUIRED (unchanged)
    "title": str | null,                              // optional override (unchanged)
    "description": str | null,                        // optional override (unchanged)
    "owner_id": UUID | null,                          // optional (unchanged)
    "team_id": UUID | null,                           // optional (unchanged)
    "item_type": "project" | "task" | null,           // NEW: user-resolved type; null => use intake.suggested_item_type, else "project"
    "target_project_id": UUID | null,                 // NEW: required when item_type=="task" and not creating a new parent
    "new_project_title": str | null                   // NEW: when item_type=="task" and target_project_id is null => create minimal parent project with this title (fallback to intake.generated_title)
  }
  ```
  Omit-vs-null discipline: all three new fields are optional and nullable; absence/null means "no override" (server resolves from `intake.suggested_item_type`). `confirmed_priority` must never be optional.

  New response model `ConfirmIntakeResult` (replaces bare `ProjectOut` so the frontend learns what was created and where to refresh):
  ```
  {
    "item_type": "project" | "task",
    "project": ProjectOut,                  // the project the items live under (new or existing)
    "tasks_created": int,
    "tasks": [TaskOut, ...]                 // the Task rows created (subtasks or the task(s))
  }
  ```

  Resolved confirm routing (complete case enumeration):
  1. **type=project** (resolved): create `Project` (status=intake, priority=`confirmed_priority`, created_by=user) exactly as today, THEN for each non-empty string in `intake.suggested_subtasks` create a real `Task(project_id=project.id, title=subtask, status=ProjectStatus.todo, priority=confirmed_priority, created_by=user)`. Return `item_type="project"`, the project, and the created subtask Tasks.
  2. **type=task + existing project** (`target_project_id` set): load that project (404 if missing); create one `Task` per `suggested_subtasks` entry (or a single Task from `generated_title` if subtasks empty) under it; do NOT create a new project. Return `item_type="task"`, the existing project, the created tasks.
  3. **type=task + new project** (`target_project_id` null): create a minimal parent `Project` (title=`new_project_title` or `intake.generated_title`, status=intake, priority=`confirmed_priority`), then create the task(s) under it.
  4. **AI-misclassified → user override**: `item_type` from the request always wins over `intake.suggested_item_type`. Test sends both classifications and asserts the request value is honoured.
  5. **empty/missing subtasks**: type=project with no subtasks creates project + zero tasks (200-path, `tasks_created=0`); type=task with no subtasks creates exactly one task from `generated_title`.
  6. **intake already confirmed**: keep the existing 409 (`intake.intake_status != IntakeStatus.pending`).
  7. **missing parent when type=task→existing**: `item_type=="task"` with `target_project_id` set but not found => 404 "Target project not found".

  Side effects (all inside the existing try/except, before final commit): set `intake.intake_status=confirmed`, `user_confirmed_priority`, `project_id`, `confirmed_by`, `confirmed_at` (unchanged); call `projects._log_activity(db, project.id, current_user.id, "created")` for a created project and one `tasks._log_activity`-equivalent per created task (entity_type="task"); after commit, `from app.api.v1.projects import _kanban_cache; _kanban_cache.clear()` (matches kanban.py:45-46 pattern). Activity logged with `current_user.id` so it surfaces in both `recent_activity` (`["dashboard"]`) and `my_activity` (`["my-dashboard"]`).

  Prompt change: `INTAKE_SYSTEM` gains a rule producing `suggested_item_type` = exactly "project" or "task" (default "project" when the request describes substantial multi-step work). `_IntakeAIOutput` gains `suggested_item_type: str` with a safe default fallback to "project" on parse.

- Dependency: none (reuses projects.py helpers by import; does not write it).
- Builder: claude

---

### Stream B - Frontend: type/override UI, parent-project picker, dynamic button, correct invalidation

- Scope (files WRITTEN):
  - `frontend/app/(dashboard)/intake/page.tsx` (add item-type toggle defaulting to `result.suggested_item_type`; parent-project picker shown only when type=task; dynamic confirm-button label; correct query invalidation)
  - `frontend/lib/types.ts` (add `suggested_item_type?: "project" | "task"` to `IntakeResult`; add `ConfirmIntakeResult` interface matching Stream A response)
  - `frontend/lib/api.ts` (extend `aiApi.confirmIntake` body typing to allow the new fields — already `Record<string, unknown>`, so add a typed convenience signature/comment; add no new endpoint, reuse `projectsApi.list` for the picker)

- Excluded: all `backend/**`, `frontend/components/kanban/KanbanBoard.tsx` (do NOT edit — fix refresh via invalidation from intake page, not by touching the board query), `frontend/components/dashboard/ActivityFeed.tsx`, `frontend/app/(dashboard)/dashboard/page.tsx`.

- Exports (UI behaviour contract):
  - Item-type selector: two options Project / Task, initialised from `result.suggested_item_type ?? "project"`, user-overridable.
  - When type=task: render a project picker populated from `projectsApi.list({ limit: 200 })`, plus a "New project" option; when "New project" chosen, capture `new_project_title` (prefill `result.generated_title`). When an existing project is chosen, send `target_project_id`.
  - Confirm button label is computed, not hardcoded: `New Project` (type=project), `Add to <projectName>` (task→existing), `Create project + task(s)` (task→new); pending label mirrors. Removes the hardcoded "✓ Create Project" / "Creating project…".
  - `confirmIntake` body now sends: `{ confirmed_priority, item_type, target_project_id?, new_project_title? }` (priority confirmation block stays exactly as the CRITICAL UX comment requires).
  - **Invalidation fix (the bug):** on confirm success, invalidate BOTH `["projects"]` AND `["projects-kanban"]` (board query key from KanbanBoard.tsx:59) AND `["dashboard"]` + `["my-dashboard"]`. Use predicate invalidation `queryClient.invalidateQueries({ predicate: q => ["projects","projects-kanban","dashboard","my-dashboard"].includes(q.queryKey[0] as string) })` so the staleTime-60s board query refetches. Then `router.push("/board")`.

- Dependency: none for build (reads new field as optional). Integration verification depends on Stream A response shape.
- Builder: claude

---

**Shared files:** none. Pairwise-disjoint write sets confirmed — Stream A writes only `backend/**`; Stream B writes only `frontend/**`. `backend/app/api/v1/projects.py` and `KanbanBoard.tsx` are read/imported by their respective neighbours but written by neither (the backend cache + `_log_activity` are imported, not edited; the board refresh is fixed via invalidation key, not by editing the board). No collapse to a sequenced stream required.

**Integration gate (all must hold to merge):**
- Confirm of each of the 3 routes produces visible items: (a) new project appears as an Intake-column card on `/board`; (b) its subtasks appear as Task rows on the project detail page; (c) task→existing adds tasks under the chosen project with no spurious new project; (d) task→new creates one parent project + its task(s).
- After confirm, the board reflects the change without manual reload (frontend predicate invalidation hits `["projects-kanban"]` AND backend `_kanban_cache.clear()` ran) — no `["projects"]` vs `["projects-kanban"]` mismatch remains.
- A `created` activity (and per-task entries) appears in the dashboard activity feed (`recent_activity` and `my_activity`) after confirm.
- Confirm button label correctly reflects the resolved action in all three modes; never reads hardcoded "Create Project" when routing to a task.
- `confirmed_priority` still required (422 if omitted); human-priority block unchanged.
- Backend: `pytest backend/tests/test_regression.py` green against a live local backend on 8001, including the 7 enumerated cases (project, task→existing, task→new, override-wins, empty-subtasks, already-confirmed 409, missing-target-project 404).
- Startup auto-migration ALTER present in `main.py` AND numbered `002_*.sql` exists and is idempotent; cold start does not break sign-in/queries.
- Frontend `npm run build` / typecheck clean; `IntakeResult` and `ConfirmIntakeResult` types match the backend response.

**Deferred to next Burst:**
- Per-subtask assignee/due-date extraction and editing in the intake UI (subtasks are created as plain titles this burst).
- AI-suggested target project ("AI may suggest one") beyond surfacing `suggested_item_type` — auto-recommending a specific existing project to attach a task to is deferred; the picker is user-driven this burst.
- Bulk re-classification or editing of an already-confirmed intake.
- vitest frontend specs (none exist today; establishing the frontend test harness is out of scope).

### Critical Files for Implementation
- backend/app/api/v1/ai.py
- backend/app/schemas/schemas.py
- backend/app/main.py
- frontend/app/(dashboard)/intake/page.tsx
- frontend/lib/types.ts
