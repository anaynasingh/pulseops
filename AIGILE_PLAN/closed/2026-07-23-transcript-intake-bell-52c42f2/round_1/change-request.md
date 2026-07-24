# Change-request whitelist — round 1 → round 2 (2026-07-22)

Authorised changes to plan.md ONLY. Everything not listed must be preserved verbatim.

## Additions
1. Stream A implementation notes: poll serialization contract (R1-1) — APScheduler max_instances=1 + module-level asyncio.Lock shared with the internal endpoint (waits or 409s during an active run); single-process deploy verified; replica scale-out stays in Deferred.
2. Stream A DB spec: `extracted_at TIMESTAMPTZ NULL` on meeting_transcripts, in 007 + run_migrations mirror (R1-2), with the extraction-state contract: success ⟺ extracted_at IS NOT NULL; retry/reuse checks key on extracted_at, never action_items truthiness.
3. Stream A implementation notes: window-independent retry sweep (R1-3) — per tick, re-pick rows where extracted_at IS NULL AND created_at > now()-7d and extract them.
4. Stream A implementation notes: calendarView pagination contract (R1-4) — follow @odata.nextLink to exhaustion before cursor advance.
5. Stream A implementation notes: task-move recalc (R1-5) — update_task recalcs old AND new project when project_id changes.
6. Stream B contract: distinct query keys ["proposed-tasks","count"] / ["proposed-tasks","list",status], prefix invalidation (R1-6).
7. Stream B contract: vitest resolve.alias for "@" matching tsconfig paths (R1-7).
8. Stream B contract: refetchInterval 60_000 on the badge count query (R1-8).
9. Integration gate #4: overlapping poll executions for one user create no duplicate proposals (serialization test) (R1-1).
10. Integration gate #6 case set: zero-action-item extraction success is terminal (no endless retry) (R1-2).

## Modifications
11. Stream A implementation notes: the C1 reuse sentence ("missing-stored-extraction checks") and C4 retry sentence must be restated in terms of `extracted_at IS NULL` rather than absent action_items (R1-2 supersedes their state test; the contracts themselves stand).

## Deletions
None.

## Cascading consequences
- Item 2 adds one column to the DB spec — cascades into the 007 + run_migrations mirror text in the same plan line. No scope-file changes.
- No stream decomposition, executor, dependency, or scope-list changes authorised (scope lists unchanged this round).
