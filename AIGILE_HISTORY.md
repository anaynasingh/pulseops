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

### [2026-06-26] Burst: guide-modal-center

**Built:** Fixed the Claude setup "guide" modal opening clamped to the left sidebar pane instead of centered on the viewport. Root cause: the sidebar wrapper in `frontend/app/(dashboard)/layout.tsx` applies a CSS `transform` (`translate-x-*` for the mobile off-canvas slide), which establishes a containing block; since `ClaudeSetupModal` is rendered from inside `Sidebar`, its `fixed inset-0` resolved against the 256px sidebar box rather than the viewport. Fix: render the modal via `createPortal(..., document.body)` so it escapes the transformed ancestor and centers. Single file: `frontend/components/layout/ClaudeSetupModal.tsx`. Client-only render-time guard (`typeof document === "undefined"`) keeps it SSR/hydration-safe.
**Verify:** PASS (static). Production build clean (16/16 pages SSR-generate), `tsc --noEmit` clean, `eslint` 0 errors (2 pre-existing unused-var warnings unchanged). No frontend test harness in repo; live click-through to be confirmed on the dev deploy.
**Steer:** SHIP. Codex round 1: [MED] `react-hooks/set-state-in-effect` blocking lint error from the initial `useEffect(setMounted)` mount guard → fixed by switching to a render-time `typeof document` guard. Round 2: deliverable clean (0 code findings); one [MED] process-artefact finding (STATUS resume pointer → untracked `AIGILE_PLAN/current/`) accepted as known AI-gile architecture — `/clear` preserves the working tree, so `ag-resume` reads the untracked plan store locally; resume never runs from a fresh clone.
**Learnings:** (1) A CSS `transform` on any ancestor silently re-parents `position: fixed` descendants to that ancestor's box — the classic "centered overlay clamps to a panel" bug. The tell here was that the *same* modal rendered directly in the layout (outside the transform) centered fine, while the sidebar-triggered instance did not. (2) The newer React/Next lint rule `react-hooks/set-state-in-effect` rejects the common `useEffect(() => setMounted(true), [])` SSR-portal idiom as a blocking error; the render-time `typeof document` guard is the lint-safe equivalent and is sufficient here because both call sites only mount post-hydration.

**Built:** AI intake confirm now defaults a new project's `owner_id` and every created task's `assigned_to` to the confirming user "unless otherwise specified". Single backend stream, no migration (`Task.assigned_to` and `Project.owner_id` already existed). Uses the `model_fields_set` omit-vs-null contract: omitted field => `current_user.id`; explicit null => respected (ownerless/unassigned); explicit UUID => as-is. Applied to project Routes 1 + 3 and the task-creation loop; Route 2 (existing project) owner is never mutated. Added `assigned_to` to `IntakeConfirmRequest` and 11 tests to `TestIntakeConfirm` (creator-default, override, explicit-null for owner on both routes + assignee, Route 2 owner-not-mutated guard, legacy null-classification default).
**Verify:** PASS (static + adversarial). Live 24-test IntakeConfirm suite + API check UNEXECUTED locally (no backend/.env / Supabase / running server — Connection refused) and deferred to the Railway deploy per steer. Static instead: Pydantic 2.13.4 omit-vs-null contract proven in isolation; schema + ai router import clean; py_compile clean on all 3 files; 24 tests collect with no errors. Opus self-review: 0 Critical/High.
**Steer:** Accept; defer live verification to deploy (precedent: intake-functional). Codex adversarial review (thread 019f0358): verdict APPROVE, 0 material findings — independently re-verified the field-set behavior, defaulting scope, and explicit-null preservation. Two product ambiguities resolved pre-build: backend-only this burst (UI assignee picker deferred); project owner AND all subtasks default to creator.
**Gemini:** clean — no feedback (PR #9, reviewed 12eadaf). Shipped prod P33-AI master, merge 98316eb. Railway prod auto-deploy triggered.
**Learnings:** (1) ag-init drift loop bug: the header drift detector flags a missing parser-contract notice, but `migrate_corrections_header` no-ops when the Builder marker is already present, so drift never clears and `.aigile/last-init` is never written — preflight hard-blocks every burst. Fixed by bringing the CORRECTIONS header to the canonical template manually; flag for /ag-upstream. (2) The omit-vs-null contract is only meaningful with a paired explicit-null test — a `payload.x or current_user.id` implementation passes the omitted and override cases but silently breaks explicit-null; Codex C2 correctly demanded that test. (3) Frontend needed zero changes: because the existing client omits the new field, `model_fields_set` excludes it and the creator-default fires automatically — backward compatible by construction.

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

### [2026-06-26] Burst: intake-functional

**Built:** Made the AI Intake confirm flow actually functional. Before: the confirm button was hardcoded "Create Project", `confirm_intake` created only a Project (suggested subtasks silently dropped, no Tasks), logged no activity, and the frontend invalidated the wrong react-query key (`["projects"]`) while the board reads `["projects-kanban"]` with 60s staleTime + a 30s server cache — so the created project never appeared and the button felt dead. Now (Option C): the intake AI classifies project-vs-task (`suggested_item_type` column + idempotent migration 002 + startup auto-migration); `confirm_intake` is an 8-case router under `require_writer` that creates real Task rows and routes to (1) new project + subtasks, (2) task(s) into an existing project (`_can_edit_project` → 403/404), or (3) task(s) into a new parent project; logs project + per-task activity; busts `_kanban_cache`; returns `ConfirmIntakeResult`. Frontend: "What should this become?" type selector (defaults to AI suggestion, user override) + project picker for task→existing + dynamic button label + state reset/gating + predicate invalidation of `projects`/`projects-kanban`/`dashboard`/`my-dashboard`.

**Verify:** PASS (static + adversarial). Static: full app import (no circular import ai→projects/tasks), `_IntakeAIOutput` Literal validator coercion verified, `IntakeConfirmRequest` priority-required, `ConfirmIntakeResult` forward refs, `tsc --noEmit` clean, 48 tests collect (13 new + concurrency test). Live pytest/UI/API deferred to the Railway dev deploy (no local backend/.env/Supabase) — to be exercised before the dev→main PR.

**Steer:** Accept. Codex round 1: C1 [HIGH] concurrent-confirm TOCTOU race → fixed with `SELECT … FOR UPDATE` atomic claim; C2 [MED] existing-project test polluted real data → fixed with disposable `_reg` project + try/finally teardown. Round 2 (confirmation): C1/C2 confirmed resolved; C3 [MED] `progress_pct` not recalc'd on task creation → deferred (pre-existing app-wide behaviour; `create_task` has the same gap; out of intake scope).

**Learnings:** (1) The "button does nothing" symptom was three independent bugs stacked (dropped subtasks, wrong invalidation key, server cache) — each had to be found separately; the react-query key mismatch (`["projects"]` vs `["projects-kanban"]`) passes typecheck and looks correct in isolation. (2) Codex's C3 was real but pre-existing and app-wide — verifying `create_task` had the identical gap turned a "regression" into a correctly-scoped deferral instead of scope creep into `tasks.py`. (3) `Task.project_id` is NOT NULL, so "standalone task" is not representable — every task route still needs a parent project; this constraint shaped Option C's three routes.
