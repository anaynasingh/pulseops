# Round 1 Determination — build-time notes (approved, no re-plan)

Codex round 1 raised MED/LOW edge-case hardening. None change scope/files/architecture. Captured as build notes the builder MUST apply:

- R1-1 (naive datetime): `GET /tasks/day` — if a parsed `start`/`end` is naive (no tzinfo), coerce to UTC (`.replace(tzinfo=timezone.utc)`) before comparing. Frontend sends `.toISOString()` (always `Z`), so this is a defensive guard.
- R1-2 (invalid range): validate `end > start`; if not, 422. Cap span at ≤ 48h → 422 otherwise (prevents arbitrary expensive scans on a /day endpoint).
- R1-3 (duration default): scheduling PATCH from the frontend always includes `duration_minutes` (60 when the user hasn't chosen one). Layout uses `duration_minutes ?? 60`. DB column default 60 covers raw SQL inserts. No reliance on ORM default materialising for app-created tasks.
- R1-4 (ordering): `scheduled` query `ORDER BY scheduled_at`; `unscheduled` query `ORDER BY` priority rank then `created_at` (mirror list_tasks stability).
- R1-5 (boundary-spanning): v1 shows only tasks whose `scheduled_at` is within `[start, end)`. Blocks extending past `DAY_END_HOUR` clamp to grid bottom. Tasks that start before the selected day or spill past midnight are out of scope (deferred) — not rendered on the adjacent day.
- R1-6 (date echo drift): DROP the `date` field from the response. Backend returns `{scheduled, unscheduled}` only. Frontend uses its own selected `dateStr` for the cache key and labels. `tasksApi.day(start, end)` — no `date` param.
- R1-7 (false-parallel contract): accepted — the integration gate's end-to-end check (schedule a task, PATCH persists, achievability recomputes against live backend) is the contract verification.

These supersede the round_1 plan only where they tighten it; the plan text otherwise stands as approved.
