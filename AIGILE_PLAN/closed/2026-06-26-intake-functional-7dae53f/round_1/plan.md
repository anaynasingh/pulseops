## Burst Plan
**Goal:** Make AI Intake confirm fully functional by classifying intake as project-vs-task, routing the confirm to create real persisted Task rows under a new/existing project with user override, refreshing board and dashboard, and logging activity.

**CHARTER alignment:** Advances O3 "AI Intake flow working end-to-end" — intake now produces visible, correct work items on the Kanban board, project detail page, and dashboard activity feed.

**Streams:** Two parallel streams (A backend, B frontend) bound by a frozen confirm request/response contract. The classification field on `_IntakeAIOutput`/`IntakeOut` is owned entirely by Stream A and surfaced through the existing `IntakeOut`/`IntakeResult` shape; Stream B reads it as an optional field, so no sequencing dependency is created — both streams build against the contract below. Stream B can stub the new `item_type` field as optional until A lands; integration gate verifies the wired result. The streams build in parallel but MUST be integrated together (or A before B) — never ship the frontend against the old backend (see Integration gate).

---

### Stream A - Backend: classification, migration, confirm routing, task creation, activity, cache-bust

- Scope (files WRITTEN):
  - `backend/app/services/ai_service.py` (extend `INTAKE_SYSTEM` prompt with project-vs-task classification instructions)
  - `backend/app/api/v1/ai.py` (add `suggested_item_type` to `_IntakeAIOutput` as a `Literal` with coercion; persist it on `RequestIntake`; rewrite `confirm_intake` routing + task creation + `_log_activity` calls + `_kanban_cache.clear()`; switch the confirm dependency to `require_writer`; import `_can_edit_project` from projects.py for the task→existing authorization gate)
  - `backend/app/models/models.py` (add `suggested_item_type: Mapped[Optional[str]]` column to `RequestIntake`)
  - `backend/app/schemas/schemas.py` (add `suggested_item_type` to `IntakeOut`; extend `IntakeConfirmRequest` with the new optional routing fields; add a `ConfirmIntakeResult` response wrapper — see Exports)
  - `backend/app/main.py` (add idempotent `ALTER TABLE request_intake ADD COLUMN IF NOT EXISTS suggested_item_type TEXT` to the `run_migrations()` startup block)
  - `backend/migrations/002_intake_item_type.sql` (numbered idempotent migration mirroring the startup ALTER)
  - `backend/tests/test_regression.py` (fix BASE_URL to port 8001; add intake-confirm route + negative-path tests; deterministic DB-seeded `pending` intakes — see seeding note below; live-backend httpx style matching existing file)

- Excluded: all `frontend/**`, `backend/app/api/v1/projects.py` (reuse its `_log_activity`, `_kanban_cache`, and `_can_edit_project` via import; do NOT edit), `backend/app/api/v1/tasks.py`, `backend/app/api/v1/kanban.py`.

