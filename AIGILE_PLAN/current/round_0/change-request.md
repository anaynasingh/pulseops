# Round 0 → Round 1 change-request whitelist — intake-functional

## Modifications (to existing plan content; preserve everything else verbatim)

1. **Stream A confirm_intake auth (H1):** Change dependency from `get_current_user` to `require_writer`. Add to the route enumeration: when `item_type=="task"` and `target_project_id` is set, load the target project; 404 if not found, 403 if `_can_edit_project(project, current_user)` is False. Import `_can_edit_project` from projects.py (read-only reuse, not edited). Add case 8 (403 unauthorized target) to the case list and tests.

2. **Stream A test determinism (H2):** In the `backend/tests/test_regression.py` scope note, specify: fix BASE_URL to port 8001; confirm-route tests seed `pending` RequestIntake rows directly (DB insert or fixture) with fixed `suggested_subtasks` and `suggested_item_type`, not via the live `/ai/intake` endpoint.

3. **Stream A serialization (H3):** In Exports, specify that created Task rows are reloaded with `selectinload(Task.assignee)` (and `Task.project` if `TaskOut` requires it) after commit, before building `ConfirmIntakeResult.tasks` — mirroring the existing project reload at ai.py:214. No lazy relationship access during Pydantic serialization.

4. **Stream A AI classification validation (M2):** `_IntakeAIOutput.suggested_item_type` typed as `Literal["project","task"]` with default/validator coercing unknown or missing → "project". `confirm_intake` resolves a null/legacy `intake.suggested_item_type` → "project". Add acceptance cases: AI returns invalid/missing type (coerced); legacy intake row with null classification (treated as project).

5. **Stream A parent-project override semantics (M4):** In route 2 (task→existing) and route 3 (task→new), state explicitly which fields apply. task→new parent: title=`new_project_title or intake.generated_title`, description=`intake.generated_description`, priority=`confirmed_priority`, owner_id/team_id only if provided, tags/due_date/next_action from intake (same as the project route at ai.py:191-201). task→existing: no project fields mutated.

6. **Stream B frontend state + gating (M3):** Add to UI behaviour contract: reset item_type / target_project_id / new_project_title on new analysis and on discard. Confirm button disabled when item_type=="task" AND existing-project mode AND no project selected. Add matching acceptance criteria.

7. **Integration gate (M1):** Add clause: Stream A and Stream B merge together (or A before B); the frontend is never shipped against the old backend. Add the new auth case (403) and the AI-classification edge cases to the backend test gate.

## Additions
- New backend test cases: 403 unauthorized target project (H1); invalid/missing AI item_type coercion + legacy null classification (M2).

## Deletions
- None.

## Cascading consequences
- No Scope files dropped. `backend/app/api/v1/projects.py` remains read-only/imported (now also imports `_can_edit_project`, already in that file) — still NOT written by Stream A. No new shared writers introduced; write sets remain disjoint (backend-only vs frontend-only).
