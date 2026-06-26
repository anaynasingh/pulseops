# Opus self-review — intake-functional burst

Pre-reviewer: opus (inherit). Diff: 7dae53f..b4b0afc (backend + frontend).

**No Critical/High defects.**

## Absorbed before Codex (Step 7)
- **Test cleanup cascade-delete hazard (rated Low by reviewer; treated as safety bug)** — `tests/test_regression.py` `_cleanup_async` deletes the project at `intake.project_id` unconditionally. For `test_task_to_existing_project`, that id is the real `anayna_project`, so teardown would cascade-delete a real project + tasks from the shared dev DB. Fix: only delete projects whose title starts with the `_reg` test marker (never an existing fixture project), and have the existing-project test delete the tasks it created via the API.

## Surfaced (informational — accepted/deferred)
- Low — `ai.py:323` `tasks_created=len(tasks_out)` derives count from the reload query rather than `len(created_tasks)`; values always equal. Accept.
- Low — task/project titles not length-clamped to String(500); pre-existing exposure on the project route, now also reachable via task route. Accept (parity with existing behaviour).
- Medium — frontend stale `targetProjectId` if the project list changes after selection; backend 404-validates and reset paths cover the common cases. Low likelihood. Accept/defer.
- Low — confirm invalidation does not touch `["project", id]` / `["tasks", ...]`; mitigated by `router.push("/board")`. Accept (by design).

## Verified non-issues
- selectinload eager-loads assignee/project before serialization (no async lazy-load trap).
- db.flush() before task.id used for activity logging; before project.id used.
- Literal + mode="before" validator coerces bad AI values; missing falls to default.
- Activity helper signatures match imports; require_writer + _can_edit_project → 403/404 correct.
- ConfirmIntakeResult (Pydantic) matches TS interface field-for-field; IntakeOut/IntakeResult both gain suggested_item_type.
- Single commit after all inserts/flushes; read-only reloads after.
