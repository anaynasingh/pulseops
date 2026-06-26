# Codex plan challenge — round 0

Thread: 019f034a-86ba-7591-98b8-ba675fa45404

**Findings**

- Medium: Route 3’s new-parent `Project(...)` path has separate owner wiring at ai.py:256, but the enumerated tests only prove explicit `owner_id` override/null behavior on the Route 1 project path. A bug that fixes Route 1 but leaves Route 3 on `payload.owner_id` or mishandles explicit `null` there could pass the listed acceptance set.

- Medium: The omit-vs-null contract for `assigned_to` is not fully covered. The plan tests omitted assignee and `assigned_to=other`, but not explicit `assigned_to: null`. That is the exact case most likely to regress if implementation uses `payload.assigned_to or current_user.id` instead of `model_fields_set`. Touches schemas.py:345 and the task creation loop at ai.py:274.

- Low: The Route 2 carve-out says not to mutate an existing project owner, which is correct, but the test set appears to check owner unchanged only for omitted `owner_id`. A `target_project_id + owner_id` request should be explicitly accounted for in acceptance criteria so accidental mutation of the fetched project is caught.

- Low: The integration gate hits a live server via BASE = http://localhost:8001/api/v1. Pytest result only proves the behavior of whatever backend is currently running; stale-server false positives remain possible unless the run is tied to the updated code.

**Direct Answers**

- model_fields_set reasoning is correct for Pydantic v2 with Optional[UUID] = None. Verified local Pydantic 2.13.4: omitted fields absent; explicit null fields present.
- No missed confirm_intake creation route. Route 1 = project + subtasks, Route 2 = tasks under existing project, Route 3 = parent project + tasks. Legacy null classification resolves into Route 1.
- Defaulting owner_id/assigned_to to authenticated current_user.id introduces no FK risk (current_user is a valid DB user).
- Existing-project carve-out is correct: new Route 2 tasks default to the confirming caller, not the project owner.
