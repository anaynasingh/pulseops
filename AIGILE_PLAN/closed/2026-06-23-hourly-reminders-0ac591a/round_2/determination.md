# Round 2 Determination

## R2H1 — Railway gate too weak
**Disposition:** ABSORB-GATE
**Reason:** railway.json must specify cron schedule `0 * * * *`, target endpoint URL, and `X-Cron-Secret` header name. Integration gate must verify these are present in the file and that the endpoint returns 200 on correct secret.

## R2M2 — CRON_SECRET auth delivery unspecified
**Disposition:** ABSORB-GATE
**Reason:** Secret delivered via `X-Cron-Secret` request header. Endpoint returns 401 on missing or wrong value. Gate verifies 200 on correct secret, 401 on wrong.

## R2M3 — Reassignment clears last_reminded_at?
**Disposition:** BUILD-NOTE
**Reason:** Stream B scope gets `backend/app/api/v1/tasks.py` as a minor addition. When `assigned_to` changes in the PATCH handler, reset `last_reminded_at = None`. Defers full per-assignee tracking to next burst.

## R2M4 — Insert + stamp atomicity unspecified
**Disposition:** ABSORB-GATE
**Reason:** reminder_service.py must wrap `INSERT Notification + UPDATE Task.last_reminded_at` in a single `async with session.begin()` transaction block. Partial write breaks the duplicate-guard guarantee.

## R2L5 — GET /notifications limit unbounded
**Disposition:** REJECT
**Reason:** Default of 20 is the binding constraint. Arbitrary limit is v0-acceptable. No gate required.

## Rejected alternatives
- Per-assignee reminder tracking table: rejected — over-engineering for v0; BUILD-NOTE handles the reassignment edge case with a simpler reset.
- Hard-coding limit cap in the API: rejected — default 20 is sufficient for v0.