- Exports (interface contract — FROZEN):

  Endpoint unchanged: `POST /api/v1/ai/intake/{intake_id}/confirm`, status 201. Dependency changed from `get_current_user` to `require_writer` (blocks viewer-role accounts from confirming, matching `create_project` at projects.py:162).

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
  Omit-vs-null discipline: all three new fields are optional and nullable; absence/null means "no override" (server resolves from `intake.suggested_item_type`, itself coerced to "project" when null/legacy). `confirmed_priority` must never be optional.

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
  1. **type=project** (resolved): create `Project` (status=intake, priority=`confirmed_priority`, created_by=user) exactly as today — same field list as ai.py:191-201 (title, description, owner_id, team_id, tags, due_date, next_action) — THEN for each non-empty string in `intake.suggested_subtasks` create a real `Task(project_id=project.id, title=subtask, status=ProjectStatus.todo, priority=confirmed_priority, created_by=user)`. Return `item_type="project"`, the project, and the created subtask Tasks.
  2. **type=task + existing project** (`target_project_id` set): load that project (404 if missing); gate with `_can_edit_project(project, current_user)` → 403 if not permitted. No project fields are mutated. Create one `Task` per `suggested_subtasks` entry (or a single Task from `generated_title` if subtasks empty) under it; do NOT create a new project. Return `item_type="task"`, the existing project, the created tasks.
  3. **type=task + new project** (`target_project_id` null): create a minimal parent `Project` with explicit override survival — title=`new_project_title or intake.generated_title`, description=`intake.generated_description`, status=intake, priority=`confirmed_priority`, owner_id/team_id only if provided in the request, tags=`intake.suggested_tags`, due_date=`intake.suggested_due_date`, next_action from `intake.suggested_next_steps` (same source fields as the project route at ai.py:191-201) — then create the task(s) under it.
  4. **AI-misclassified → user override**: `item_type` from the request always wins over `intake.suggested_item_type`. Test sends both classifications and asserts the request value is honoured.
  5. **empty/missing subtasks**: type=project with no subtasks creates project + zero tasks (201-path, `tasks_created=0`); type=task with no subtasks creates exactly one task from `generated_title`.
  6. **intake already confirmed**: keep the existing 409 (`intake.intake_status != IntakeStatus.pending`).
  7. **missing parent when type=task→existing**: `item_type=="task"` with `target_project_id` set but not found => 404 "Target project not found".
  8. **unauthorized target when type=task→existing**: `item_type=="task"` with `target_project_id` set, project found, but `_can_edit_project(project, current_user)` is False => 403 (reuses the owner/creator/admin control from projects.py:16-22).

  Side effects (all inside the existing try/except, before final commit): set `intake.intake_status=confirmed`, `user_confirmed_priority`, `project_id`, `confirmed_by`, `confirmed_at` (unchanged); call `projects._log_activity(db, project.id, current_user.id, "created")` for a created project and one `_log_activity`-equivalent per created task (entity_type="task"); after commit, `from app.api.v1.projects import _kanban_cache; _kanban_cache.clear()` (matches kanban.py:45-46 pattern). Activity logged with `current_user.id` so it surfaces in both `recent_activity` (`["dashboard"]`) and `my_activity` (`["my-dashboard"]`).

  Serialization discipline (H3): after commit, reload the created Task rows with `selectinload(Task.assignee)` (and `selectinload(Task.project)` since `TaskOut` carries an optional `project: ProjectMini` field, schemas.py:230) before building `ConfirmIntakeResult.tasks` — mirroring the existing project reload at ai.py:214-225. No lazy relationship access during Pydantic serialization. The parent `ProjectOut` continues to be reloaded with its existing relationship options.

  Prompt + classification change: `INTAKE_SYSTEM` gains a rule producing `suggested_item_type` = exactly "project" or "task" (default "project" when the request describes substantial multi-step work). `_IntakeAIOutput` gains `suggested_item_type: Literal["project", "task"] = "project"`, with a validator (e.g. `field_validator(mode="before")`) coercing any unknown/missing value to "project" — because `_schema_hint` (ai_service.py:31-39) emits only field types (not enum literals) and `structured_completion` calls `model_validate` directly with no fallback (ai_service.py:80-81), so an invalid AI value would otherwise raise. `confirm_intake` resolves a null/legacy `intake.suggested_item_type` (rows created before this column existed) → "project".

- Dependency: none (reuses projects.py helpers `_log_activity`, `_kanban_cache`, and `_can_edit_project` by import; does not write it).
- Builder: claude

---

### Stream B - Frontend: type/override UI, parent-project picker, dynamic button, correct invalidation

- Scope (files WRITTEN):
  - `frontend/app/(dashboard)/intake/page.tsx` (add item-type toggle defaulting to `result.suggested_item_type`; parent-project picker shown only when type=task; dynamic confirm-button label; confirm-button gating; routing-state reset on new analysis and discard; correct query invalidation)
  - `frontend/lib/types.ts` (add `suggested_item_type?: "project" | "task"` to `IntakeResult`; add `ConfirmIntakeResult` interface matching Stream A response)
  - `frontend/lib/api.ts` (extend `aiApi.confirmIntake` body typing to allow the new fields — already `Record<string, unknown>`, so add a typed convenience signature/comment; add no new endpoint, reuse `projectsApi.list` for the picker)

- Excluded: all `backend/**`, `frontend/components/kanban/KanbanBoard.tsx` (do NOT edit — fix refresh via invalidation from intake page, not by touching the board query), `frontend/components/dashboard/ActivityFeed.tsx`, `frontend/app/(dashboard)/dashboard/page.tsx`.

