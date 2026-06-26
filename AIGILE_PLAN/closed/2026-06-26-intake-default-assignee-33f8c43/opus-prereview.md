# Opus self-review — intake-default-assignee (round 0)

Diff reviewed: 33f8c43..HEAD (ai.py, schemas.py, test_regression.py).

## Findings

No Critical or High findings.

| Sev | file:line | Finding |
|-----|-----------|---------|
| Low | ai.py:223-230 | `resolved_owner_id` is computed unconditionally but is unused on the Route 2 (existing-project) path. Harmless (no side effect, no DB write) and keeps the resolution logic in one place; acceptable. |
| Low | test_regression.py (test_task_to_existing_project_defaults_assignee_owner_unchanged) | Sends a fake `owner_id` UUID that is not a real user. Safe today because Route 2 never writes the project owner, so no FK is exercised. If a future change adds owner_id validation on confirm, this test would need a real id. Documents the carve-out intent well. |
| Info | test_regression.py (owner-unchanged test) | `original_owner` is captured from the live POST /projects/ response rather than assumed, so the assertion holds whether create_project defaults owner to creator or leaves it null. Robust. |

## Verified manually (no DB needed)
- Pydantic 2.13.4 model_fields_set contract: omitted field absent from set; explicit null present with value None; explicit UUID preserved. Confirmed via isolated script.
- Both project constructors (Route 1 + Route 3) now use resolved_owner_id; task loop uses resolved_assignee_id; Route 2 existing project owner untouched.
- schema + ai router modules import cleanly; all three files py_compile clean.

## Disposition
No Critical/High to absorb before Codex. Two Low findings are documented design choices, surfaced as informational. Proceed to Step 7 (Codex adversarial review).
