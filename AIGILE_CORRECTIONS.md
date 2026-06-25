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
<!-- Never pre-populate. Entries earn their place through real errors.    -->
<!-- When promoting a correction from repo-specific to global, copy the   -->
<!-- entry to ~/.claude/aigile-canonical/global/AIGILE_CORRECTIONS.md -->
<!-- and note the promotion date here.                                    -->

PENDING: [2026-06-25] Tests called "passing" must actually be executed before a burst ships.
         Builder: claude.
         Why: day-view-timeblock shipped backend/tests/test_reminders.py as green, but this machine had no Python toolchain (no pip/venv) so the suite had never run. Once run under py3.12 all 6 cases errored — the AsyncMock chain made scalars() return a coroutine. Deploy success had been used as a proxy for tests passing.
         How to apply: at /ag-probe, never claim tests pass without running them. If no runner exists, install one or flag the suite explicitly as UNEXECUTED rather than reporting PASS.

PENDING: [2026-06-25] After a direct-to-prod merge that bypasses dev, back-sync dev immediately.
         Builder: n/a.
         Why: the dashboard fix shipped via a branch cherry-picked off prod/master and squash-merged to prod; dev was left holding the inferior pre-Gemini version of the same two files until manually back-synced.
         How to apply: whenever a hotfix lands on prod/master without going through dev, sync the changed files (or merge) back into dev before starting any new work, so dev never trails prod.

PENDING: [2026-06-25] git fetch the prod remote before reasoning about branch divergence.
         Builder: n/a.
         Why: local prod/master tracking ref was stale at e774a64; `git log dev..prod/master` showed empty and `git checkout prod/master -- <file>` pulled pre-fix content. `git ls-remote` shows the true remote tip but does not update local tracking refs.
         How to apply: run `git fetch prod` before any divergence comparison or `git checkout <remote>/<branch> -- <file>`.
