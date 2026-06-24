## Burst Plan

**Goal:** Replace email/password authentication with Microsoft Azure AD OAuth SSO, while preserving the existing JWT bearer token pattern for all downstream API calls.

**CHARTER alignment:** Hard Spec "JWT auth with bearer tokens" (maintained — our own JWT is still issued post-OAuth); Hard Spec "MCP servers for external integrations (M365)" (Azure app registration created for auth will be reused for M365 Graph API access).

**Streams:** Two parallel streams. The interface contract is lockable upfront: the backend callback endpoint returns `{"access_token": string, "token_type": "bearer", "user": UserOut}` — identical shape to the existing `TokenResponse`, so the frontend stores it exactly as today.

---

### Stream A - Backend OAuth + Migration

- Scope (files WRITTEN):
  - `backend/app/api/v1/auth.py`
  - `backend/app/core/config.py`
  - `backend/app/models/models.py`
  - `backend/app/schemas/schemas.py`
  - `backend/.env.example`
  - `backend/requirements.txt`
  - `database/002_microsoft_oauth.sql`

- Excluded: `backend/app/core/security.py` (unchanged — `create_access_token` / `decode_token` not touched), `backend/app/core/deps.py` (unchanged — `get_current_user` works on our JWT, not MS tokens)

- Exports (interface contract):
  - `GET /api/v1/auth/microsoft/login` → `302` redirect to Microsoft authorize URL
  - `GET /api/v1/auth/microsoft/callback?code=...&state=...` → redirects to `${FRONTEND_URL}/auth/callback?access_token=...&user=...`
  - `GET /api/v1/auth/me` → `UserOut` (unchanged)
  - Removed: `POST /api/v1/auth/login`, `POST /api/v1/auth/signup`

- Dependency: none

- Builder: claude

---

### Stream B - Frontend Login Replacement

- Scope (files WRITTEN):
  - `frontend/app/(auth)/login/page.tsx`
  - `frontend/app/(auth)/signup/page.tsx`
  - `frontend/lib/api.ts`
  - `frontend/app/(auth)/callback/page.tsx` (new)

- Excluded: `frontend/lib/store.ts` (unchanged), `frontend/app/(dashboard)/layout.tsx` (unchanged), `frontend/components/layout/Sidebar.tsx` (unchanged)

- Exports: none (pure consumer of Stream A contract)

- Dependency: Stream A interface contract (lockable at plan approval — no code dependency)

- Builder: claude

---

**Shared files:** none

**Integration gate:** Stream A callback redirects to `${FRONTEND_URL}/auth/callback?access_token=...&user=...`. Stream B's new `callback/page.tsx` catches the query params, calls `setAuth(user, token)`, pushes to `/dashboard`. Full browser test: login page → "Sign in with Microsoft" → Microsoft consent → redirect back → dashboard loads with authenticated user.

**Deferred to next Burst:** Token refresh (MS tokens not stored; our JWT expiry of 7 days is adequate). Role-based provisioning from Azure AD groups. M365 Graph access reusing the same Azure app registration.

---

## Implementation Notes

### Exact OAuth flow (numbered steps)

1. User visits `/login`, sees a single "Sign in with Microsoft" button.
2. User clicks the button. Frontend navigates `window.location.href = API_URL + "/api/v1/auth/microsoft/login"` (full-page redirect, not XHR).
3. FastAPI `GET /auth/microsoft/login`: uses `msal.ConfidentialClientApplication` to build the Microsoft authorization URL with a `state` CSRF token (stored in a signed HttpOnly cookie), returns `RedirectResponse` to Microsoft.
4. Microsoft presents login/consent UI.
5. Microsoft redirects to `GET /api/v1/auth/microsoft/callback?code=...&state=...`.
6. FastAPI callback: validates `state` cookie (CSRF), calls `msal_app.acquire_token_by_authorization_code(code, scopes, redirect_uri)`.
7. Extract user profile from ID token claims: `oid`, `email`/`preferred_username`, `name`.
8. Upsert `User` in DB: look up by `ms_oid` first, then `email` (for existing password-era users). On first MS login of existing user, sets `ms_oid`. Creates user with `password_hash=NULL` if new.
9. Issue our own JWT: `create_access_token({"sub": str(user.id)})`.
10. Redirect to `${FRONTEND_URL}/auth/callback?access_token=<jwt>&user=<json-encoded-UserOut>`.

### New environment variables

```
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=common
AZURE_REDIRECT_URI=http://localhost:8001/api/v1/auth/microsoft/callback
FRONTEND_URL=http://localhost:3000
```

### New Python packages

```
msal==1.29.0
```

Add to `backend/requirements.txt`.

### API surface

| Endpoint | Status | Notes |
|----------|--------|-------|
| `GET /api/v1/auth/microsoft/login` | NEW | Browser redirect to Microsoft |
| `GET /api/v1/auth/microsoft/callback` | NEW | OAuth code exchange, redirects to frontend |
| `GET /api/v1/auth/me` | UNCHANGED | |
| `POST /api/v1/auth/login` | REMOVED | |
| `POST /api/v1/auth/signup` | REMOVED | |

### Migration: `database/002_microsoft_oauth.sql`

```sql
-- 002_microsoft_oauth.sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS ms_oid TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_ms_oid ON users (ms_oid) WHERE ms_oid IS NOT NULL;
```

### ORM model update

Add to `User` class in `backend/app/models/models.py`:
```python
ms_oid: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
```
Uniqueness enforced via partial index in migration, not `unique=True` on the column.

### Existing users

Upsert logic: `SELECT user WHERE ms_oid = :oid OR email = :email`. If found by email only, updates `ms_oid` on the row — preserving all existing data. Requires email on Microsoft account to match DB email.

### `backend/app/core/config.py` additions

```python
AZURE_CLIENT_ID: str = ""
AZURE_CLIENT_SECRET: str = ""
AZURE_TENANT_ID: str = "common"
AZURE_REDIRECT_URI: str = "http://localhost:8001/api/v1/auth/microsoft/callback"
FRONTEND_URL: str = "http://localhost:3000"
```
