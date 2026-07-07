## Burst Plan
**Goal:** Make every PulseOps MCP auth path accept the permanent per-user `User.api_key` as a bearer credential so a user connects once and never re-authenticates.

**CHARTER alignment:** Augments the "JWT auth with bearer tokens" Hard Spec by adding an api_key fallback without removing JWT (existing JWT behaviour fully preserved); supports the MCP/agent-connectivity objective (connect once, stays connected).

**Streams:** Two parallel streams (A: backend, B: local MCP server + docs). File-write sets are pairwise disjoint (verified below), so they build in parallel and are joined at the integration gate.

---

### Stream A - Backend api_key fallback in get_current_user
- Scope (files WRITTEN):
  - `backend/app/core/deps.py`
  - `backend/tests/test_regression.py`
- Excluded: `backend/app/api/v1/mcp_server.py` (already correct — do NOT touch), `backend/app/api/v1/auth.py` (already mints/returns key at `GET /auth/api-key` — no change needed), `backend/app/models/models.py` (column already `String(64)` nullable), `backend/app/core/security.py`
- Exports: no new importable symbol. `get_current_user()` keeps its exact signature `(credentials, db) -> User`. Behaviour contract extended: after JWT decode fails, fall back to `select(User).where(User.api_key == credentials.credentials)` with the same `is_active` guard.
- Dependency: none
- Builder: claude

**Consistency decision (justified):** Duplicate the ~6-line api_key fallback inline in `deps.py` rather than extracting a shared helper. Rationale: (1) `mcp_server.py._authenticate()` returns `User | None` and opens its own `AsyncSessionLocal()`, while `deps.py` receives an injected `db` session and raises `HTTPException` — the surrounding shapes differ, so a shared helper would need to abstract session-source and error-mode, growing larger than the duplication it removes. (2) A shared symbol in `security.py` would couple `deps.py` and `mcp_server.py`, and Stream A already excludes `mcp_server.py` to keep the blast radius to one backend module. The duplication is trivial and the two call sites legitimately differ. Do NOT modify `mcp_server.py`.

**Implementation detail for deps.py:** Restructure so a missing/invalid JWT no longer raises immediately. New order inside `get_current_user`:
1. `if not credentials:` → 401 "Not authenticated" (unchanged).
2. `token = credentials.credentials`. Try `payload = decode_token(token)`. If payload and `payload.get("sub")` → resolve `user_id`, use existing cache read (`_user_cache` keyed by `user_id`), else DB lookup by `User.id`, cache-populate, return (existing path preserved exactly).
3. If JWT path did not yield a user, fall back: `result = await db.execute(select(User).where(User.api_key == token))`; `user = result.scalar_one_or_none()`; if `user and user.is_active` → cache-populate under `_user_cache[str(user.id)]` then return; else fall through.
4. If neither path resolves → 401.

**Cache interaction (addressed):** The cache is keyed by `user_id`, populated after any successful lookup. The api_key path must populate/read it under `str(user.id)` (same key space as the JWT path) so a user hitting api_key then JWT (or vice-versa) shares one cache entry. Cache lookup on the api_key path is only possible after the DB resolves the user_id, so the first api_key request always does one DB hit; subsequent requests within TTL hit cache. This is consistent and correct — no bypass needed. Note the `is_active` guard is enforced at DB-lookup time; a user deactivated mid-TTL stays cached up to 5 min on either path (pre-existing behaviour, unchanged, not in scope to fix).

**Case enumeration (deps.py auth path):**
- valid JWT, no api_key → resolves via JWT (existing behaviour preserved)
- valid api_key, no JWT / garbage JWT → resolves via api_key (new happy path)
- token that is neither valid JWT nor a matching api_key → 401
- api_key matches a user with `is_active=False` → 401
- missing credentials entirely → 401 (existing)
- empty-string token → `decode_token("")` returns None, `select(...where api_key == "")` matches nothing → 401 (guard: never let an all-NULL/empty api_key column match; empty string is safe since real keys are 43-char tokens, but confirm no seeded user has empty-string api_key)
- malformed/whitespace token → same as "neither valid" → 401

**Test plan (Stream A) — seeded-api_key approach (Orchestrator ruling 2026-07-06):**

