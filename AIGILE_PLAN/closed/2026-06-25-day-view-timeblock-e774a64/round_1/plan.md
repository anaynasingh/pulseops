## Burst Plan
**Goal:** Add a Franklin Covey style `/day` view that time-blocks the logged-in user's tasks into hourly slots for a chosen day, surfacing whether the day is achievable.
**CHARTER alignment:** "Frontend connected to live backend — no mock data"; "Complete backend API — all routers functional."
**Streams:** Two parallel streams (A backend, B frontend). Write-sets pairwise disjoint.

### Stream A - Backend (model + migration + schema + API)
- Scope (files WRITTEN):
  - `backend/app/models/models.py` (add two columns to `Task`)
  - `backend/app/schemas/schemas.py` (add fields to `TaskUpdate`, `TaskOut`, `TaskCreate`)
  - `backend/app/api/v1/tasks.py` (add `GET /tasks/day` endpoint)
  - `backend/app/main.py` (add `ADD COLUMN IF NOT EXISTS` lines in `run_migrations()`)
  - `database/004_task_scheduling.sql` (new migration — canonical SQL backup)
- Excluded: any frontend file; `analytics.py`; all other routers/models.
- Exports (contract for Stream B):
  - `TaskOut` gains `scheduled_at: string | null` (ISO 8601, tz-aware) and `duration_minutes: number | null`.
  - `PATCH /tasks/{task_id}` accepts `scheduled_at` (ISO datetime or explicit `null`) and `duration_minutes`. Omit-vs-null handled by existing `exclude_unset` + `setattr`.
  - `GET /tasks/day?start=<iso>&end=<iso>` (with optional `date` echo label) → `{ "date": "...", "scheduled": [TaskOut...], "unscheduled": [TaskOut...] }`, scoped to `current_user.id`. Backend filters `scheduled_at >= start AND scheduled_at < end` (half-open), tz-aware UTC, no naive datetimes.
- Dependency: none.
- Builder: claude.

### Stream B - Frontend (page + nav + types + api client)
- Scope (files WRITTEN):
  - `frontend/lib/types.ts` (add `scheduled_at: string | null`, `duration_minutes: number | null` to `Task`; add `DayViewResponse`)
  - `frontend/lib/api.ts` (add `tasksApi.day(start, end, date?)`)
  - `frontend/components/layout/Sidebar.tsx` (add one entry to `NAV_ITEMS`)
  - `frontend/app/(dashboard)/day/page.tsx` (new page)
- Excluded: any backend file; all other pages and components.
- Exports: a route at `/day` plus the nav entry.
- Dependency: none for build (codes to agreed contract). End-to-end run needs live `GET /tasks/day` + migrated columns (integration gate).
- Builder: claude.

**Shared files:** none. Stream A touches only `backend/**` + `database/**`; Stream B touches only `frontend/**`. Pairwise disjoint.

**Integration gate:**
- Backend boots: `run_migrations()` adds both columns and the partial index; `/docs` renders `/tasks/day`.
- `GET /tasks/day?start=<iso>&end=<iso>` returns `{scheduled, unscheduled}` with both new fields on each `TaskOut`.
- Frontend `/day` loads against live backend, schedules a task into an in-grid slot, PATCH persists, achievability bar recomputes. No mock data.
- `npm run build` (frontend) + backend import check clean.

**Deferred to next Burst:**
- Multi-user / team day view.
- Recurring blocks, drag-to-resize duration, overlap collision detection.
- Conflict detection with calendar/meetings data.
- Per-user working-hours preference (constant this burst).
- Full dnd-kit drag-from-rail-into-slot (v1 uses click-to-assign).

## Implementation Notes

### New column DDL — `database/004_task_scheduling.sql`
```sql
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 60;
CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at ON tasks (assigned_to, scheduled_at) WHERE scheduled_at IS NOT NULL;
```

### Startup migration lines (`main.py`, in `run_migrations()` before commit)
```python
await db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ"))
await db.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 60"))
await db.execute(text("CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at ON tasks (assigned_to, scheduled_at) WHERE scheduled_at IS NOT NULL"))
```
Load-bearing: ORM column without startup migration = 500 for all users (verified pattern). `database/004_*.sql` is the manual Supabase backup; `run_migrations()` migrates prod on boot. (C6) The partial index `idx_tasks_scheduled_at` must be present in BOTH `database/004_task_scheduling.sql` and `run_migrations()`; keep both.

### ORM additions (`models.py`, in `Task` after `completed_at`)
```python
scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=60, nullable=True)
```

### Schema additions (`schemas.py`)
- `TaskUpdate`: `scheduled_at: Optional[datetime] = None`, `duration_minutes: Optional[int] = Field(default=None, ge=15, le=1440)`. (C4: out-of-range → 422.)
- `TaskOut`: `scheduled_at: Optional[datetime] = None`, `duration_minutes: Optional[int] = None`.
- `TaskCreate`: `scheduled_at: Optional[datetime] = None`, `duration_minutes: Optional[int] = Field(default=None, ge=15, le=1440)`. (C4: out-of-range → 422.)

