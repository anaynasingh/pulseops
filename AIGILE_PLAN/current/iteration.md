# Iteration log: mcp-longlived-apikey

## Round 0 (planned 2026-07-06)

**Plan written:** 2026-07-06
**Plan agent model:** opus
**ag-challenge (Step 5.7):** Round 1, opus/Prosecution. 2 Critical (both DESIGN, resolved by Orchestrator ruling: seeded-api_key tests + risk accepted). Gate: PASS_CLEAN. See challenge-plan.md / challenge-decision.md.
**Codex challenge (Step 6):** Round 0, thread 019f3728-110c-7e22-807b-ddf8d0223741, exit 0. 6 findings (2 MED build-note, 3 HIGH + 1 LOW absorbed as spec tightenings). See round_0/codex.md + round_0/determination.md.

## Round 1 (Codex-absorbed 2026-07-06)

**Absorbed:** all 6 Codex findings (C1-C6) into canonical plan.md. No stream/scope change, no Plan-agent re-spawn, Codex not re-run (spec clarifications within reviewed design). See round_1/plan.md for deltas.

## Approved 2026-07-06

**Round approved:** 1
**Burst base:** b93641132e752836f4062e836de5f6887530b997
**Approved by:** Orchestrator ("go")
**Branch:** fix/mcp-longlived-apikey

## Probe 2026-07-06

**Build:** Stream A (deps.py + test_regression.py, commit 66e2a73), Stream B (server.py + .env.example + claude-settings.json + SETUP.md, commit a717fb3). Both COMPLETE.
**Static verify:** py_compile clean; scope clean (declared files only); no AMBIGUITY comments; frontend untouched (UI step N/A).
**Tests:** live TestApiKeyAuth NOT executed (no local backend/.env) — deferred to deploy per repo precedent.
**ag-challenge --build:** Round 1, Opus/Prosecution, PASS_CLEAN (0 findings; line-by-line diff verification). See challenge-build.md.
**Codex adversarial code-review:** SKIPPED — hung twice at context-gathering (review-mr96bcna-u8k6ut, review-mr99fvw0-mdu6t7), no verdict; cancelled. Verification via completed Codex plan-challenge + Opus build-challenge.
**Steer:** SHIP (Orchestrator: proceed on completed adversarial passes).
**Per-stream final:** Stream A COMPLETE (66e2a73); Stream B COMPLETE (a717fb3).
