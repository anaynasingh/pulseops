# AIGILE_CORRECTIONS.md

<!-- Record of real mistakes made in this repo and the correction the     -->
<!-- Orchestrator gave. Read on session start alongside CLAUDE.md so past -->
<!-- mistakes are not repeated.                                           -->
<!--                                                                     -->
<!-- Format: - [YYYY-MM-DD] Short rule.                                    -->
<!--                        Builder: <claude|codex|mixed|n/a>.            -->
<!--                        Why: <what went wrong>.                       -->
<!--                        How to apply: <when/where this kicks in>.     -->
<!-- Builder values: claude, codex, mixed (multi-stream burst with both), -->
<!-- or n/a (process/orchestration correction not tied to a builder).     -->
<!-- `legacy` is reserved for retrospective use only: mark a PENDING entry-->
<!-- `Builder: legacy` if it surfaces at retrospective with no Builder    -->
<!-- line. `legacy` is excluded from per-builder routing analytics.       -->
<!--                                                                     -->
<!-- Every entry header MUST begin with `- ` or `PENDING:`. Bare          -->
<!-- `[YYYY-MM-DD]` headers are silently dropped by corrections_parser.   -->
<!--                                                                     -->
<!-- Never pre-populate. Entries earn their place through real errors.    -->
<!-- When promoting a correction from repo-specific to global, copy the   -->
<!-- entry to ~/.claude/aigile-canonical/global/AIGILE_CORRECTIONS.md -->
<!-- and note the promotion date here.                                    -->
<!--                                                                     -->
<!-- When an entry is superseded by a structural fix, move it to         -->
<!-- AIGILE_CORRECTIONS_ARCHIVE.md (create alongside this file) and add  -->
<!-- an **Absorbed:** line explaining the structural fix. Archive keeps   -->
<!-- the audit trail without loading stale rules into session context.   -->

- [2026-06-25] Tests called "passing" must actually be executed before a burst ships.
         Builder: claude.
         Why: day-view-timeblock shipped backend/tests/test_reminders.py as green, but this machine had no Python toolchain (no pip/venv) so the suite had never run. Once run under py3.12 all 6 cases errored — the AsyncMock chain made scalars() return a coroutine. Deploy success had been used as a proxy for tests passing.
         How to apply: at /ag-probe, never claim tests pass without running them. If no runner exists, install one or flag the suite explicitly as UNEXECUTED rather than reporting PASS.

- [2026-06-25] After a direct-to-prod merge that bypasses dev, back-sync dev immediately.
         Builder: n/a.
         Why: the dashboard fix shipped via a branch cherry-picked off prod/master and squash-merged to prod; dev was left holding the inferior pre-Gemini version of the same two files until manually back-synced.
         How to apply: whenever a hotfix lands on prod/master without going through dev, sync the changed files (or merge) back into dev before starting any new work, so dev never trails prod.

- [2026-06-25] When an LLM gets a truncated list as "the user's data", make the truncation lossless for the questions asked.
         Builder: claude.
         Why: assistant-task-prompts fed /ai/chat a due-date-sorted, 15-item slice of the user's tasks and told the model to answer priority/overdue questions from it. Codex flagged (R1) counts computed on the truncated slice misstated the workload, and (R2) priority work could be hidden behind the due-date slice. Two rounds on the same truncation mechanism.
         How to apply: when building LLM context from a capped query, compute aggregate counts over the FULL set, order by relevance to the prompt intent (not one arbitrary key), use a cap generous enough that realistic volumes are never cut, and label any truncation. Ideally make retrieval intent-aware (priority vs due-date vs blocked) rather than one fixed slice.

- [2026-06-25] git fetch the prod remote before reasoning about branch divergence.
         Builder: n/a.
         Why: local prod/master tracking ref was stale at e774a64; `git log dev..prod/master` showed empty and `git checkout prod/master -- <file>` pulled pre-fix content. `git ls-remote` shows the true remote tip but does not update local tracking refs.
         How to apply: run `git fetch prod` before any divergence comparison or `git checkout <remote>/<branch> -- <file>`.

- [2026-06-26] Any status-gated "create/confirm once" endpoint needs an atomic claim, not check-then-create.
         Builder: claude.
         Why: intake-functional confirm_intake read intake_status==pending then ran the project/task create fanout. Two concurrent confirms both passed the check and both created work (duplicate projects/tasks, orphaned rows). The "already confirmed -> 409" plan case only covered sequential re-confirm, not the race. Codex C1 (HIGH).
         How to apply: when an endpoint transitions a row through a one-shot status gate (pending->confirmed, draft->published, etc.) and then creates dependent rows, claim the row atomically in the same transaction: SELECT ... FOR UPDATE (or a conditional UPDATE ... WHERE status='pending' RETURNING). The loser of the race must see the new status and return 409, not re-run the side effects. At /ag-plan, scan create/confirm endpoints for check-then-act and require the atomic claim in the plan, not as a probe fix.

- [2026-06-26] Live-backend tests that touch real/shared rows must isolate via disposable marked entities + try/finally teardown; never mutate or delete a real fixture.
         Builder: claude.
         Why: intake-functional test_regression.py runs against a persistent shared dev backend. _cleanup_async deleted the project at intake.project_id unconditionally; for the task->existing test that id was the real anayna_project, so teardown would cascade-delete real data. Separately, task cleanup ran only after assertions, so an assertion failure leaked real rows (Codex C2/N3, opus self-review).
         How to apply: for live-backend (non-fixture-DB) suites, create disposable entities the test owns (unique "_reg"-style title marker), wrap mutations in try/finally so teardown runs even on assertion failure, gate any DELETE on the test marker so a real fixture can never be removed, and never assert "no spurious X" against shared global lists without marker-scoped filtering.

PENDING: [2026-06-26] When ag-init preflight hard-blocks with a parser-contract / header-drift notice that never clears, hand-sync the AIGILE_CORRECTIONS.md header to the canonical template.
         Builder: n/a.
         Why: ag-init's header drift detector flags a missing parser-contract notice, but migrate_corrections_header no-ops when the Builder marker is already present, so drift never clears and .aigile/last-init is never written. Preflight then hard-blocks every burst at session start (the intake-default-assignee plan was blocked this way).
         How to apply: if preflight loops on a CORRECTIONS header-drift / parser-contract notice, manually update the AIGILE_CORRECTIONS.md header block to match the canonical template so the detector clears and last-init is written. Root cause is an upstream canonical bug — file /ag-upstream to fix migrate_corrections_header; remove this entry once the canonical fix lands.
