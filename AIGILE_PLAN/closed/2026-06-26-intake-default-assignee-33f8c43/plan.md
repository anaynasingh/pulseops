## Burst Plan

**Goal:** In AI intake confirm, default the new project's `owner_id` and each created task's `assigned_to` to the confirming `current_user` when no assignee/owner is explicitly specified, preserving any explicit override.

**CHARTER alignment:** Objective "Complete backend API — all routers functional with working DB layer (ai, projects, tasks)"; builds directly on the shipped "AI Intake flow working end-to-end" objective and the `intake-functional` capability.

**Streams:** single (backend-only). See AMBIGUITY 1 below for the optional frontend follow-on.

### Key findings (grounded in code)

1. **No migration needed.** `Task.assigned_to` (`models.py:159`, FK `users.id ondelete=SET NULL`, nullable) and `Project.owner_id` (`models.py:125`, same shape) already exist. The deliverable is pure wiring in `confirm_intake`. No ORM change, no numbered migration, no startup auto-migration hook — the CORRECTIONS rule about startup auto-migration does not trigger because there is no schema change.

2. **Current gap in `ai.py confirm_intake`** (`ai.py:185-331`):
   - Project Route 1 (`ai.py:228-239`) and Route 3 new parent (`ai.py:256-267`) set `owner_id=payload.owner_id`. When the UI omits it (it always does today — see finding 5), `payload.owner_id` is `None`, so the project is created **owner-less**.
   - Task creation loop (`ai.py:274-283`) sets no `assigned_to` at all, so every intake task is created **unassigned**.
   - The fix: default both to `current_user.id` when not explicitly provided.

3. **Omit-vs-null contract.** `IntakeConfirmRequest` (`schemas.py:345-355`) has `owner_id: Optional[UUID] = None` but **no** `assigned_to` field. To honor "unless an assignee is otherwise specified" with the model_fields_set pattern, add an explicit `assigned_to: Optional[UUID]` field to `IntakeConfirmRequest`, and resolve using `model_fields_set`:
   - For project owner: `owner = payload.owner_id if "owner_id" in payload.model_fields_set else current_user.id`. This means client omits → creator; client sends `owner_id: null` explicitly → ownerless (respected); client sends a UUID → that user.
   - For task assignee: `assignee = payload.assigned_to if "assigned_to" in payload.model_fields_set else current_user.id`. Same semantics.
   - Apply the same `owner_id` resolution to **both** project-creation sites (Route 1 `ai.py:236` and Route 3 `ai.py:262`). Do NOT set owner/assignee on the Route 2 existing-project path's project (that project already exists and has an owner) — only its new tasks get the assignee default.

4. **Parity check.** Regular `create_task` (`tasks.py:106`) and `create_project` (`projects.py:164`) do NOT auto-assign to creator — they pass through `payload` verbatim (assignee may be null). This burst makes intake *more* helpful than the raw endpoints by defaulting to creator, which matches the stated goal. This is an intentional, goal-driven divergence, not a parity break — note it for the Codex challenge.

5. **Frontend.** `intake/page.tsx` builds the confirm body (`page.tsx:58-72`) with only `confirmed_priority`, `item_type`, and routing fields. There is **no assignee/owner picker** in the intake UI. Because the new backend field is omitted by the existing client, `model_fields_set` will not contain it, so the default-to-creator path fires correctly with zero frontend changes. The frontend needs no change for the core deliverable.

6. **Serialization already supports it.** `ConfirmIntakeResult` returns `ProjectOut` (carries `owner_id` + `owner`) and `TaskOut` (carries `assigned_to` + `assignee`). The reload queries at `ai.py:299-321` already `selectinload(Project.owner)` and `selectinload(Task.assignee)`, so the assigned values serialize without lazy-load errors. No schema/response change beyond the request field.

### Stream A - backend-intake-default-assignment
- Scope (files WRITTEN):
  - `/home/anayna/repos/pulseops/backend/app/schemas/schemas.py` — add `assigned_to: Optional[UUID] = None` to `IntakeConfirmRequest` (after `owner_id`, `schemas.py:350`). Update the routing docstring comment to note owner/assignee default-to-creator semantics.
  - `/home/anayna/repos/pulseops/backend/app/api/v1/ai.py` — in `confirm_intake`: compute `resolved_owner_id` and `resolved_assignee_id` via the `model_fields_set` pattern near `ai.py:218-219`; apply `resolved_owner_id` to the two `Project(...)` constructors (`ai.py:236`, `ai.py:262`); add `assigned_to=resolved_assignee_id` to the `Task(...)` constructor in the loop (`ai.py:274-283`).
  - `/home/anayna/repos/pulseops/backend/tests/test_regression.py` — extend `TestIntakeConfirm` with the case set below, mirroring the seeded-intake + `_reg`-prefix disposable + try/finally cleanup style already in the file (`test_regression.py:406-504`). Resolve the expected creator id via `GET /auth/me`.
