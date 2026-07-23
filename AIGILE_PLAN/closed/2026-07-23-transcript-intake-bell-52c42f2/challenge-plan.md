# Plan Adversarial Challenge

## Round 1 — 2026-07-22
**Model:** opus (Prosecution)

Every file path, line-number, API shape, and existing-behaviour claim in the plan was checked against source. The plan's own stated assumptions and citations are unusually accurate (apscheduler/vitest/CRON_SECRET absence, internal-router unregistered, server.py port ranges 544-576/618-640/643-661/691-716, main.py:123, KanbanBoard.tsx:59, ai.py:29/598/1461 all verified true). The remaining risks are design-level, not text errors.

## Fixed
| Sev | Vector | Location | Defect | Fix applied |
|-----|--------|----------|--------|-------------|
| Low | V2 | plan line 28 (DB spec) | `graph_transcript_id` is the sole dedup lookup key (gate #4) but was declared as a bare column with no index — every poll would seq-scan `meeting_transcripts`. | Added a partial `CREATE INDEX IF NOT EXISTS ... WHERE graph_transcript_id IS NOT NULL` to the migration spec in both plan copies, matching the existing convention at main.py:115/117. |

## Findings (unfixed — require gate decision)
| Sev | Vector | Location | Indictment |
|-----|--------|----------|------------|
| Critical | V1 | `backend/migrations/001_rls_policies.sql:91-129` + plan line 29 (recalc extraction) | `projects` has `FORCE ROW LEVEL SECURITY`; UPDATE is allowed only for owner/creator/admin (or NULL user ctx). The plan extracts `recalc_project_progress` and calls it from `create_task`/`delete_task`/confirm. `create_task`/`delete_task` run on the RLS-stamped `get_db_for_user` session (tasks.py:130,229). When a user accepts a proposed task into a project they do NOT own, the task INSERT succeeds (tasks_insert = any) but the progress-recalc UPDATE on that project silently updates zero rows under RLS. Progress never reflects the new task, no error is raised. Bundling recalc into create_task also introduces this silent no-op into a path that currently has no such bug. |
| High | V2/V1 | plan lines 26, 29 (confirm session unspecified) | The plan says all endpoints use `Depends(get_current_user)` but never states `get_db` vs `get_db_for_user` for the confirm endpoint. This is load-bearing: with `get_db_for_user` (matching create_task) the recalc silently no-ops cross-owner per above; with plain `get_db` the confirm path bypasses RLS on tasks/projects entirely, diverging from the create_task contract. Must be decided explicitly. |
| High | V1 | plan line 29 (AsyncIOScheduler) + gate #4 | In-process `AsyncIOScheduler` in main.py runs on every process. If Railway runs >1 replica, every replica polls, and app-level dedup (SELECT-then-INSERT on `graph_transcript_id`, no UNIQUE constraint) is a race: two concurrent polls both pass the check and both insert → duplicate transcripts and duplicate PROPOSED tasks. The added index is non-unique; hardening requires a UNIQUE constraint + INSERT-conflict handling. |
| High | V1 | plan line 44 (Stream B confirm semantics) | `Confirm → confirm(checkedIds, uncheckedIds)` maps every unchecked item to `dismissed_ids`, and confirm permanently dismisses them. Because checkboxes default-checked, "accept these 3 now, leave the rest for later" is impossible — confirming any subset permanently dismisses all other shown items. Silent data loss of PROPOSED tasks with no partial-triage path. |
| Medium | V2 | plan line 29 (auth) vs deps.py:80, tasks.py:131, ai.py:190 | Confirm endpoint creates real Task rows but is specced with `get_current_user`, not `require_writer`. A viewer could create tasks via confirm, bypassing the guard create_task has. Codebase precedent is inconsistent (transcript create-tasks uses get_current_user) — genuine authz-precedent decision. |
| Medium | V3/V1 | plan line 29 (extraction) vs server.py:724 | No size cap before feeding transcript to `structured_completion`. A multi-hour VTT sent whole to GPT-4o risks the <10s CHARTER criterion, context limits, and cost. No truncation/chunking strategy in scope. |
| Medium | V3 | plan line 29 + tasks.py confirm loop | If `recalc_project_progress` is called per-accepted-task inside the confirm loop, bulk accept runs 2 COUNT queries + commit per task (N×). Should run once per affected project after the batch. |
| Low | V3 | plan lines 27, 61 (internal router) | Registering the `internal` router also activates the dormant `POST /internal/run-reminders` (writes Notification rows). Flagged in plan ambiguity #1; no auto-fire without Railway Cron — low immediate risk, but a live side effect of this burst. |

Note: the plan's four flagged ambiguities are all verified accurate against source — correctly surfaced for Orchestrator confirmation rather than defects.

## Round 2 — 2026-07-22
**Model:** opus (Prosecution, verification pass)

Round-1 resolution verification: all 5 COHERENT (service-session recalc confirmed viable — AsyncSessionLocal is non-RLS, db/session.py:28; bonus: also fixes a latent RLS COUNT undercount in the old inline recalc. require_writer+get_db_for_user compose per tasks.py:130-131. UNIQUE+ON CONFLICT coherent. Dismiss semantics consistent across plan:26/44/gate#3. truncated column additive-safe.)

## Fixed
| Sev | Vector | Location | Defect | Fix applied |
|-----|--------|----------|--------|-------------|
| Critical | V2 | plan:28 DDL | `priority prioritylevel` — live Postgres enum is `priority_level` (schema.sql:15); typo would raise `type "prioritylevel" does not exist`, aborting cold-start migration and app boot. | Corrected to `priority_level` in both plan copies with class-name-vs-DB-type note. |

## Findings (unfixed — require gate decision)
| Sev | Vector | Location | Indictment |
|-----|--------|----------|------------|
| Medium | V1 | plan:28 dedup index | Global UNIQUE on graph_transcript_id: for a shared/co-attended meeting, the second user's poll hits ON CONFLICT DO NOTHING and silently gets zero proposals. UNIQUE (user_id, graph_transcript_id) would serve both race guard and per-user delivery — schema decision, reported only. |
| Medium | V2/V1 | plan:29 recalc callers | Helper opens own AsyncSessionLocal; needs explicit "runs post-commit, best-effort (never 500s a committed write)" contract for create_task/delete_task callers — ordering only specified for confirm path. |
| Low | V1 | plan:29 APScheduler | Single process today (railway config, no --workers); replicas>1 would mean N pollers — redundant Graph calls (429 risk), not duplicate rows. Deferred Railway Cron noted. |
| Low | V3 | plan:44 vitest deps | React 19.2.4 requires @testing-library/react >=16.1; pin it or the harness fails to render. |

Builder note: project fallback must be get-or-create-by-title — do NOT copy ai.py:1428-1439's create-every-time pattern.

GATE: PASS_CLEAN (C=0, H=0 unfixed). Mediums/Lows passed forward as builder context.