### API — dedicated `GET /tasks/day`
`GET /tasks/day?start=<iso>&end=<iso>` (uses `get_db` + `get_current_user` like `list_tasks`):
- (C1) `start` and `end` are required ISO 8601 datetimes (FastAPI parses to tz-aware `datetime`; malformed or missing → 422 automatically). `date` is an optional echo label only (returned verbatim); NOT used for filtering. The `tz_offset` parameter and all offset arithmetic are removed entirely.
- (C1) Window: half-open `[start, end)`. The frontend computes the boundaries. Backend never constructs day boundaries and never uses naive datetimes; all comparisons tz-aware UTC.
- `scheduled`: `assigned_to == current_user.id` AND `scheduled_at >= start` AND `scheduled_at < end`, ordered by `scheduled_at`.
- `unscheduled`: `assigned_to == current_user.id` AND `is_completed == False` AND `scheduled_at IS NULL`.
- (C2) Returns `{ "date", "scheduled": [...], "unscheduled": [...] }`. Both queries use `.options(selectinload(Task.assignee), selectinload(Task.project))` before `TaskOut.model_validate` (mirrors `list_tasks`).

Validation cases:
1. Happy path — valid start/end, owned tasks bucketed.
2. Empty day — `scheduled: []`, unscheduled populated.
3. Malformed start/end (non-ISO) → 422.
4. Missing start or end → 422 (both required).
5. Task not owned — excluded even if in window; no private leakage.
6. Clear via PATCH `{"scheduled_at": null}` — drops from scheduled, returns in unscheduled.
7. Local-midnight boundary — task at `start` included (`>= start`), at `end` excluded (`< end`).
8. DST-transition day — frontend-computed start/end span true local day; correct bucketing.

### Frontend page (`day/page.tsx`)
Model on `gantt/page.tsx`: `"use client"`, `useQuery`, `useUIStore().theme`, `Header`.
- Constants `DAY_START_HOUR = 6; DAY_END_HOUR = 22;` slot ~64px.
- Two-column flex: left hour grid (`DAY_START_HOUR..DAY_END_HOUR-1`), right "Unscheduled" rail.
- (C3) In-grid task: absolute, `top = (localHour + min/60 - DAY_START_HOUR)*slotH`, height `(duration_minutes ?? 60)/60*slotH`, priority-colored. Block past `DAY_END_HOUR` clamped to grid bottom.
- (C3) "Outside working hours" strip: scheduled tasks with local hour `< DAY_START_HOUR` or `>= DAY_END_HOUR` render in a compact list ABOVE the grid with an unschedule control; never positioned in the grid.
- Date nav: prev/next + `<input type="date">`, state holds `YYYY-MM-DD`, refetch on change.
- Achievability: `scheduledMinutes = sum(duration_minutes ?? 60)`, `availableMinutes = (END-START)*60`; green/amber/red, "Overbooked by Xh".
- Dark shell `bg-[#0f1629] border border-slate-800 rounded-xl`, light via `isLight`.

### Scheduling interaction — click-to-assign (v1)
(C3) Unscheduled task → "assign to slot" dropdown offering ONLY in-grid hours `DAY_START_HOUR..DAY_END_HOUR-1`. On select: `new Date(y, m, d, hour, 0, 0)` → ISO → `tasksApi.update(id, {scheduled_at, duration_minutes})`. (C5) Optimistic `onMutate` patches `["tasks","day",dateStr]` (dateStr = selected `YYYY-MM-DD`), rollback on error. Unschedule = "x" on a placed block (grid or off-hours strip) sends `{scheduled_at: null}`. dnd-kit drag deferred.

### API client + types
- (C1) `tasksApi.day: (start, end, date?) => api.get("/tasks/day", { params: { start, end, date } }).then(r => r.data)`. No `tz_offset`.
- (C7) `types.ts`: `Task` gains `scheduled_at: string | null;` and `duration_minutes: number | null;` (NOT optional `?`). Plus `interface DayViewResponse { date: string; scheduled: Task[]; unscheduled: Task[]; }`.

### Timezone / day-boundary
- `scheduled_at` is `TIMESTAMPTZ` (UTC at rest). Local day boundary computed entirely on the frontend; backend only receives explicit ISO `start`/`end`.
- (C1) Frontend: `start = new Date(y, m, d, 0, 0, 0)`, `end = new Date(y, m, d + 1, 0, 0, 0)`, sent as ISO. Local `Date` construction is DST-correct (`d + 1` = true next local midnight regardless of 23h/25h day).
- Placing: `new Date(y, m, d, hour, 0, 0)` → ISO (browser encodes offset → correct UTC instant).
- Rendering: convert `scheduled_at` to local hours for positioning (in-grid vs off-hours strip).
- (C1) Backend applies half-open `[start, end)` against tz-aware `scheduled_at`; each task counted once; no naive datetimes.

### Source corrections
- Sidebar array is `NAV_ITEMS` (not `NAV`). Entry: `{ href: "/day", icon: "◷", label: "Day View" }` — monochrome glyph, not emoji.
- `api.ts` default `API_URL` fallback is `http://localhost:8000` (non-blocking).
- `GET /tasks/day` is a distinct static path; no collision with dynamic non-GET `/{task_id}` or GET `/` `list_tasks`. Place alongside `list_tasks`.
