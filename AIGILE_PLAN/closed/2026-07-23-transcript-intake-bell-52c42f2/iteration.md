# Iteration log: transcript-intake-bell

## Round 0 (planned 2026-07-22)

**Plan written:** 2026-07-22
**Plan agent model:** opus
**Codex challenge:** round 0 run 2026-07-22 via codex-review task (shared session). 1 Critical, 3 High, 4 Medium — all lifecycle-boundary findings (per-user proposals vs global transcript dedup; recurring-occurrence binding; poll cursor semantics; LLM timeout; package-lock scope; CRON_SECRET optionality; overlapping confirm lists; recalc ordering). Output: round_0/codex.md. Prior: ag-challenge rounds 1-2 PASS_CLEAN after 5 inline fixes + 7 Orchestrator rulings (challenge-plan.md).

Route decision (Orchestrator, 2026-07-22): Route 1 — backend polls Microsoft Graph
directly with per-user delegated tokens (User.m365_token_cache). Routes considered
and rejected: claude-bridge push (request/response only, per-user token contract
broken, CHARTER hard-spec conflict on LLM inference); manual upload v1 (superseded
by Route 1 feasibility findings). Research reports: three parallel investigations
(m365 MCP server reach, claude-bridge architecture, Graph transcript API state)
completed 2026-07-22.

Plan agent corrections to brief premises: (1) no APScheduler exists in backend —
internal router unregistered, CRON_SECRET missing, reminders dormant; (2) vitest
not configured at all in frontend — full harness needed, not just RTL/jsdom.

## Round 1 (re-plan, 2026-07-22)

**Trigger:** Orchestrator ABSORB of all 8 Codex round-0 findings.
**Artefacts:** round_0/determination.md (dispositions), round_0/change-request.md (12-item whitelist), round_1/plan.md (Opus Plan agent revision), round_1/preservation-check.md (3 hunks, all AUTHORISED, no unauthorised edits). Lint OK.
**Notable:** extraction storage reuses existing meeting_transcripts.action_items JSONB (models.py:326) — no new column needed; whitelist item 2's conditional resolved by Plan agent verification.
**Codex round 1:** first attempt (task --resume) hung and hit the 10-min Bash timeout (exit 143, no output; matches known env behaviour — see memory feedback_codex_adversarial_hangs). Retried as a fresh non-resumed task in background; result landed as round_1 findings (8: 4 HIGH, 4 MED).

## Round 2 (re-plan, 2026-07-22; closed 2026-07-23)

**Trigger:** Orchestrator ABSORB of all 8 round-1 findings (round_1/determination.md), with ruling: PROCEED to Step 7 approval after re-plan, NO further Codex confirmation pass (severities falling, all second-order pins, hang risk).
**Artefacts:** round_1/change-request.md (11-item whitelist), round_2/plan.md, round_2/preservation-check.md (5 hunks, all AUTHORISED, PASS — completed 2026-07-23 after session interruption left it empty). challenge-decision.md: GATE PASS_CLEAN, round 2, 0 Critical, 0 High.
**Plan promoted:** current/plan.md byte-identical to round_2/plan.md.

## Build (started 2026-07-23)

Orchestrator go-ahead 2026-07-23 ("keep working on that"). Phase → Building.
Burst base: 52c42f2ea24968547e15e4c3fc26de4d9911c053 (dev HEAD at approval).
Streams: A backend (transcript poll + proposed_tasks store/API), B frontend (bell/panel + vitest harness). Disjoint file sets, both Executor: claude.

## Steer (2026-07-23)

Decision: SHIP. Orchestrator delegated the four open rulings to the assistant's recommendations and confirmed ship ("take decisions on all 4 actions and then ship it"):
1. Catch-all project race → DEFER (DEFERRED.md, unique-index migration, trigger: first 500 or next projects migration).
2. Poison-meeting cursor stall → DEFER (DEFERRED.md, per-meeting skip+log, trigger: first stuck cursor or next poll burst).
3. TLS verify=False → ACCEPT as documented corp-proxy convention; repo-wide env-driven toggle queued in DEFERRED.md.
4. Retry-sweep fan-out ambiguity → ACCEPT for v1; durable association queued in DEFERRED.md.
CHARTER objective "Meeting Intelligence working" marked complete. Note: RELEASE FLOW STOP gate still applies at /ag-ship — steer approval is not merge approval.

## Probe (2026-07-23)

Verify: PASS. Tests: pytest 37/37 new suites + vitest 7/7 + tsc clean (test_reminders 6 pre-existing env failures, not burst; regression/guardrails need live server — deferred to deploy). API: all 5 new endpoints registered (OpenAPI) and 401 unauthenticated, incl. internal with no CRON_SECRET. Gates: scope 0, risk-tier 0, executors 0 (STATUS streams migrated to seven-field shape; empty manifest re-inited; Stream B executor provenance corrected to general-purpose-builder with rationale in plan.md).
ag-challenge --build round 1 (opus/Prosecution): PASS_CLEAN — 1 Low fixed inline (bell date UTC-parse), 2 Medium + 1 Low unfixed for steer.
Peer adversarial review (ag-review --wait, no hang): 3 findings — TLS verify=False deferred (repo-wide convention), TS nullability FIXED, per-tick extraction dedup FIXED (+1 test). review.md + STATUS Deferred Reviews updated. Phase → Steering.

**Build complete 2026-07-23.** Stream B (subagent): 9 files, vitest 7/7, tsc clean — committed. Stream A (inline): 13 files, 36/36 new unit tests (pytest), all 5 endpoints verified registered via OpenAPI — committed. Notes: (1) test_reminders' 6 pre-existing failures are env-caused (AsyncMock children are AsyncMock on Py3.12 → `result.scalars()` returns coroutine) — untouched code, fails identically without burst changes; (2) test_regression/test_guardrails are live-backend suites (conftest: uvicorn on 8001 required) — 360 connection errors without a server, deferred to probe; (3) black not installed in env — formatting verified by compile + style match only; (4) apscheduler installed via pip3 --user --break-system-packages (matches existing user-site deps); (5) # AMBIGUITY in transcript_poll_service.py retry-sweep fan-out: recovery proposals scoped to ingesting user + users whose scan window still covers the meeting (no durable user↔transcript association exists for other attendees when extraction fails beyond the 1h overlap).
