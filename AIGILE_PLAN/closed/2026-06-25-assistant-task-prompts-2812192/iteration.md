# Iteration log: assistant-task-prompts

## Round 0 (planned 2026-06-25)

**Plan written:** 2026-06-25
**Plan agent model:** opus (authored inline by orchestrator after source-first investigation of AIAssistantPanel.tsx and ai.py /chat branch)
**Codex challenge:** evaluated — SKIP (no new dependency/schema/service/Agent/pattern; reuses existing Task query + context-append in one endpoint; 2-file change). See presentation.

## Approved 2026-06-25

**Round approved:** 0
**Burst base:** ea32bf424e5943474f68866fcf23ccaea4a27a8a
**Approved by:** Orchestrator

## Probe round 1 (2026-06-25)

**Codex critique (verdict: needs-attention):**
- [HIGH] ai.py:790-813 — task context truncates to 15 AND computes open/overdue/due-today counts from the truncated list; a user with >15 tasks is misinformed and "what are my overdue tasks?" can omit real overdue work.
- [MEDIUM] ai.py:804-824 — today/overdue labels use server `date.today()` not the user's local date; day-boundary unreliability on non-UTC deploys.

**Steer decision:** fix HIGH now; DEFER MEDIUM (timezone) to a follow-up burst (cross-stack: client-local-date in /ai/chat request). Logged in DEFERRED.

**Authorised scope (round 1):** `backend/app/api/v1/ai.py`, the per-user task block only (~lines 789-827):
- Compute `total_open`, `overdue_n`, `due_today_n`, and a new `due_week_n` (within 7 days) on the FULL filtered task set BEFORE truncation (mirrors the projects block above, which counts on the full list and displays `[:20]`).
- Slice to 15 for the listing only; append "...and N more (showing the soonest-due)" when truncated.
- No other files. Timezone (MEDIUM) explicitly NOT touched this round.

**Class-fix scan:** count-on-truncated-list defect. Sibling read path = the projects block (lines 778-786) — already correct (counts on full `projects`, displays `[:20]`). No other site with the bug.

## Probe round 1 preservation-check

All hunks within authorised scope (ai.py per-user task block). Categorisation:
- counts computed before truncation — AUTHORISED modification
- `due_week_n` 7-day bucket added — AUTHORISED addition
- `shown = my_tasks[:15]`, list `shown` — AUTHORISED modification
- "...and N more" truncation label — AUTHORISED addition
No unauthorised additions/deletions/modifications. Timezone (MEDIUM) untouched. PASS.

## Probe round 2 (2026-06-25)

**Codex critique (verdict: needs-attention):**
- [HIGH] ai.py:811-836 (DISCOVERY) — listing sorted by due date only + sliced to 15, so an urgent/high task with no/late due date can be hidden behind dated tasks; "top priorities" prompt then recommends wrong work. New case not in the plan.
- [MEDIUM] ai.py timezone — re-raise of the round-1 deferred timezone finding. Disposition unchanged: DEFERRED.

**Classification:** discovery, and same `truncation-to-15` mechanism as round 1 → round-economics structural-stop triggered.

**Steer decision:** apply structural fix and STOP the Codex round loop (no round 3). File PENDING for intent-aware context. Timezone stays deferred.

**Authorised scope (round 2):** `backend/app/api/v1/ai.py`, per-user task block only:
- add `_prio()` helper + urgent_n/high_n aggregates over full set
- replace due-date-only sort with relevance sort (overdue → priority → due date → undated last)
- raise listing cap 15 → 40 (personal backlog effectively never truncated)
- add urgent/high to header; update truncation-label wording

**Class-fix scan:** structural truncation defect resolved at the mechanism (relevance sort + generous cap + complete counts). No sibling site.

## Probe round 2 preservation-check

All hunks within authorised scope. AUTHORISED: _prio helper (add), urgent_n/high_n (add), relevance sort + cap 40 (modify), header urgent/high (add), label wording (modify). No unauthorised changes. PASS.

## Codex round loop: STOPPED after round 2 (round-economics structural-stop; remaining items = deferred timezone + accepted relevance heuristic).
