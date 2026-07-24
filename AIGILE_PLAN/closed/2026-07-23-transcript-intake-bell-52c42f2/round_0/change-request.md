# Change-request whitelist — round 0 → round 1 (2026-07-22)

Authorised changes to plan.md ONLY. Everything not listed must be preserved verbatim.

## Additions
1. Stream A implementation notes: per-user proposal-creation idempotency contract (C1) — proposal creation keyed on (user_id, transcript_id) absence; extraction result stored on the shared meeting_transcripts row and reused for subsequent users; at most one LLM call per transcript.
2. Stream A DB spec: extraction-storage note — extracted action items JSON persisted on meeting_transcripts (new column `extracted_items JSONB` if no suitable column exists — Plan agent verifies against models.py:317-330 and adds to 007 + run_migrations mirror if needed) (C1).
3. Stream A implementation notes: recurring-occurrence binding contract (C2) — occurrence-window transcript selection, port the occurrence-date parameter of the source helper.
4. Stream A implementation notes: poll cursor contract (C3) — scan window [max(cursor - 1h, now - 7d), now]; advance to poll-start only on exception-free user iteration; per-user failure isolation; idempotent rescan.
5. Stream A implementation notes: extraction timeout contract (C4) — asyncio.wait_for 30s around structured_completion in poll path; per-transcript try/except; unextracted transcript retried next tick.
6. Integration gate #5: add "simulated slow LLM call fails boundedly; batch continues" (C4).
7. Stream B Scope: add `frontend/package-lock.json` (C5).
8. Stream A implementation notes: `CRON_SECRET: Optional[str] = None`; falsy → 401, never boot-crash (C6). Gate #6 case set gains "no CRON_SECRET configured".
9. Stream A confirm contract (plan:26): overlapping accepted_ids ∩ dismissed_ids → 422 listing offending ids; negative-path test (C7). Gate #6 case set gains the overlap case.
10. Stream A implementation notes: generalized recalc ordering contract (C8) — post-commit invocation by every caller; helper best-effort, logs, never raises.

## Modifications
11. Stream A implementation notes: the existing "Only proceed to extraction/proposal creation when the transcript insert actually took" sentence must be REPLACED by the C1 contract (insert-won is no longer the gate for proposal creation; per-user proposal absence is).
12. Integration gate #4: extend with per-user delivery acceptance — "two users attending the same meeting each get their own proposals from one shared transcript row" (C1).

## Deletions
None.

## Cascading consequences
- No Scope files are dropped; no references to dropped files exist.
- Item 2 may ADD a column to the DB spec (extracted_items JSONB on meeting_transcripts) — authorised, cascades into 007_proposed_tasks.sql + run_migrations mirror text in the same plan lines.
- Item 11 rewrites one existing (round-1-fixed) sentence — authorised modification of a prior fix, superseded by C1's stronger contract; the ON CONFLICT/UNIQUE-index race fix itself is preserved.
- No stream decomposition, executor, or dependency changes authorised.