- Excluded: `models.py` (no schema change), all `migrations/`, `tasks.py`, `projects.py`, `frontend/**`, `conftest.py`.
- Exports / interface contract:
  - `IntakeConfirmRequest` gains optional `assigned_to: Optional[UUID]`. Backward compatible — existing clients that omit it get default-to-creator behavior; this is the intended new default.
  - Response contract (`ConfirmIntakeResult`) unchanged in shape; values now populated: `project.owner_id` and each `tasks[].assigned_to` default to the caller.
- Dependency: none.
- Builder: claude

**Test case set (negative + positive, all using seeded `_reg_` disposable intakes):**
- Project route (Route 1), no owner specified → `project.owner_id` == caller id (resolve via `/auth/me`).
- Project route (Route 1), explicit `owner_id` = another user → that user (override wins). Use an existing seeded user id, e.g. derive Stephen via existing `stephen_*` fixtures.
- Project route (Route 1), explicit `owner_id: null` sent → `project.owner_id` is null (explicit-null respected, distinct from omit). Confirms the model_fields_set contract.
- Task→new-project (Route 3), no assignee → every `tasks[].assigned_to` == caller; new parent project `owner_id` == caller.
- **[C1] Task→new-project (Route 3), explicit `owner_id` = another user → new parent project `owner_id` == that user (Route 3 owner override, separate constructor from Route 1).**
- **[C1] Task→new-project (Route 3), explicit `owner_id: null` → new parent project `owner_id` is null (Route 3 explicit-null respected).**
- Task→existing-project (Route 2, disposable `_reg` project owned by caller, try/finally delete) → tasks default `assigned_to` == caller; existing project's `owner_id` unchanged.
- **[C3] Task→existing-project (Route 2) with explicit `owner_id` in body → fetched existing project's `owner_id` is NOT mutated (the carve-out: Route 2 never writes the project's owner).**
- Task with explicit `assigned_to` = another user → tasks carry that user; omitted owner on a new parent still defaults to caller.
- **[C2] Explicit `assigned_to: null` sent → created tasks have `assigned_to` null (explicit-null respected, distinct from omit; catches `payload.assigned_to or current_user.id` regression).**
- Multi-subtask project route → project `owner_id` == caller AND all created subtasks `assigned_to` == caller (AMBIGUITY 2 resolved: owner + all subtasks).
- Legacy null-classification path (`item_type=None`) still defaults type to project AND owner to caller.

**Shared files:** none (single stream).

**Integration gate:** **[C4] restart the local backend against the freshly-edited code before running the suite** (a stale server yields a false PASS); then `pytest backend/tests/test_regression.py -k IntakeConfirm` passes against the live local backend (these are live-backend httpx tests, not in-process); existing IntakeConfirm cases still green; new cases green; manual API check via `/docs` that `confirm_intake` now returns populated `owner_id`/`assigned_to`; Codex adversarial review on the diff (flag the intentional divergence from raw create_task parity, finding 4).

**Deferred to next Burst:** Frontend assignee/owner picker in `intake/page.tsx` (explicit in-UI override). Not required for the core deliverable since omission triggers the creator default; deliver only if the Orchestrator wants an in-UI affordance (AMBIGUITY 1).

### AMBIGUITIES for the Orchestrator
- **AMBIGUITY 1 ("unless an assignee is otherwise specified"):** The intake UI has no assignee picker today (`page.tsx`). Two readings: (a) "otherwise specified" is satisfied purely by the backend contract (a future/API client can send `assigned_to`/`owner_id`); the core deliverable is the creator default — backend-only, single stream. (b) The user also wants an in-UI picker now → adds a second frontend stream (`intake/page.tsx` write, plus possibly a users-list fetch via `lib/api.ts`), sequenced after the backend contract lands. Recommend (a) for this burst, defer (b). Confirm before building.
- **AMBIGUITY 2 (subtask assignment scope):** When a *project* with N suggested subtasks is confirmed, should all N subtasks be assigned to the creator, or only the project owner be set and subtasks left unassigned? The goal says "assign the created task/project to the user." Literal reading: both project owner and all task rows → creator. Recommend assigning both (consistent, matches "task/project"). Confirm so the test assertions are correct.

### Critical Files for Implementation
- /home/anayna/repos/pulseops/backend/app/api/v1/ai.py
- /home/anayna/repos/pulseops/backend/app/schemas/schemas.py
- /home/anayna/repos/pulseops/backend/tests/test_regression.py
- /home/anayna/repos/pulseops/backend/app/models/models.py
- /home/anayna/repos/pulseops/frontend/app/(dashboard)/intake/page.tsx
