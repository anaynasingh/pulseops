## Burst Plan

**Goal:** Replace email/password authentication with Microsoft Azure AD OAuth SSO, while preserving the existing JWT bearer token pattern for all downstream API calls.

**CHARTER alignment:** Hard Spec "JWT auth with bearer tokens" (maintained — our own JWT is still issued post-OAuth); Hard Spec "MCP servers for external integrations (M365)" (Azure app registration created for auth will be reused for M365 Graph API access).

**Streams:** Two parallel streams. The interface contract is lockable upfront: the backend token endpoint returns `{"access_token": string, "token_type": "bearer", "user": UserOut}` — identical shape to the existing `TokenResponse`, so the frontend stores it exactly as today.

### Stream A - Backend OAuth + Migration

- Scope (files WRITTEN):
  - `backend/app/api/v1/auth.py`
  - `backend/app/core/config.py`
  - `backend/app/models/models.py`
  - `backend/app/schemas/schemas.py`
  - `backend/.env.example`
  - `backend/requirements.txt`
  - `database/002_microsoft_oauth.sql`

- Excluded: `backend/app/core/security.py` (unchanged), `backend/app/core/deps.py` (unchanged)

- Exports (interface contract):
  - `GET /api/v1/auth/microsoft/login` → `302` redirect to Microsoft authorize URL
  - `GET /api/v1/auth/microsoft/callback?code=...&state=...` → `302 → ${FRONTEND_URL}/callback?code=<uuid>`
  - `POST /api/v1/auth/microsoft/token` → `TokenResponse` JSON (exchanges short-lived code for JWT)
  - `GET /api/v1/auth/me` → `UserOut` (unchanged)
  - Removed: `POST /api/v1/auth/login`, `POST /api/v1/auth/signup`

- Dependency: none
- Builder: claude

### Stream B - Frontend Login Replacement

- Scope (files WRITTEN):
  - `frontend/app/(auth)/login/page.tsx`
  - `frontend/app/(auth)/signup/page.tsx`
  - `frontend/lib/api.ts`
  - `frontend/app/(auth)/callback/page.tsx` (new)

- Excluded: `frontend/lib/store.ts` (unchanged), `frontend/app/(dashboard)/layout.tsx` (unchanged)

- Exports: none
- Dependency: Stream A interface contract (lockable at plan approval)
- Builder: claude

**Shared files:** none

**Integration gate:** Stream A callback redirects to `${FRONTEND_URL}/callback?code=<uuid>`. Stream B's new `callback/page.tsx` catches the `code` query param, calls `POST /api/v1/auth/microsoft/token` with `{"code": "<uuid>"}`, receives `TokenResponse`, calls `setAuth(user, access_token)`, pushes to `/dashboard`.

**Deferred to next Burst:** Token refresh, role-based provisioning from Azure AD groups, M365 Graph access.

---

## Implementation Notes

### OAuth flow (end-to-end)

1. User lands on `/login`. Page renders a single "Sign in with Microsoft" button. No email/password fields.
2. Button navigates to `GET /api/v1/auth/microsoft/login`. Backend builds the Microsoft authorize URL using `AZURE_CLIENT_ID`, `AZURE_TENANT_ID=common`, and `AZURE_REDIRECT_URI` (set to the backend callback, e.g. `http://localhost:8001/api/v1/auth/microsoft/callback`). A CSRF `state` value (UUID) is stored in a short-lived server-side dict keyed by state value (TTL: 300 s). Response is `302` to Microsoft.
3. Microsoft authenticates the user and redirects to `GET /api/v1/auth/microsoft/callback?code=<ms_code>&state=<state>`. Backend:
   a. Validates `state` against the server-side dict; removes it (one-time use). On mismatch → `302 → ${FRONTEND_URL}/login?error=invalid_state`.
   b. Exchanges `ms_code` for Microsoft tokens via `msal.ConfidentialClientApplication.acquire_token_by_authorization_code(code, scopes, redirect_uri)`.
   c. Calls `GET https://graph.microsoft.com/v1.0/me` with the MS access token to fetch `mail` (or `userPrincipalName`) and `displayName`.
   d. Lowercases the email. Upserts the `users` row: look up by `ms_oid` first, then lowercased `email`. On first MS login of existing user, sets `ms_oid`. Creates user with `password_hash=NULL` if new.
   e. Checks `user.is_active`. If false → `302 → ${FRONTEND_URL}/login?error=account_disabled`.
   f. Issues PulseOps JWT via existing `create_access_token({"sub": str(user.id)})`.
   g. Generates a UUID exchange code, stores `{code: jwt_string, expiry: time.time() + 60}` in in-memory dict.
   h. Redirects: `302 → ${FRONTEND_URL}/callback?code=<uuid>`.
   i. All other error paths → `302 → ${FRONTEND_URL}/login?error=<message>`.

