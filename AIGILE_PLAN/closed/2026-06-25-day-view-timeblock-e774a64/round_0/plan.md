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
  - `GET /tasks/day?date=YYYY-MM-DD&tz_offset=<minutes>` → `{ "date": "...", "scheduled": [TaskOut...], "unscheduled": [TaskOut...] }`, scoped to `current_user.id`.
- Dependency: none.
- Builder: claude.

### Stream B - Frontend (page + nav + types + api client)
- Scope (files WRITTEN):
  - `frontend/lib/types.ts` (add `scheduled_at?`, `duration_minutes?` to `Task`; add `DayViewResponse`)
  - `frontend/lib/api.ts` (add `tasksApi.day(date, tzOffset)`)
  - `frontend/components/layout/Sidebar.tsx` (add one entry to `NAV_ITEMS`)
  - `frontend/app/(dashboard)/day/page.tsx` (new page)
- Excluded: any backend file; all other pages and components.
- Exports: a route at `/day` plus the nav entry.
- Dependency: none for build (codes to agreed contract). End-to-end run needs live `GET /tasks/day` + migrated columns (integration gate).
- Builder: claude.

**Shared files:** none. Stream A touches only `backend/**` + `database/**`; Stream B touches only `frontend/**`. Pairwise disjoint.

**Integration gate:**
- Backend boots: `run_migrations()` adds both columns; `/docs` renders `/tasks/day`.
- `GET /tasks/day?date=<today>&tz_offset=<n>` returns `{scheduled, unscheduled}` with both new fields on each `TaskOut`.
- Frontend `/day` loads against live backend, schedules a task into a slot, PATCH persists, achievability bar recomputes. No mock data.
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
Load-bearing: ORM column without startup migration = 500 for all users (verified pattern). `database/004_*.sql` is the manual Supabase backup; `run_migrations()` migrates prod on boot.

### ORM additions (`models.py`, in `Task` after `completed_at`)
```python
scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, default=60, nullable=True)
```

### Schema additions (`schemas.py`)
- `TaskUpdate`: `scheduled_at: Optional[datetime] = None`, `duration_minutes: Optional[int] = None`.
- `TaskOut`: `scheduled_at: Optional[datetime] = None`, `duration_minutes: Optional[int] = None`.
- `TaskCreate`: `scheduled_at: Optional[datetime] = None`, `duration_minutes: Optional[int] = None`.

### API — dedicated `GET /tasks/day`
`GET /tasks/day?date=YYYY-MM-DD&tz_offset=<minutes>` (uses `get_db` + `get_current_user` like `list_tasks`):
- `date` → FastAPI parses to `date` (malformed → 422 automatically). Required.
- `tz_offset` → JS `getTimezoneOffset()` minutes, used to compute UTC window for the local day.
- Window: `start_utc = datetime(date, 00:00) + timedelta(minutes=tz_offset)`, `end_utc = start_utc + 24h`. Half-open `[start_utc, end_utc)`.
- `scheduled`: `assigned_to == current_user.id` AND `scheduled_at` in window, ordered by `scheduled_at`.
- `unscheduled`: `assigned_to == current_user.id` AND `is_completed == False` AND `scheduled_at IS NULL`.
- Returns `{ "date", "scheduled": [...], "unscheduled": [...] }` via `selectinload(assignee, project)` + `TaskOut.model_validate`.

Validation cases:
1. Happy path — bucketed lists.
2. Empty day — `scheduled: []`.
3. Malformed date — 422.
4. Missing date — required → 422.
5. Task not owned — filtered by `assigned_to`; no private leakage.
6. Clear via PATCH `{"scheduled_at": null}` — drops from scheduled, returns in unscheduled.
7. Boundary — local-midnight task lands in exactly one day (half-open window).

### Frontend page (`day/page.tsx`)
Model on `gantt/page.tsx`: `"use client"`, `useQuery`, `useUIStore().theme`, `Header`.
- Constants `DAY_START_HOUR = 6; DAY_END_HOUR = 22;` slot height ~64px.
- Two-column flex: left hour grid, right "Unscheduled" rail.
- Scheduled task: absolute positioned, `top = (localHour + min/60 - DAY_START_HOUR)*slotH`, height `duration/60*slotH`, colored by priority.
- Date nav: prev/next + `<input type="date">`, state holds `YYYY-MM-DD`, refetch on change.
- Achievability: `scheduledMinutes = sum(duration)`, `availableMinutes = (END-START)*60`; green/amber/red, "Overbooked by Xh".
- Dark shell `bg-[#0f1629] border border-slate-800 rounded-xl`, light via `isLight`.

### Scheduling interaction — click-to-assign (v1)
Unscheduled task → "assign to slot" dropdown of hours. On select: local `scheduled_at` = day+hour → ISO with local offset → `tasksApi.update(id, {scheduled_at, duration_minutes})`. Optimistic `onMutate` patches `["tasks","day",date]` cache, rollback on error. Unschedule = "x" on placed block sends `{scheduled_at: null}`. dnd-kit drag deferred.

### API client + types
- `tasksApi.day: (date, tzOffset) => api.get("/tasks/day", { params: { date, tz_offset: tzOffset } }).then(r => r.data)`.
- `types.ts`: `Task` gains `scheduled_at?: string; duration_minutes?: number;` + `interface DayViewResponse { date: string; scheduled: Task[]; unscheduled: Task[]; }`.

### Timezone / day-boundary
- `scheduled_at` is `TIMESTAMPTZ` (UTC at rest). Day boundary computed in user's local tz, never UTC.
- Frontend sends `tz_offset = new Date().getTimezoneOffset()` with day query.
- Placing: construct `new Date(y, m, d, hour, 0)`, send ISO (browser encodes offset → correct UTC instant).
- Rendering: convert `scheduled_at` to local hours for positioning.
- Half-open `[start, end)` window → task counted in exactly one day.

### Source corrections
- Sidebar array is `NAV_ITEMS` (not `NAV`). Entry: `{ href: "/day", icon: "◷", label: "Day View" }` — use a monochrome glyph for consistency, not emoji.
- `api.ts` default `API_URL` fallback is `http://localhost:8000` (non-blocking).
