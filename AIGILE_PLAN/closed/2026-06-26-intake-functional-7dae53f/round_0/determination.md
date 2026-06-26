# Round 0 determination — intake-functional

Orchestrator decision: ABSORB ALL. One round-1 re-plan.

| ID | Sev | Disposition | Resolution |
|----|-----|-------------|------------|
| H1 | HIGH | ABSORB-PLAN | confirm_intake must use `require_writer` (matching create_project). When `item_type=="task"` with `target_project_id`, load the project and gate with `_can_edit_project(project, user)` (reuse from projects.py) → 403 if not permitted, 404 if not found. |
| H2 | HIGH | ABSORB-PLAN | Fix test base URL to 8001 (test_regression.py:13 currently 8002). Confirm-route tests seed `pending` RequestIntake rows directly via DB insert / a fixture with fixed subtasks + suggested_item_type, NOT via the live `/ai/intake` AI call. Document the seeding approach in the test deliverable. |
| H3 | HIGH | ABSORB-PLAN | After creating tasks and committing, reload them with `selectinload(Task.assignee)` (and project if TaskOut needs it) before serializing, mirroring the existing project reload at ai.py:214. Specify the exact reload query in Exports. |
| M1 | MED | ABSORB-GATE | Integration gate: Stream A + Stream B merge together (or A before B); never ship frontend alone. Add explicit gate clause. |
| M2 | MED | ABSORB-PLAN | `_IntakeAIOutput.suggested_item_type: Literal["project","task"] = "project"` (or validator coercing unknown→"project"). confirm resolves null/legacy DB rows → "project". Add acceptance cases: AI returns invalid/missing type; legacy intake row with null suggested_item_type. |
| M3 | MED | ABSORB-PLAN | Frontend: reset item_type/target_project_id/new_project_title on new analysis and on discard. Confirm button disabled when item_type=="task" AND mode==existing AND no project selected. Add to UI behaviour contract + acceptance. |
| M4 | MED | ABSORB-PLAN | Define override survival: task→new parent project applies title (new_project_title or generated_title), description (generated_description), priority (confirmed_priority); owner_id/team_id only if provided in request; tags/due_date/next_action from intake (same as project route). State explicitly per route. |

Rejected alternatives: none. All findings accepted as legitimate.
