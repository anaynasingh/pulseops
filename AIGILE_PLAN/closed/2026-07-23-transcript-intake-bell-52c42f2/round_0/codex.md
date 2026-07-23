# Codex plan challenge — round 0 (2026-07-22)

Invoked via `codex-review task --prompt-file` (shared session; no discrete thread ID exposed by `codex-review status`). Read-only critique; constraints + Orchestrator rulings supplied as known-decisions context.

Read-only review only. No patches applied.

**Findings**

1. **Critical - per-user proposals can be suppressed by transcript-level dedup**
   Location: `database/007_proposed_tasks.sql`, `backend/app/services/transcript_poll_service.py`
   The plan says proposals are user-scoped, but also says proposal creation only proceeds when the `meeting_transcripts.graph_transcript_id` insert wins. If two connected PulseOps users can see the same Teams transcript, the second user's poll can hit `ON CONFLICT DO NOTHING` and skip proposal creation entirely. This is not a complaint about constraint-backed dedup; it is about coupling per-user `ProposedTask` creation to a globally deduped transcript insert. Missing acceptance: two users with access to the same transcript both get their own pending proposals, without duplicate transcript rows.

2. **High - recurring Teams meetings can ingest the wrong occurrence or only the latest occurrence**
   Location: `backend/app/services/graph_service.py`, `backend/app/services/transcript_poll_service.py`
   The source helper sorts all transcripts for a recurring online meeting and defaults to the latest unless an occurrence date is supplied (`mcp-servers/m365/server.py:697-707`). The plan does not state that the poll path binds a calendar event occurrence date to the transcript selection. Failure mode: every occurrence in a recurring series can map to the same latest transcript, while older/newer distinct occurrences are missed or mislabeled. Missing acceptance: recurring-series calendar events with multiple transcript dates.

3. **High - poll cursor semantics are undefined**
   Location: planned `User.m365_last_transcript_poll`; planned `transcript_poll_service.py`
   The plan adds `m365_last_transcript_poll` but never defines when it advances: before/after Graph paging, after transcript insert, after GPT extraction, after proposal creation, or after partial user failure. Advancing too early loses transcripts after extraction/proposal failure; advancing too late causes repeated Graph scans every tick. Missing acceptance: partial transcript failure, model failure, paginated calendar response, retry behavior.

4. **High - the <10s extraction criterion is measured but not enforced**
   Location: planned `transcript_poll_service.py`
   No plan-level timeout contract on the `structured_completion` call in the poll path. A slow OpenRouter call can hold the scheduler/internal endpoint past the CHARTER limit. Missing acceptance: simulated slow LLM call fails boundedly and does not block the whole poll batch.

5. **Medium - dependency scope makes the Vitest harness unreproducible**
   Location: frontend/package.json:29
   Stream B's write scope does not include `frontend/package-lock.json`. The repo has an npm lockfile; changing only `package.json` leaves `npm ci` unable to install the new test stack.

6. **Medium - CRON_SECRET startup behavior is underspecified**
   Location: backend/app/core/config.py:5, backend/app/api/v1/internal.py:11
   Existing internal auth expects a falsy value to disable access. A required `str` setting would crash app import in local/test envs without the env var. Missing acceptance: app boots with no cron secret; internal endpoints return unauthorized rather than crashing.

7. **Medium - batch confirm has no declared behavior for overlapping explicit lists**
   Location: planned `proposed_tasks.py`, `schemas.py`
   Same UUID in both `accepted_ids` and `dismissed_ids` is reachable via direct API use. Missing acceptance: overlap returns a deterministic error or deterministic outcome.

8. **Medium - service-session recalc ordering is not pinned**
   Location: tasks.py:127, planned `proposed_tasks.py`
   If any caller invokes the non-RLS recalc helper before committing, the helper's separate session counts stale rows. Plan pins ordering only for confirm. Missing acceptance: recalc observes newly created/deleted/completed tasks from each caller path.

Overall: the plan is much stronger than a typical parallel split, but the risky parts are not writer conflicts. They are lifecycle boundaries: transcript dedup versus per-user proposals, recurring meeting occurrence selection, poll cursor advancement, and test/dependency reproducibility.
