# Preservation check: round_0 → round_1

All hunks categorised against round_0/change-request.md authorisations:

- **Exports / contract:** `?date=&tz_offset=` → `?start=<iso>&end=<iso>` (+ date echo) — AUTHORISED (C1)
- **Stream A exports:** added "half-open, tz-aware UTC, no naive datetimes" — AUTHORISED (C1)
- **types.ts scope line:** `?` → `string | null` / `number | null` — AUTHORISED (C7)
- **api.ts scope line:** `day(date, tzOffset)` → `day(start, end, date?)` — AUTHORISED (C1)
- **Schema additions:** `duration_minutes` gains `Field(default=None, ge=15, le=1440)` in TaskUpdate/TaskCreate — AUTHORISED (C4)
- **GET /tasks/day notes:** rewritten for start/end contract, selectinload added, naive-datetime ban — AUTHORISED (C1, C2)
- **Validation cases:** expanded to 8 (malformed/missing start|end, DST-transition) — AUTHORISED (C1)
- **Frontend page:** added off-hours strip, in-grid-only assignment, clamp — AUTHORISED (C3)
- **Scheduling notes:** dropdown offers in-grid hours only; cache key `["tasks","day",dateStr]` — AUTHORISED (C3, C5)
- **Timezone section:** rewritten to frontend-ISO-boundary, removed tz_offset arithmetic — AUTHORISED (C1)
- **Index parity note:** reinforced both SQL + main.py — AUTHORISED (C6)
- **Goal, CHARTER alignment, stream file-sets, Shared files, Deferred:** unchanged — PRESERVED VERBATIM

**Result: no unauthorised additions, deletions, or modifications. All changes trace to round_0 determinations C1–C7.**
