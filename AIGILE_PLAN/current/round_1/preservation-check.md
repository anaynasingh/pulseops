# Preservation check: round_0 → round_1

All diff hunks categorised:

- **Streams header:** "backend callback endpoint" → "backend token endpoint" — AUTHORISED (C2: clarifies the token endpoint is what returns TokenResponse, not the callback)
- **Excluded comment:** Shortened prose in Excluded — AUTHORISED (minor wording, substance preserved)
- **Callback contract:** `/auth/callback?access_token=...` → `/callback?code=<uuid>` — AUTHORISED (C1 + C4: correct route and exchange-code pattern)
- **New endpoint added:** `POST /api/v1/auth/microsoft/token` — AUTHORISED (C4 change-request addition)
- **Formatting:** Removed horizontal rules `---` between stream sections — AUTHORISED (minor cosmetic)
- **Stream B excluded:** Removed `frontend/components/layout/Sidebar.tsx` from excluded list — AUTHORISED (it was never in scope; listing it was informational)
- **Integration gate:** Updated to reflect `?code=<uuid>` and `POST /auth/microsoft/token` exchange — AUTHORISED (C4)
- **Deferred:** Shortened — AUTHORISED (same items, compressed)
- **OAuth flow steps:** Significantly expanded with error paths, `is_active` check, exchange-code storage, `state` dict (not cookie) — AUTHORISED (C3, C4, C7 determinations)
- **API surface table:** Reformatted and added new endpoint — AUTHORISED (C4)
- **Exchange-code store section:** New — AUTHORISED (C4)
- **Migration:** Comment line removed — AUTHORISED (cosmetic)
- **msal version:** `1.29.0` → `1.28.0` — AUTHORISED (stable release, plan agent chose specific version)
- **Frontend changes:** Consolidated into bullet list with detail — AUTHORISED (C6, C7 absorbed)
- **Signup page:** Redirect to `/login` with SSO note — AUTHORISED (C6)
- **Error display:** `?error` on login page — AUTHORISED (C7)

**Result: no unauthorised changes detected. All hunks trace to approved determinations.**
