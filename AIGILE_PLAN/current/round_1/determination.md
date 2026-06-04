# Round 1 Determination

## R1H1 — Stream A imports Stream B's internal.py before it exists
**Disposition:** ABSORB-PLAN
**Reason:** Stream A's main.py edit registers only the notifications router. Stream B registers the internal router as its own sequential main.py edit after A merges. main.py is back to being a sequenced shared file: A then B.

## R1H2 — SQLAlchemyEnum under-specified vs PG enum name
**Disposition:** ABSORB-GATE
**Reason:** Builder must use `SQLAlchemyEnum(EntityType, name="entity_type", ...)` to match the existing PG enum name exactly. Integration gate: migration applies without DuplicateObject error.

## R1H3 — is_active filter missing from service query contract
**Disposition:** ABSORB-PLAN
**Reason:** reminder_service.py query contract must add JOIN/filter on users.is_active = TRUE. test_reminders.py inactive-user case must exercise this path.

## R1H4 — Concurrent cron invocations can double-send
**Disposition:** REJECT
**Reason:** Railway Cron is single-invocation by design. The last_reminded_at threshold handles re-trigger. Row-level locking is over-engineering for v0.

## R1H5 — "Backend scheduler" goal text doesn't match Railway Cron reality
**Disposition:** BUILD-NOTE
**Reason:** Valid product choice; goal text updated to "Railway Cron Service"; railway.json presence + endpoint responding is the probe artefact.

## R1H6 — Polling interval dropped from NotificationBell spec
**Disposition:** ABSORB-GATE
**Reason:** NotificationBell.tsx polls every 30 seconds. Without an explicit interval the probe "shows in bell" gate is unverifiable.

## Rejected alternatives
- Row-level locking for concurrent cron protection: rejected — over-engineering for Railway Cron single-invocation model.
- Folding is_active into the case enumeration only (not the query): rejected — test would pass a stub but the real query would still send reminders to inactive users.