The old `login()`/`anayna_token` path is DEAD — `test_regression.py:21-24` POSTs to `/auth/login`, removed in commit `271707b` when SSO landed. The whole existing suite is red as a result. **This burst does NOT fix that pre-existing breakage** (deferred). Instead we verify the new api_key path with **zero JWT dependency** by seeding a known api_key directly.

- **New fixture** (in `test_regression.py`, module scope): `seeded_api_key`. Uses `asyncio.run()` + `AsyncSessionLocal` (same pattern as `backend/seed_june11.py`) to upsert a dedicated test user `mcp-test@prospect33.com` with `is_active=True` and a KNOWN `api_key` constant. Yields that key. No `/auth/login`, no token minting.
- **New tests** under a new `TestApiKeyAuth` class (do NOT reuse `TestAuthentication`, whose fixtures are dead): (1) `test_api_key_authenticates` — `GET /auth/me` with the seeded key → 200; (2) `test_api_key_works_on_protected_endpoint` — `GET /projects/` with the seeded key → 200; (3) `test_bad_token_rejected` — random non-existent 43-char key → 401; (4) `test_empty_token_rejected` → 401; (5) `test_no_token_rejected` → 401.
- **`is_active=False` case:** fixture also seeds `mcp-test-disabled@prospect33.com` (is_active=False, known key); `test_disabled_user_key_rejected` → 401. Fully automatable.
- **JWT regression:** no non-interactive JWT source post-SSO, so no JWT-path test is added; the `deps.py` diff must PRESERVE the JWT branch unchanged (code-review + Codex verified; `# AMBIGUITY:` the uncovered JWT happy-path).
- **Idempotency:** fixture get-or-creates and re-sets the known key each run; dev DB only, never prod.

---

### Stream B - Local MCP server + docs switch to PULSEOPS_API_KEY
- Scope (files WRITTEN):
  - `mcp-servers/pulseops/server.py`
  - `mcp-servers/pulseops/.env.example`
  - `mcp-servers/claude-settings.json`
  - `mcp-servers/SETUP.md`
- Excluded: everything under `mcp-servers/m365/` and every M365 section of SETUP.md and claude-settings.json (M365 is Azure AD delegated OAuth — OUT OF SCOPE, must not change); all backend files
- Exports: MCP server now reads `PULSEOPS_API_KEY` env var and sends `Authorization: Bearer <api_key>` on every request. No login, no 401-retry.
- Dependency: none at build time (server.py does not import backend code). Runtime-depends on Stream A being live for end-to-end verification — handled at the integration gate.
- Builder: claude

**Implementation detail for server.py (verified against read):**
- Replace module-level `EMAIL`/`PASSWORD` (lines 24-25) with `API_KEY = os.getenv("PULSEOPS_API_KEY", "")`.
- Remove the `_token` global (line 30), `_login()` (lines 33-45), and `_get_token()` (lines 48-52).
- Rewrite `_request()` (lines 55-87): drop `global _token`, build `headers = {"Authorization": f"Bearer {API_KEY}"}` directly, remove the entire `if resp.status_code == 401:` re-login/retry branch (lines 75-86), return `resp`. Signature `_request(method, path, *, params=None, json_body=None)` is unchanged, so all ~14 call sites (`_list_projects` … `_get_gantt`) need no edits — verified they only pass method/path/params/json_body.
- Optional hardening: in `main()` (line 789), if `not API_KEY`, print a clear "PULSEOPS_API_KEY not set — grab it from PulseOps Settings → MCP Token" warning to stderr before serving. Low risk, single-line, recommended.

**`.env.example` rewrite:**
```
PULSEOPS_API_URL=http://localhost:8001/api/v1
PULSEOPS_API_KEY=your-api-key-from-pulseops-settings
```
(Remove PULSEOPS_EMAIL and PULSEOPS_PASSWORD.)

**`claude-settings.json` rewrite:** In the `pulseops.env` block replace `PULSEOPS_EMAIL` and `PULSEOPS_PASSWORD` with a single `PULSEOPS_API_KEY: ""`. Leave `PULSEOPS_API_URL` and the entire `m365` block byte-for-byte unchanged.

