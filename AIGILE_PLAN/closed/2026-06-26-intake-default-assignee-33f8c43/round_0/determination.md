# Round 0 determination — intake-default-assignee

Orchestrator approved ("go") with all four Codex findings absorbed. All are additive
test-coverage / gate notes — no design or scope change — so no re-plan round is required;
the test set and integration gate in plan.md are amended in place.

| ID | Sev | Disposition | Action |
|----|-----|-------------|--------|
| C1 | MED | ABSORB-PLAN | Add Route 3 (task->new-parent-project) explicit `owner_id`=other and explicit `owner_id: null` test cases, mirroring the Route 1 project tests. |
| C2 | MED | ABSORB-PLAN | Add explicit `assigned_to: null` test case (distinct from omitted) — asserts model_fields_set contract, catches `payload.assigned_to or current_user.id` regression. |
| C3 | LOW | ABSORB-PLAN | Add Route 2 (existing-project) + explicit `owner_id` test asserting the fetched project's owner_id is NOT mutated. |
| C4 | LOW | ABSORB-GATE | Restart the local backend against the freshly-edited code before running the live suite; add to integration gate so a stale server cannot yield a false PASS. |

## Confirmed (not defects)
- model_fields_set omit-vs-null reasoning correct for Pydantic 2.13.4 (Codex verified live).
- No confirm_intake creation route missed (Route 1 / 2 / 3; legacy null-classification folds into Route 1).
- No FK risk defaulting owner_id/assigned_to to authenticated current_user.id.
- Route 2 carve-out correct: new tasks default to caller, existing project owner untouched.

## Rejected alternatives
- Full frontend UI picker this burst — rejected by Orchestrator (AMBIGUITY 1 -> backend-only; deferred).
- Owner-only / subtasks-unassigned — rejected by Orchestrator (AMBIGUITY 2 -> owner + all subtasks).