- Exports (UI behaviour contract):
  - Item-type selector: two options Project / Task, initialised from `result.suggested_item_type ?? "project"`, user-overridable.
  - When type=task: render a project picker populated from `projectsApi.list({ limit: 200 })`, plus a "New project" option; when "New project" chosen, capture `new_project_title` (prefill `result.generated_title`). When an existing project is chosen, send `target_project_id`.
  - Confirm button label is computed, not hardcoded: `New Project` (type=project), `Add to <projectName>` (task→existing), `Create project + task(s)` (task→new); pending label mirrors. Removes the hardcoded "✓ Create Project" / "Creating project…".
  - **State reset (M3):** reset `item_type`, `target_project_id`, and `new_project_title` to defaults on a new analysis (alongside the existing result/priority reset, page.tsx:22) and on discard (page.tsx:221), so a stale selection never carries across a second analysis.
  - **Confirm-button gating (M3):** in addition to the existing priority-confirmation gate (page.tsx:214), disable the confirm button when `item_type=="task"` AND existing-project mode is selected AND no `target_project_id` is chosen.
  - `confirmIntake` body now sends: `{ confirmed_priority, item_type, target_project_id?, new_project_title? }` (priority confirmation block stays exactly as the CRITICAL UX comment requires).
  - **Invalidation fix (the bug):** on confirm success, invalidate BOTH `["projects"]` AND `["projects-kanban"]` (board query key from KanbanBoard.tsx:59) AND `["dashboard"]` + `["my-dashboard"]`. Use predicate invalidation `queryClient.invalidateQueries({ predicate: q => ["projects","projects-kanban","dashboard","my-dashboard"].includes(q.queryKey[0] as string) })` so the staleTime-60s board query refetches. Then `router.push("/board")`.

- Dependency: none for build (reads new field as optional). Integration verification depends on Stream A response shape, and the frontend MUST NOT be shipped/integrated against the old backend (see Integration gate).
- Builder: claude

---

**Shared files:** none. Pairwise-disjoint write sets confirmed — Stream A writes only `backend/**`; Stream B writes only `frontend/**`. `backend/app/api/v1/projects.py` and `KanbanBoard.tsx` are read/imported by their respective neighbours but written by neither (the backend cache, `_log_activity`, and `_can_edit_project` are imported, not edited; the board refresh is fixed via invalidation key, not by editing the board). No collapse to a sequenced stream required.

**Integration gate (all must hold to merge):**
- **Merge-together clause (M1):** Stream A and Stream B are integrated together (or A before B); the frontend is never shipped against the old backend. A 201 that silently ignores the new routing fields (old backend + new frontend) is a gate failure.
- Confirm of each of the 3 routes produces visible items: (a) new project appears as an Intake-column card on `/board`; (b) its subtasks appear as Task rows on the project detail page; (c) task→existing adds tasks under the chosen project with no spurious new project; (d) task→new creates one parent project + its task(s).
- After confirm, the board reflects the change without manual reload (frontend predicate invalidation hits `["projects-kanban"]` AND backend `_kanban_cache.clear()` ran) — no `["projects"]` vs `["projects-kanban"]` mismatch remains.
- A `created` activity (and per-task entries) appears in the dashboard activity feed (`recent_activity` and `my_activity`) after confirm.
- Confirm button label correctly reflects the resolved action in all three modes; never reads hardcoded "Create Project" when routing to a task. Button is disabled when type=task + existing mode + no project selected.
- `confirmed_priority` still required (422 if omitted); human-priority block unchanged.
- Backend: `pytest backend/tests/test_regression.py` green against a live local backend on **port 8001** (BASE_URL corrected from 8002), including the enumerated cases: project, task→existing, task→new, override-wins, empty-subtasks, already-confirmed 409, missing-target-project 404, **unauthorized-target 403 (H1)**, **invalid/missing AI item_type coerced to project (M2)**, and **legacy intake row with null suggested_item_type treated as project (M2)**. Confirm-route tests seed `pending` `RequestIntake` rows directly via DB insert / a fixture with fixed `suggested_subtasks` and `suggested_item_type` — NOT via the live `/ai/intake` AI call — to remove external AI variance.
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
