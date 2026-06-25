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

### [2026-06-25] Burst: focus-reminder-toggle

**Built:** Two sidebar fixes to the Focus reminders section. (1) Toggle knob could render outside the track — anchored with `left-0.5` and symmetric `translate-x-0`/`translate-x-4` so it stays inside the 32px pill. (2) Renamed the reminder-preview button from "Test" (read like a dev artifact) to "Preview".
**Verify:** PASS — `tsc --noEmit` clean, `next build` clean. NOT browser-verified.
**Steer:** Shipped to prod (P33-AI master) via PR #3, squash-merged as f617541. Same out-of-cycle hotfix flow (branch off prod/master); dev back-synced immediately after merge this time.
**Gemini:** 2 rounds, all resolved. R1 (MEDIUM): overflow-hidden redundant + would clip focus rings; missing `role="switch"`/`aria-checked`; missing focus-visible ring. R2 (MEDIUM): `role="switch"` needs a static `aria-label` or screen readers fall back to the dynamic title. Re-review loop stopped after R2 (diminishing-returns a11y polish on a 1-file change).
**Learnings:** Back-syncing dev right after the prod merge (rather than later) kept the two branches' file content aligned — applying the PENDING correction from the prior burst.

### [2026-06-25] Burst: reminder-modal

**Built:** Two fixes to the Focus Check reminder modal. (1) Renamed "Hourly Focus Check" to "Focus Check" since the interval is configurable (15/30/60/120 min). (2) Killed the ~5s empty-then-populate flash: the task query was gated on `visible`, so the modal opened showing "No incomplete tasks found" until the fetch resolved. Now fetches on mount (modal is mounted once in the dashboard layout) with a 5-min staleTime, and shows a loading skeleton instead of the false empty state.
**Verify:** PASS — `tsc --noEmit` clean, `next build` clean. NOT browser-verified.
**Steer:** Shipped to prod (P33-AI master) via PR #4, squash-merged as 7180bed; dev back-synced after merge.
**Gemini:** 1 round, 1 MEDIUM finding REJECTED with reasoning — it assumed general task mutations invalidate a `["tasks"]` prefix, but this repo invalidates `["my-dashboard"]`/`["projects"]`/etc. and nothing invalidates `["tasks"]`, so the suggested hierarchical key gained nothing. Example of adversarially verifying a reviewer finding against the actual codebase rather than applying blindly.
**Learnings:** Reviewer best-practice suggestions must be checked against the repo's actual conventions — a generically-correct cache-key recommendation was inert here because the invalidation scheme is dashboard-keyed, not tasks-keyed.

### [2026-06-25] Burst: remove-my-tasks

**Built:** Removed the redundant "My Tasks" list from the dashboard (the Overdue/Upcoming `MyTaskSplit` above already covers a user's tasks) and deleted the now-unused `MyTasksList.tsx` (272 lines, zero references). Recent activity now fills the left column.
**Verify:** PASS — `tsc --noEmit` clean, `next build` clean. NOT browser-verified.
**Steer:** Shipped to prod (P33-AI master) via PR #5, squash-merged as db4bacd; dev back-synced after merge.
**Gemini:** 1 round, 1 MEDIUM — dead `space-y` spacing class on the now-single-child column; applied.
**Learnings:** Confirmed Railway frontend auto-deploys on merge to master (user observed all prior fixes redeployed automatically) — the long-standing "manual frontend redeploy" assumption is retired; memory updated.

### [2026-06-25] Burst: assistant-task-prompts

**Built:** Stream A — replaced the AI assistant's 4 quick-prompt buttons with task-focused prompts (focus today / overdue / top priorities / due this week). Stream B — `/ai/chat` query branch now loads the user's open assigned tasks into the LLM context with complete aggregate counts (open/overdue/due-today/due-within-7-days/urgent/high), a priority-aware relevance sort (overdue → priority → due date), a generous cap (40), and truncation labelling; plus a system-prompt nudge to answer focus/priority questions from "Your tasks" first.
**Verify:** PASS — frontend `tsc`+`next build`, backend `py_compile`+import smoke. No automated tests for this burst (per Orchestrator no-tests stance); answer quality not browser-verified locally (no LLM).
**Steer:** Codex 2 rounds. R1 HIGH — counts computed on truncated slice → fixed (aggregate on full set). R2 HIGH (discovery) — due-date-only sort could hide urgent/high tasks → fixed structurally (relevance sort + cap 40 + priority counts); round loop stopped per round-economics. MEDIUM (server-date vs user-local timezone) DEFERRED both rounds → logged in DEFERRED.md. Self-review (Opus) found no Critical/High.
**Learnings:** Building LLM context from a capped query is lossy unless counts are computed on the full set and ordering matches prompt intent — two Codex rounds on the same truncation mechanism. PENDING correction filed (intent-aware context). Timezone correctness for date-relative prompts needs the client's local date, not the server's.

### [2026-06-25] Hotfix: chat-markdown-render (out-of-cycle)

**Built:** Dashboard AI assistant rendered GPT-4o replies via `{msg.content}` as raw text, so the model's markdown (bold section labels, nested bullet lists) collapsed onto one line with literal `-`/`**` showing — an unreadable wall. Added a dependency-free `ChatMarkdown.tsx` renderer for the markdown subset the assistant emits (`**bold**`, `-`/`*` bullets, two-space nested bullets → `◦`, paragraphs), wired assistant messages through it in `AIAssistantPanel.tsx`, and tightened the `CHAT_SYSTEM` prompt in `backend/app/api/v1/ai.py` with renderer-aware formatting rules (one item per bullet line, bold for short labels only, two-space nested bullets, blank line between sections).
**Verify:** PASS — frontend `next build` clean, `tsc --noEmit` clean, backend `ai.py` parses (`ast.parse`). No new lint findings from changed files (2 pre-existing lint items in untouched code left as-is). NOT browser-verified locally (no LLM); not formally probed.
**Steer:** Out-of-cycle hotfix — Phase was Idle, no `/ag-plan`/`/ag-probe` burst cycle. Shipped to prod (P33-AI master) via PR #7, squash-merged as 2ef8ecf; Railway prod auto-deploy triggered. `/ag-ship` RELEASE FLOW did not apply mechanically: no VERSION file (hard-gate inapplicable), Idle/no active burst (archive + manifest steps inapplicable), and prod is a separate remote (`prod` = P33-AI) from the `gh` default (`origin` = anaynasingh/pulseops mirror). No Gemini or Codex review run (Orchestrator chose direct deploy).
**Learnings:** (1) Two coupled changes reinforce each other — the renderer parses the markdown and the prompt makes the model emit it consistently; fixing only one would have been half a fix. (2) The canonical `/ag-ship` skill assumes an active burst + `origin/main` + VERSION; on an Idle out-of-cycle hotfix to a separate prod remote those gates don't map, and forcing them mechanically would have failed at the VERSION and archive-burst steps. Direct squash-merge-PR on P33-AI is the established prod-ship path for this repo. (3) `prod/master` had diverged from `dev` (prior squash merges), so a `dev:master` push was non-fast-forward — the squash-merge PR is what reconciles them, not a direct push.
