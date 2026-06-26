# Iteration log: intake-functional

## Round 0 (planned 2026-06-26)

**Plan written:** 2026-06-26
**Plan agent model:** opus
**Scope decision:** Option C (AI classifies project-vs-task, user override + parent-project picker).
**Codex challenge:** done. Thread 019f02e4-d6f6-7d93-8eef-7bea33b6ba89. Findings: 3 HIGH, 4 MED.

## Round 1 (re-planned 2026-06-26)

**Trigger:** Orchestrator ABSORB ALL of round 0 Codex findings.
**Plan agent model:** opus
**Changes:** H1 (require_writer + _can_edit_project + 403 case), H2 (test port 8001 + DB-seeded intakes), H3 (selectinload before serialize), M1 (merge-together gate), M2 (Literal item_type + null/legacy coercion), M3 (frontend state reset + button gating), M4 (parent-project override survival).
**Preservation verdict:** ALL AUTHORISED (round_1/preservation-check.md).
**Codex re-challenge:** done (round 1, resumed). All 7 prior findings confirmed resolved. 4 new (3 MED, 1 LOW) carried as BUILD-NOTES, not re-planned. See round_1/codex.md.

## Approved 2026-06-26

**Round approved:** 1
**Burst base:** 7dae53f2de15f721913344c3df07b66bd295ddaf
**Approved by:** Orchestrator

## Build + probe (2026-06-26)

**Build commit:** b4b0afc (Stream A backend + Stream B frontend, single agent).
**Static verification:** app imports (no circular import ai→projects/tasks), `_IntakeAIOutput` validator coercion verified, IntakeConfirmRequest requires priority, ConfirmIntakeResult forward refs resolve, `tsc --noEmit` clean, 47 tests collect (13 new TestIntakeConfirm).
**Live verification (pytest/UI/API):** BLOCKED in this environment — no backend/.env, no Supabase, no live backend on 8001. Must run against a live backend (local with .env, or dev deploy).
**Scope:** 10 changed files == declared scope. No violations.

### Probe round 0 (self-review fix)

**Authorised scope:** backend/tests/test_regression.py ONLY (Stream A declared scope).
**Self-review (opus, opus-prereview.md):** no Critical/High. Absorbed one safety bug:
`_cleanup_async` deleted `intake.project_id`'s project unconditionally — for the
task→existing test that is the REAL anayna_project, so teardown would cascade-delete
real data. Fix: guard project deletion behind the `_reg` title marker; delete the
existing-project test's added tasks via API.
**Preservation:** both hunks confined to test_regression.py (cleanup guard + in-test
task cleanup). AUTHORISED — within Stream A test scope, no production code touched.

### Probe round 1 (Codex adversarial — review-mqunqa66-vawfmc)

**Verdict:** needs-attention. Steer decision: FIX BOTH.

**Codex critique:**
- C1 [HIGH] ai.py:203-208 — TOCTOU race: concurrent confirms for one intake both see
  `pending` and both run the create fanout → duplicate projects/tasks, orphaned work.
  Classified DISCOVERY (concurrency not in plan case set). Single finding, not
  predominantly-discovery round.
- C2 [MED] test_regression.py — existing-project test mutates real anayna_project; task
  cleanup runs only after assertions, so an assertion failure leaves real tasks behind.

**Class-fix scan (C1, structural):** grep for `intake_status != pending` then-create
sites — only confirm_intake (ai.py:207). No sibling endpoints share the pattern. Class
== single instance.

**Authorised scope:**
- backend/app/api/v1/ai.py — confirm_intake intake SELECT gains `.with_for_update()`
  (atomic row claim; concurrent confirms serialize, loser sees `confirmed` → 409). No
  other logic changed.
- backend/tests/test_regression.py — test_task_to_existing_project creates a disposable
  `_reg_existing_parent` project (owned by test user, editable) instead of mutating
  anayna_project; remove the now-unneeded manual task cleanup. Add a concurrency test
  (two threads confirm one intake → exactly one 201, one 409).

**Applied:**
- ai.py: intake SELECT now `.with_for_update()`; added explanatory comment. No other
  logic touched (verified by diff — single hunk in the claim region).
- test_regression.py: test_task_to_existing_project creates `_reg_existing_parent` via
  POST /projects, wraps assertions in try/finally with delete_project teardown; dropped
  the anayna_project fixture param + manual per-task cleanup. Added
  test_concurrent_confirms_create_one_set (48 tests collect, was 47).

**Preservation verdict:** AUTHORISED. Code hunks confined to ai.py (C1 claim) and
test_regression.py (C2 + concurrency test). AIGILE_STATUS.md + manifest json are process
artefacts (steering phase + deferred-review note), not burst code. No unauthorised
additions/deletions/modifications. No production logic outside the atomic-claim line.
**Static verification:** app imports clean with `.with_for_update()`; py_compile OK.
**Live pytest:** still pending Orchestrator backend bring-up (option a).

### Probe round 2 (Codex confirmation — review-mquo3tdl-a0821i)

**Verdict:** needs-attention. C1 (race) and C2 (test pollution) CONFIRMED RESOLVED.
**New finding C3 [MED]** ai.py task→existing route doesn't recalc Project.progress_pct.
Verified pre-existing + app-wide: tasks.py create_task (POST /tasks) has the identical
gap — progress only recalcs on task PATCH (update_task), never on create/delete. Intake
route is consistent with the established create_task contract.
**Steer decision:** DEFER (recommended). Fixing properly = extract shared recalc and
apply to create_task/delete_task/intake — that is tasks.py (excluded from this burst's
scope) and a separate "progress_pct derived-state consistency" burst. Recorded in
AIGILE_PLAN/DEFERRED.md [2026-06-26].
**No further fix round** — C3 deferred, not patched. Round-economics: not a repeat
defect class; a discovery finding about pre-existing behaviour.
