# Iteration log: claude-bridge-live

## Round 0 (planned 2026-07-07)

**Plan written:** 2026-07-07
**Plan agent model:** fable
**ag-challenge (Step 5.7):** PASS_CLEAN at round 3 (opus Prosecution). R1: CRITICAL 0.0.0.0-vs-IPv6 bind fixed (higher-model); .dockerignore added inline. R2: HIGH local-exposure regression → Orchestrator ruling: code default 127.0.0.1 + Dockerfile ENV BRIDGE_HOST=::; gate IPv6-curl + .dockerignore constraints folded in. R3: verified clean; curl-context MEDIUM fixed.
**Codex challenge:** round 0 done 2026-07-07, thread 019f3ce5-fbfb-7311-b016-7531c8709799. 0 CRITICAL / 3 HIGH / 2 MEDIUM / 1 LOW. Orchestrator confirmed dispositions (5 ABSORB-PLAN, 1 BUILD-NOTE); round_0/determination.md + change-request.md written; round-1 revision by fable Plan agent; preservation check PASS (6/6 hunks authorised).

## Round 1 (2026-07-07)

**Plan revised:** 2026-07-07 (round_1/plan.md, copies identical, lint clean)
**Codex challenge:** round 1 done (resumed, same thread; turn 019f3d05-fc90-7f02-92a1-04b247fe564e). 0 CRITICAL / 2 HIGH / 1 MEDIUM / 1 LOW — C3/C4/C6 absorbed clean; C1/C2 partially closed. Orchestrator confirmed 4× ABSORB-PLAN; round-2 revision by fable Plan agent; preservation PASS (4/4 hunks).

## Round 2 (2026-07-08)

**Codex challenge:** round 2 done (resumed; turn 019f3fcc-afe8-7f42-874f-b16e602be61e). 1 HIGH / 1 MEDIUM / 1 LOW (guard-vs-seeding-runbook conflict; smoke lacks m365 tool call; case (6) wording). Orchestrator confirmed 3× ABSORB-PLAN; round-3 revision applied as orchestrator-direct targeted edits (4 whitelisted lines — see round_2/determination.md mechanics note); preservation PASS (4/4 hunks); lint clean.

## Round 3 (2026-07-08)

**Codex challenge:** round 3 done (resumed; turn 019f3fd0-d2e6-7733-932b-690ef99ba67c). Verdict: **"Plan is ready."** R2-1/R2-2/R2-3 all addressed; no new CRITICAL/HIGH.

## Approved 2026-07-08

**Round approved:** 3
**Burst base:** bb3c8d20c428fae00057b8363a1f5f467396516e
**Approved by:** Orchestrator ("go")
**Risk-tier floors:** A=2, B=2, C=1 (declared at floor)

## Build 2026-07-08

**Stream A:** COMPLETE @ 78306ca (bridge.py binding/env + m365 wiring; m365 server headless guard + M365_TOKEN_CACHE; requirements pins; .env.example)
**Stream B:** COMPLETE @ 13ed87a (Dockerfile with ENV BRIDGE_HOST=:: baked; railway.json DOCKERFILE builder; constrained .dockerignore)
**Stream C:** COMPLETE @ 4135ba2 (README Railway runbook + M365 seeding; backend/.env.example; CHARTER 3 amendments)
**Integration gate (local, no docker):** PASS — health 200; bare run binds 127.0.0.1 only; malformed PORT fail-fast; missing PULSEOPS_API_KEY RuntimeError; m365 config included/omitted + CLIENT_SECRET key omitted when empty; headless M365AuthError fires with runbook message; allowed/disallowed tools exact; no ANTHROPIC_API_KEY in diff; README env names match os.getenv reads; CHARTER Hard Specs amended exactly once.
**Integration gate (docker-dependent):** PENDING — docker build, in-container [::]:PORT bind (docker exec curl [::1]), claude --version in image, /chat smoke with real secrets forcing pulseops + m365 tool calls. Docker unavailable in this WSL distro (Docker Desktop integration off). # AMBIGUITY: in-container claude -p headless auth with CLAUDE_CODE_OAUTH_TOKEN remains unverified until the docker smoke or the Railway deploy.
