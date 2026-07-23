# Determination — round 1 Codex challenge (2026-07-22)

Orchestrator disposition: ABSORB all 8 round-1 findings into round-2 re-plan, THEN PROCEED to Step 7 approval without a further Codex confirmation pass (Orchestrator ruling: severities falling, all findings second-order pins; Codex round cost 10-20 min with real hang risk in this env).

| ID | Sev | Disposition | Determination |
|----|-----|-------------|---------------|
| R1-1 | HIGH | ABSORB-PLAN | Serialize the poll per process: APScheduler job registered with max_instances=1 AND a module-level asyncio.Lock shared by the scheduler callback and the internal endpoint handler, so a manual POST /internal/run-transcript-poll during a scheduled tick waits or returns 409. Single-process deploy verified (railway config, no --workers). Replica scale-out remains deferred (Railway Cron item). |
| R1-2 | HIGH | ABSORB-PLAN | Add `extracted_at TIMESTAMPTZ NULL` to meeting_transcripts (007 + run_migrations mirror). Extraction success ⟺ extracted_at IS NOT NULL (zero-item success representable: extracted_at set, action_items=[]). Retry/reuse checks key on extracted_at, never on action_items truthiness. |
| R1-3 | HIGH | ABSORB-PLAN | Retry decoupled from calendar window: each tick, after the calendar scan, re-pick meeting_transcripts rows where extracted_at IS NULL AND created_at > now() - 7 days and run extraction for them (per-user proposal fan-out follows the standard path). Bounded by the 7-day age cap. |
| R1-4 | HIGH | ABSORB-PLAN | The ported calendarView call must follow @odata.nextLink until exhausted ($top stays 50 per page; pagination loop mandatory before any cursor advance). |
| R1-5 | MED | ABSORB-PLAN | update_task: when project_id changes, recalc BOTH the old and new project (post-commit, best-effort, per the C8 contract). |
| R1-6 | MED | ABSORB-PLAN | Distinct query keys: ["proposed-tasks","count"] for the badge, ["proposed-tasks","list",status] for the panel; all invalidations use the ["proposed-tasks"] prefix. |
| R1-7 | MED | ABSORB-PLAN | vitest.config.ts sets resolve.alias '@' → repo frontend root, matching tsconfig.json paths ("@/*"). |
| R1-8 | MED | ABSORB-PLAN | Badge count query gets refetchInterval: 60_000 (matches dashboard page precedent at app/(dashboard)/dashboard/page.tsx:21). |

Rejected alternative (R1-1): UNIQUE constraint on proposed_tasks (user_id, transcript_id, title) — title collisions within one transcript are legitimate (two distinct action items may share a short title), so a constraint would silently drop real proposals; serialization is the correct guard.
