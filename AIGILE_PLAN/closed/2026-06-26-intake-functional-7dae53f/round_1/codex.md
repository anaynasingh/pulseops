Codex thread ID: 019f02e4-d6f6-7d93-8eef-7bea33b6ba89 (resumed, turn 019f02ee-dc5c-7a92-b5d1-6088320976a0)

**Prior Findings — all adequately resolved**
- H1 auth: resolved. require_writer + _can_edit_project for task-to-existing covers arbitrary-attach risk.
- H2 tests: resolved in intent. Port corrected to 8001; direct DB-seeded intakes remove live AI variance.
- H3 serialization: resolved. Reloading created tasks with selectinload(assignee, project) addresses async lazy-load failures.
- M1 merge order: resolved. Merge-together gate covers old-backend/new-frontend silent misrouting.
- M2 AI validation: mostly resolved, caveat below.
- M3 frontend state: resolved. Reset + gating cover stale selection and missing target.
- M4 parent override: resolved. Task-to-new parent field survival now explicit.

**New Findings**
- Medium (N1): M2 validator wording may miss "missing" values. `suggested_item_type: Literal["project","task"] = "project"` handles OMITTED fields via the default; a before-validator handles bad PROVIDED values. In Pydantic v2, field validators do not necessarily run for missing defaults. Not a blocker (default covers missing), but acceptance should not assume the validator itself covers that path.
- Medium (N2): Task activity action naming ambiguous. Existing task creation uses action `"task_created"` (tasks.py:109); the plan's "_log_activity-equivalent" / "created" wording could diverge, producing inconsistent feed labels or brittle tests. Fix the expected task action string.
- Medium (N3): Direct DB seeding (test_regression.py) introduces cleanup/isolation risk. Suite runs against a persistent live backend; repeated runs could pollute project/task lists and make "no spurious new project" assertions flaky unless seeded entities are isolated/cleaned up or use unique markers.
- Low (N4): Frontend picker load path underspecified for loading/error states. If projectsApi.list errors or has not loaded, "existing vs new project" state can be ambiguous unless implementation defines it.

Disposition (Orchestrator): all 4 carried as BUILD-NOTES (implementation guidance), not a further re-plan round.
