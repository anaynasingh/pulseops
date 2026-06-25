# AIGILE_HISTORY.md

Full Burst archive. Append-only. Used for retrospectives and pattern mining.
AIGILE_STATUS.md keeps the rolling last 5 for quick context.
This file keeps everything.

<!-- Entry format:

### [YYYY-MM-DD] Burst: <name>

**Built:** <what was built>
**Verify:** PASS | FAIL
**Steer:** <decision>
**Learnings:** <optional - non-obvious insights, corrections promoted, friction encountered>

-->

### [2026-06-25] Burst: dashboard-complete-gap

**Built:** Fixed the dashboard task-completion layout gap. Completing a task left an empty slot for ~10s because cards were styled `opacity-0 scale-95` (still in layout flow) and only vacated when the 600ms-delayed refetch returned. Reworked `MyTaskSplit` and `MyTasksList` to drive removal off local state via framer-motion `AnimatePresence` with a height-collapse exit, so siblings reflow immediately. Added a `doneIds`/`removedIds` 300ms beat so the completion checkmark shows before the card flies out.
**Verify:** PASS — `tsc --noEmit` clean, `next build` clean. NOT browser-verified.
**Steer:** Shipped to prod (P33-AI master) via PR #2, squash-merged as b67f6dd. Out-of-cycle hotfix: focused branch cherry-picked off prod/master, not the standard dev->main flow.
**Gemini:** 2 rounds, all resolved. R1 (MEDIUM x2): `last:mb-0` margin-snap on exiting `:last-child`; `AnimatePresence` unmounted on empty list, cutting the last card's exit. R2 (MEDIUM x1): completion animation skipped because `visible` filtered on `doneIds` in the same render — fixed by decoupling visual-done from layout-removal. Codex challenge skipped (Orchestrator requested Gemini only).
**Learnings:** (1) Backend tests had never actually run — no Python toolchain on this machine; the shipped reminder test mocks failed under py3.12. (2) Shipping via a branch off prod/master left dev behind with the inferior pre-Gemini version; had to back-sync. (3) Local `prod/master` tracking ref was stale — always `git fetch prod` before reasoning about divergence or checking files out of a remote ref. See PENDING entries in AIGILE_CORRECTIONS.md.
