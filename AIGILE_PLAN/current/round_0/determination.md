# Round 0 Determination

## C1 — HIGH: Callback route mismatch
**Disposition: ABSORB-PLAN**
The Next.js `(auth)` route group is a layout group only — the URL path does not include `(auth)`. So `frontend/app/(auth)/callback/page.tsx` renders at `/callback`, not `/auth/callback`. Backend `FRONTEND_URL` redirect must target `${FRONTEND_URL}/callback`, not `${FRONTEND_URL}/auth/callback`. The file path for the new page stays correct.

## C2 — HIGH: Callback contract internally contradictory
**Disposition: ABSORB-PLAN**
Remove the `TokenResponse` JSON shape reference from the callback endpoint. The callback endpoint is a browser redirect, not a JSON API response. Its contract is: `302 → ${FRONTEND_URL}/callback?code=<exchange_code>` (after absorbing C4). Clarify this in the plan.

## C3 — HIGH: Disabled users bypass is_active check
**Disposition: ABSORB-PLAN**
After the DB upsert and before issuing a JWT, add: `if not user.is_active: raise HTTPException(403, "Account disabled")`. Mirror the existing password-login check.

## C4 — HIGH: JWT in query param is a credential exposure risk
**Disposition: ABSORB-PLAN**
Replace the direct JWT-in-URL pattern with a short-lived server-side exchange code:
1. After issuing the JWT, store it in an in-memory dict keyed by a UUID exchange code (TTL: 60 seconds).
2. Redirect to `${FRONTEND_URL}/callback?code=<uuid>`.
3. Frontend `callback/page.tsx` calls `POST /api/v1/auth/microsoft/token` with `{"code": "<uuid>"}`.
4. Backend returns `TokenResponse` JSON (access_token + user). Removes the code from the store.
Token never appears in any URL.

## C5 — MED: MS identity binding under-specified
**Disposition: BUILD-NOTE**
Use `AZURE_TENANT_ID=common` for now. Azure app registration restricts allowed tenants at the Azure portal level — no code guard needed. Lowercase-normalize email on upsert (`email.lower()`). Personal MS accounts are blocked at the Azure app registration level.

## C6 — MED: /signup page behavior undefined
**Disposition: ABSORB-PLAN**
The signup page is replaced with a simple redirect to `/login`. No self-signup path exists after this burst — SSO is the only entry point.

## C7 — MED: OAuth error paths have no contract
**Disposition: ABSORB-PLAN**
All failure paths (MS `error` param, missing/invalid state cookie, token exchange failure, inactive user, malformed claims) redirect to `${FRONTEND_URL}/login?error=<message>`. The login page reads `?error` on mount and displays it.

## Rejected alternatives
- Storing JWT in an HttpOnly cookie (avoids URL exposure without the exchange-code round-trip): rejected because the existing downstream API uses `Authorization: Bearer` from localStorage — changing the storage mechanism is a larger refactor than this burst scope.
- Keeping password login as a fallback behind a feature flag: deferred, not in this burst.
