# Preservation check: round_1 → round_2

## Verdict: PASSED — all diff hunks authorised

1. Goal sentence "backend scheduler" → "Railway Cron Service" — AUTHORISED (§Modifications: goal sentence updated)
2. models.py SQLAlchemyEnum adds `name="entity_type"` — AUTHORISED (§Modifications: explicit name= parameter)
3. Stream A main.py scope: "ONLY notifications router" + explicit exclusion of internal router — AUTHORISED (§Modifications: Stream A main.py restricted)
4. Stream A Excluded: adds "internal router include" — AUTHORISED (follows from #3)
5. Stream A Exports: SQLAlchemyEnum name updated — AUTHORISED (follows from #2)
6. Stream B reminder_service.py: adds `AND users.is_active = TRUE` join — AUTHORISED (§Modifications: query contract tightened)
7. Stream B internal.py: removes redundant "Register this router..." sentence — AUTHORISED (follows from #3, B now owns this)
8. Stream B main.py: new scope item for B's sequential edit — AUTHORISED (§Modifications: Stream B main.py edit added back)
9. Stream B test_reminders.py: adds inactive-user query verification detail — AUTHORISED (§Modifications: clarify inactive-user test)
10. Stream B case enumeration malformed/orphaned: updated to reference is_active join — AUTHORISED (follows from #6)
11. Stream C NotificationBell.tsx: adds 30-second polling interval — AUTHORISED (§Modifications: explicit poll interval)
12. Stream C Exports: adds "30-second poll" — AUTHORISED (follows from #11)
13. Shared files: updated to sequenced A-then-B — AUTHORISED (§Modifications: shared files updated)
14. Integration gate: all three bullet points updated — AUTHORISED (§Modifications: integration gate)

### Unauthorised hunks: NONE
