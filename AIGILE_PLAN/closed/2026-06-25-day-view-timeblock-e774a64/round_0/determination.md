# Round 0 Determination

## C1 — HIGH: timezone/DST boundary. ABSORB-PLAN
Replace `tz_offset` + 24h arithmetic with frontend-computed ISO day boundaries.
- Frontend computes `start = new Date(year, month, day, 0,0,0)` and `end = new Date(year, month, day+1, 0,0,0)` (JS Date respects local DST automatically — these are the true local-midnight instants), sends both as ISO UTC strings.
- New endpoint contract: `GET /tasks/day?start=<iso>&end=<iso>` (replaces `date`+`tz_offset`). Backend filters `scheduled_at >= start AND scheduled_at < end` (half-open), both parsed as tz-aware UTC. Also accept `date=YYYY-MM-DD` purely as an echo/label in the response.
- Backend builds all datetimes tz-aware (`datetime.fromisoformat` on ISO-with-offset → aware; compare against TIMESTAMPTZ column). No naive datetimes.

## C2 — HIGH: eager loading. ABSORB-PLAN
`GET /tasks/day` query uses `.options(selectinload(Task.assignee), selectinload(Task.project))` before `TaskOut.model_validate`, exactly like `list_tasks` and `update_task`.

## C3 — HIGH: off-hours tasks vs 6–22 grid. ABSORB-PLAN
- Click-to-assign dropdown only offers slots `DAY_START_HOUR..DAY_END_HOUR-1`, so new blocks never land off-grid.
- Defensive render: scheduled tasks whose local hour is `< DAY_START_HOUR` or `>= DAY_END_HOUR` render in a compact "Outside working hours" list above the grid (with an unschedule control), never absolute-positioned. Tasks extending past `DAY_END_HOUR` are clamped to the grid bottom.

## C4 — MED: duration bounds. ABSORB-PLAN
`duration_minutes` in TaskCreate/TaskUpdate: `Optional[int] = Field(default=None, ge=15, le=1440)`. Frontend uses `duration_minutes ?? 60` for layout. Out-of-range → 422.

## C5 — MED: cache key. ABSORB-PLAN
react-query key = `["tasks", "day", dateStr]` where `dateStr` is the selected `YYYY-MM-DD` (uniquely identifies the local day). tz no longer in the contract (C1), so no divergence. Optimistic onMutate patches this key.

## C6 — MED: index parity. BUILD-NOTE
The partial index `idx_tasks_scheduled_at` must appear in BOTH `database/004_task_scheduling.sql` AND the `run_migrations()` block in `main.py`. Plan already specifies both; builder must not drop either.

## C7 — LOW: nullable frontend types. ABSORB-PLAN
`Task.scheduled_at: string | null`, `Task.duration_minutes: number | null` in types.ts (match Pydantic null serialization), not optional `?`.

## Rejected alternatives
- Keeping `tz_offset` but using the selected date's offset: still fragile across DST transition days and adds server-side tz math. Frontend-ISO-boundary approach (C1) is simpler and fully DST-correct.
- Expanding the grid to 24h to absorb off-hours tasks: rejected — Franklin Covey working-day framing wants a focused window; off-hours strip (C3) is the lighter fix.
