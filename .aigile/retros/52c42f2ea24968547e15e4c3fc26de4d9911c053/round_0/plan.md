# Retrospective — transcript-intake-bell (2026-07-23, opus round 0)

## 1. Corrections review
- PENDING [2026-06-26] ag-init preflight header-drift (Builder: n/a): recommend PROMOTE — awaiting Orchestrator confirmation.
- Gap: manifest/seven-field failure this burst earned a correction; PENDING entry written 2026-07-23.

## 2. Command friction
- 0-byte manifest + prose stream bullets blocked probe gates; fix at /ag-plan (emit atomically) + preflight auto-remediation. Candidate /ag-upstream.
- AsyncMock/Py3.12 coroutine trap (bit new tests AND pre-existing test_reminders). Fix: shared conftest mock-session helper.
- Codex task --resume hangs (exit 143); peer ag-review --wait completed in-ceiling — default the review gate to peer in this env.

## 3. Missing knowledge (recorded to memory 2026-07-23)
- Postgres enum priority_level (underscore) vs SQLAlchemy PriorityLevel.
- meeting_transcripts.action_items JSONB reusable for extraction storage.
- Per-user delegated Graph token pattern (MSAL cache decrypt→silent→re-encrypt, ai.py:751-763).
- Env: apscheduler via pip3 --user --break-system-packages; black NOT installed.

## 4. Agent gaps
- Plan-time gate-artefact validator (manifest non-empty, seven-field stream blocks) — highest value.
- Py3.12-aware test-mock helper ("test-doctor").

## 5. Discovered capabilities (appended to CAPABILITIES.md 2026-07-23)
- Meeting Intelligence end-to-end; per-user delegated Graph access; FE vitest harness (resolves DEFERRED 2026-06-25 FE-harness item); RLS-safe service-session recalc; constraint-backed dedup; in-process APScheduler + internal router; peer ag-review --wait works in this env.

## 6. Decision pipeline
- Four steer rulings verified present in DEFERRED.md.
- Added DEFERRED: poll replica scale-out trigger; test_reminders AsyncMock repair.
- CONSIDERATIONS: M365-MCP-depth item now partially resolved (transcript chain ported) — narrow/close at next charter pass.
