**Findings** (Codex thread 019eff63-5f00-78f1-ad8a-41b9ee9f26f5)

1. HIGH: timezone boundary logic underspecified for DST. tz_offset + 24h fails on DST-transition days and when the selected date's offset differs from today's. Backend pseudo-code risks naive datetimes despite TIMESTAMPTZ.
2. HIGH: GET /tasks/day must eager-load assignee + project (selectinload) like existing task endpoints, or async lazy-load fails / cards incomplete.
3. HIGH: backend returns full 00:00–24:00 day but UI grid is 06:00–22:00. Off-hours tasks compute negative/overflow positions or vanish. No acceptance criteria for off-hours tasks.
4. MED: duration_minutes nullable + unbounded → null/0/negative/huge values produce zero/negative/overflow blocks. Needs bounds validation.
5. MED: optimistic cache key ["tasks","day",date] omits tzOffset though the API call includes it → cache divergence.
6. MED: index parity — partial index must exist in BOTH database/004 SQL and main.py startup migration, else boot-migrated vs SQL-migrated environments differ.
7. LOW: frontend types should be `scheduled_at: string | null` / `duration_minutes: number | null` (Pydantic serializes optional as null), not optional `?`.

Path check: existing paths real; new paths (database/004_task_scheduling.sql, day/page.tsx) plausible, not yet present.