4. Frontend `callback/page.tsx` mounts, reads `?code` from the URL. Calls `POST /api/v1/auth/microsoft/token` with `{"code": "<uuid>"}`. On success: calls `setAuth(user, access_token)`, pushes to `/dashboard`. On failure: pushes to `/login?error=auth_failed`.

5. `POST /api/v1/auth/microsoft/token`: backend looks up the code in the exchange store. If not found or expired → 401. If found → pops it (one-time use), returns `TokenResponse`.

### API surface

| Method | Path | Auth required | Description |
|--------|------|---------------|-------------|
| GET | `/api/v1/auth/microsoft/login` | No | Initiates OAuth flow, redirects to Microsoft |
| GET | `/api/v1/auth/microsoft/callback` | No (browser redirect from MS) | Handles MS callback, issues exchange code |
| POST | `/api/v1/auth/microsoft/token` | No | Exchanges code for `TokenResponse` |
| GET | `/api/v1/auth/me` | Bearer JWT | Returns `UserOut` (unchanged) |

Removed: `POST /api/v1/auth/login`, `POST /api/v1/auth/signup`.

### Exchange-code store

Module-level dict on the auth router:

```python
_exchange_store: dict[str, tuple[str, float]] = {}
# key = uuid str, value = (jwt_string, expiry_unix_timestamp)
```

Cleanup on read: handler pops the key after returning. Expired entries rejected when `expiry < time.time()`. Single-process, low-concurrency — acceptable for burst scope.

### Schema changes (`database/002_microsoft_oauth.sql`)

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS ms_oid TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_ms_oid ON users (ms_oid) WHERE ms_oid IS NOT NULL;
```

Partial unique index (not column-level `UNIQUE`) to allow multiple `NULL` values for users who have not yet linked a Microsoft account.

### Config additions (`backend/app/core/config.py`)

```python
AZURE_CLIENT_ID: str = ""
AZURE_CLIENT_SECRET: str = ""
AZURE_TENANT_ID: str = "common"
AZURE_REDIRECT_URI: str = "http://localhost:8001/api/v1/auth/microsoft/callback"
FRONTEND_URL: str = "http://localhost:3000"
```

### New dependency (`backend/requirements.txt`)

```
msal==1.28.0
```

### Frontend changes

- `frontend/app/(auth)/login/page.tsx`: single "Sign in with Microsoft" button. Reads `?error` via `useSearchParams()` and displays in error banner. No form.
- `frontend/app/(auth)/signup/page.tsx`: renders redirect to `/login` with SSO note. No form, no API call.
- `frontend/app/(auth)/callback/page.tsx` (new): reads `?code`, calls `authApi.exchangeCode(code)`, on success calls `setAuth` and pushes to `/dashboard`. Renders only a loading state.
- `frontend/lib/api.ts`: remove `login`, `signup`; add `exchangeCode: (code: string) => api.post("/auth/microsoft/token", { code }).then((r) => r.data)`.

### Existing users

Upsert logic: `SELECT WHERE ms_oid = :oid OR email = :email_lower`. If found by email only, updates `ms_oid`. Requires email on MS account to match the email in DB. All existing data preserved.
