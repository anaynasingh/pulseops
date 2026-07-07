# Round 1 plan (Codex-absorbed)

The full absorbed plan is the canonical `AIGILE_PLAN/current/plan.md`. Round 1
absorbed all 6 Codex round-0 findings as implementation-spec tightenings (no
stream/scope change). Deltas vs round_0/plan.md:

- **C3 (deps.py logic):** decisive gate is "is the token a JWT" (`decode_token`
  returns non-None), NOT "did it yield a user". Valid-but-bad JWTs (missing sub,
  inactive/missing user) 401 in the JWT branch with NO api_key fallback. Invariant
  code comment required.
- **C4 (cache):** api_key path does ONE DB lookup per request, never reads the
  user_id-keyed cache; still WRITES the cache for later JWT reuse. Overstated
  "hits cache" claim removed. Token-keyed cache deferred.
- **C2 + C5 (test fixture):** reuse existing `_run` + `AsyncSessionLocal` async
  pattern (test_regression.py:342-387), NOT `asyncio.run()`. Synthetic marker
  emails `_reg_apikey_active@pulseops.test` / `_reg_apikey_disabled@pulseops.test`,
  create-only, marker-gated teardown, own-rows-only. `test_disabled_user_key_rejected`
  added.
- **C1 (sequencing):** streams build-independent but NOT runtime-independent;
  A must be live before B reaches users; ship together.
- **C6 (settings path):** `mcp-servers/claude-settings.json` is the template users
  copy into their user-local `.claude/settings.json`; documented in SETUP.md.

See `round_0/codex.md` and `round_0/determination.md` for the full findings and
per-finding rationale.
