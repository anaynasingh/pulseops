# Plan Adversarial Challenge

## Round 1 — 2026-07-06
**Model:** opus (Prosecution frame)

## Fixed

| Sev | Vector | Location | Defect | Fix applied |
|-----|--------|----------|--------|-------------|
| High | V2 | plan.md Test plan (Stream A) | Plan named the test class `TestAuth`; actual class in `test_regression.py:100` is `TestAuthentication`. | Corrected to `TestAuthentication`, verified against file. |
| Critical | V2 | plan.md Test plan + Integration gate Step 3 | Plan assumes JWT obtained via `/auth/login` and `anayna_token` fixture. Verified: `/auth/login` was REMOVED in commit `271707b` (SSO replacement). `anayna_token` fixture POSTs to the dead endpoint and 404s. | Added verified BLOCKER note in test plan; corrected Integration gate Step 3; escalated JWT-acquisition-for-tests to the gate. |

## Findings (unfixed — require gate decision)

| Sev | Vector | Location | Indictment |
|-----|--------|----------|------------|
| Critical | V1/V3 | Whole burst premise / test harness | email/password→JWT is ALREADY dead (`/auth/login` removed at SSO landing). The local MCP server's `_login()` and the `anayna_token` test fixture are both already broken. The only path to a JWT is now an interactive browser SSO redirect — the test harness has no non-interactive way to mint one. Requires a JWT-for-tests strategy decision. |
| Critical | V3 | `deps.py` get_current_user + all ~48 `Depends(get_current_user)` sites | Accepting api_key in get_current_user changes the auth contract of EVERY protected REST endpoint, incl. `require_admin`/`require_writer` RBAC. A never-expiring, plaintext, un-revocable bearer now grants full account access across the whole surface. Orchestrator deferred revoke/rotate. Intended per plan, but a Critical documented-risk decision (P33 financial-services): leaked `.env`/`claude-settings.json` = permanent full compromise, no rotation path. |
| Medium | V1 | `deps.py` cache + is_active | 5-min `_user_cache` widens exposure: a deactivated user's api_key still authenticates up to 5 min post-deactivation on all endpoints; with no revoke, deactivation is the only kill switch and it lags 5 min. |
| Low | V2 | plan.md line 35 empty-string guard | "confirm no seeded user has empty-string api_key" is left as an unverified assertion rather than a code guard. `decode_token("")` returning None is confirmed correct, so empty-token→401 holds. |

## Claims that check out (no finding)
- `decode_token` (security.py:34-38) catches `JWTError` → returns None on a non-JWT api_key string. The "JWT decode fails, fall back" logic is valid.
- `User.api_key` is `String(64)` nullable as claimed.
- `.env.example` exists at `mcp-servers/pulseops/.env.example` with EMAIL/PASSWORD.
- Frontend untouched; hosted SSE server (`mcp_server.py`) already implements the identical fallback — "do not touch" exclusion correct.