**SETUP.md rewrite (targeted, M365 untouched):**
- "PulseOps MCP Setup" step 2 (lines 19-28): change to "grab your API key from PulseOps Settings → MCP Token" and show the two-line `.env` with `PULSEOPS_API_KEY`.
- Step 4 (lines 36-37): reference `PULSEOPS_API_KEY` instead of email/password.
- "Configuring Claude Code" JSON block (lines 127-149): update the `pulseops` env keys to `PULSEOPS_API_KEY`; leave the `m365` object unchanged.
- Troubleshooting `401 Unauthorized` row (line 177): change fix text to "Re-grab your API key from PulseOps Settings → MCP Token and update `.env`/`settings.json`."
- Do NOT touch lines 41-119 (Microsoft 365 section) or the M365 troubleshooting rows.

**Case enumeration (Stream B):** api_key present and valid → all tools authenticate; api_key missing/empty → backend returns 401, surfaced by existing `_error(resp.text, resp.status_code)` in each `_dispatch` handler (no crash — verified handlers already check `resp.status_code`); api_key present but wrong → 401 surfaced identically. No 401-retry loop remains, so a bad key fails fast with a clear HTTP 401 message rather than an infinite relogin.

**Test plan (Stream B):** No unit tests exist for the local stdio server (`test_regression.py` MCP cases at lines 324-330 target the SSE server, not this one). Verification is manual: export `PULSEOPS_API_KEY=<key from /auth/api-key>`, run `python mcp-servers/pulseops/server.py`, confirm "PulseOps MCP server ready", then exercise one read tool (e.g. `list_projects`) against the live backend and confirm a 200 payload. Flag with `# AMBIGUITY:` that this stream's coverage is manual-only.

---

**Shared files:** none. Stream A writes only under `backend/`; Stream B writes only under `mcp-servers/`. Write-sets are disjoint — safe to build in parallel in separate checkouts.

**Integration gate (backend + local server verified together):**
1. Stream A merged first is preferred but not required for build; both can land independently.
2. Start local backend (`uvicorn app.main:app --port 8001`) with Stream A's deps.py change.
3. Obtain a JWT. NOTE: `/auth/login` DOES NOT EXIST (removed in commit 271707b when SSO landed) — the only JWT source is the Microsoft SSO flow (`/auth/microsoft/login` → callback → `/auth/microsoft/token`) or a directly-seeded/minted token. Then call `GET /auth/api-key`, copy the key.
4. Backend check: `curl -H "Authorization: Bearer <api_key>" localhost:8001/api/v1/auth/me` returns 200 (proves Stream A).
5. Local-server check: run Stream B's `server.py` with `PULSEOPS_API_KEY=<key>`, invoke `list_projects` / `get_dashboard`, confirm 200 payloads (proves Stream B end-to-end on top of Stream A).
6. Regression: `pytest backend/tests/test_regression.py::TestApiKeyAuth -v` passes (new api_key cases green; the seeded fixture creates the test user). NOTE: the rest of the suite is pre-existing RED (dead `/auth/login` fixtures) — not this burst's regression to fix.
7. Confirm M365 block in `claude-settings.json` and the M365 section of `SETUP.md` are byte-identical to pre-burst (git diff shows no M365 lines touched).

**Security ruling (Orchestrator accepted 2026-07-06):** The permanent, un-revocable `api_key` now authenticating all REST endpoints is an ACCEPTED documented risk. Rationale: the same `api_key` is already a full-access credential via the hosted SSE MCP path (`mcp_server.py`), so extending it to REST is the same key with the same per-user RBAC (`require_admin`/`require_writer` still gate on the resolved user's role — a viewer's key stays view-only). Incremental surface is marginal. Mitigation today = deactivate the user; a proper rotate/revoke kill-switch is deferred (below).

**Deferred to next Burst:**
- Rotate/revoke `api_key` endpoint (explicitly out of scope this burst; the accepted-risk kill-switch).
- Repair the pre-existing RED regression suite: `login()`/`anayna_token`/`stephen_token` fixtures POST to the deleted `/auth/login` (removed at SSO, commit `271707b`) — the whole `test_regression.py` suite currently 404s. NOT caused by this burst; needs a post-SSO non-interactive JWT-for-tests strategy.
- M365 `offline_access` / delegated-OAuth verification (M365 cannot use an API key).
- Fixing the mid-TTL deactivation staleness in `_user_cache` (pre-existing, both auth paths).
- Any `users.py` domain-guard anchor work.
- Backfilling automated tests for the local stdio MCP server (currently manual-only).
