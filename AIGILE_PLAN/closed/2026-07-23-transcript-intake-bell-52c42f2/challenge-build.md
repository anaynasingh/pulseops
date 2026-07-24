# Build Adversarial Challenge

## Round 1 — 2026-07-23
**Model:** opus (Prosecution)
**Diff:** 52c42f2..HEAD (package-lock excluded)

## Fixed
| Sev | Vector | Location | Defect | Fix applied |
|-----|--------|----------|--------|-------------|
| Low | V2 | frontend/components/layout/ProposedTasksBell.tsx:175 | `new Date("YYYY-MM-DD")` parses date-only strings as UTC midnight; date-fns format renders local time, so negative-offset timezones display the meeting date one day early (CI is UTC, so tests masked it). | Parse as local midnight: `new Date(\`${group.meetingDate}T00:00:00\`)`. Vitest 7/7 green after fix. |

## Findings (unfixed — require gate decision)
| Sev | Vector | Location | Indictment |
|-----|--------|----------|------------|
| Medium | V2 | backend/app/api/v1/proposed_tasks.py:98-105 | Catch-all "Meeting Action Items" project creation is check-then-create with no unique constraint. Two concurrent first-time confirms by one user create two rows; every later confirm's `scalar_one_or_none()` then raises MultipleResultsFound → permanent HTTP 500 for that user. Proper fix needs a migration (partial unique index on projects(owner_id, title) for the catch-all) — schema + multi-file change. |
| Medium | V2 | graph_service.py:117-118 → transcript_poll_service.py:157 | A PERMANENT per-meeting Graph 4xx (e.g. 403 on one meeting's transcripts) raises out of _poll_user each tick, pinning that user's cursor forever — silent full stall for that user. Designed isolation handles transient errors; poison-meeting skip-vs-fail semantics are a design call (per-meeting try/except + what to do with the cursor). |
| Low | V2/V3 | transcript_poll_service.py:169-192 | A currently-failing extraction is attempted twice per tick (calendar loop + retry sweep re-selects the same row), doubling worst-case LLM latency/cost per stuck transcript per tick. Idempotent and self-clearing; not a correctness defect. |

**Reviewer verification notes:** C1–C8 and R1-1..R1-8 contracts verified correct; priority_level enum correct in 007 + run_migrations mirror; constraint-backed dedup correct; service-session recalc correct; expire_on_commit=False makes post-commit attribute access safe; retry sweep correctly excludes manual uploads (graph_transcript_id IS NOT NULL); frontend query keys/refetch/alias/confirm semantics match plan.
