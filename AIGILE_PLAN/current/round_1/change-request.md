# Change Request: Round 1 → Round 2

## Additions
- None.

## Modifications

- Stream A `main.py` edit: RESTRICT to registering ONLY the `notifications` router. Remove any mention of the `internal` router being included by Stream A.
- Stream B `main.py` edit: ADD back as an explicit Stream B scope item — Stream B performs a sequential `main.py` edit after A merges to add `app.include_router(internal.router, ...)`. This re-establishes main.py as a sequenced shared file: A first, then B.
- Shared files section: update to reflect `main.py` is again a sequenced shared writer — A (notifications router), then B (internal router). Explicit coordination: B's main.py edit must rebase on A's merged main.py.
- Stream B `reminder_service.py` query contract: ADD `AND users.is_active = TRUE` join condition to the core query. Update the malformed/orphaned case enumeration to reference this filter.
- Stream B `test_reminders.py`: clarify the inactive-user test case verifies the is_active filter in the query (not just that it's listed as a case).
- Stream A `backend/app/models/models.py` SQLAlchemyEnum spec: ADD explicit `name="entity_type"` parameter to match the existing PG enum name. Builder-facing instruction in the scope item.
- Stream C `NotificationBell.tsx` scope: ADD explicit 30-second polling interval. Integration gate updated: probe must verify bell updates within ~30 seconds of a reminder being created without page reload.
- Goal sentence: UPDATE from "backend scheduler" to "Railway Cron Service" to match the actual design.

## Deletions
- None.

## Cascading consequences

Files modified in scope:
- `backend/app/main.py` scope split between A (notifications) and B (internal) — both Integration gate references updated in §Modifications above.
- `backend/app/services/reminder_service.py` query tightened — test_reminders.py inactive-user case explicitly references this in §Modifications above; no orphaned references.

No Scope drops. No gate items orphaned. All modified integration gate entries updated in §Modifications.
