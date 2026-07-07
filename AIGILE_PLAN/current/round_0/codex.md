# Codex Plan Challenge — Round 0

Thread: 019f3728-110c-7e22-807b-ddf8d0223741
Exit: 0

**Findings**

1. **False-parallel trap: Stream B is not independently landable (runtime).** REST auth rejects non-JWT before DB lookup today; if Stream B ships first, the rewritten MCP server sends PULSEOPS_API_KEY and every tool 401s until Stream A is live. "Both can land independently" is build-time only.

2. **Shared dev DB seeding unsafe as specified.** Fixed emails + fixed known api_keys; get-or-create could overwrite a real row if the email exists; fixed key could collide; "best-effort cleanup" risks deleting/mutating rows the fixture did not create (esp. disabled-user case).

3. **JWT behavior preservation underspecified for valid-but-bad JWTs.** Current dep has three immediate JWT failures: decode failure, missing `sub`, missing/inactive user. "If JWT path did not yield a user, fall back" conflicts with "exact JWT behavior preserved" — a valid JWT with missing sub / inactive user must still 401, NOT fall through to api_key. Case enumeration omits these; no JWT regression test.

4. **api-key cache claim not achievable with current cache shape.** `_user_cache` is keyed by user_id and read BEFORE DB lookup. An api-key request can't know user_id until after `select(...where api_key==token)`, so every api-key request hits the DB regardless. Claiming "subsequent requests hit cache" is false unless a token→user mapping is added (different key space).

5. **Async DB fixture loop/pool lifecycle risk.** This module ALREADY uses `asyncio.new_event_loop().run_until_complete()` (`_run`, test_regression.py:342) with `AsyncSessionLocal` for intake seeding/cleanup. Reusing the same async engine across multiple event loops in one pytest process can be intermittent. "Same pattern as seed_june11.py" is a weak comparison (one-shot script vs multi-fixture pytest module).

6. **Claude settings path ambiguous.** Scoped file is `mcp-servers/claude-settings.json`, but SETUP.md tells users Claude Code uses `.claude/settings.json` (lines 36, 123). Plan doesn't verify which file Claude actually consumes.

**Confirmed checks (no finding)**
- `server.py` has 14 `_request` call sites; all pass only method/path/params/json_body — signature-preserving rewrite needs no call-site edits.
- FastAPI bearer parsing rejects empty/whitespace-only `Bearer` credentials BEFORE reaching a `User.api_key == ""` query. The empty-token test should assert 401 only, not the internal fallback path.
