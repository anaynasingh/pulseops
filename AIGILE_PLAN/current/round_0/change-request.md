# Change Request: Round 0 → Round 1

## Additions

- New endpoint: `POST /api/v1/auth/microsoft/token` — exchanges short-lived code for `TokenResponse` JSON. Add to Stream A scope.
- `frontend/app/(auth)/callback/page.tsx` now calls `POST /auth/microsoft/token` instead of reading query params directly. Stream B unchanged (file already in scope).
- Login page reads `?error` query param on mount and displays error message.

## Modifications

- Stream A callback endpoint contract: changes from "redirects with `?access_token=...&user=...`" to "redirects with `?code=<uuid>`". The `TokenResponse` JSON shape reference is removed from this endpoint's contract.
- Backend `FRONTEND_URL` redirect target: `${FRONTEND_URL}/callback` (not `/auth/callback`).
- OAuth upsert logic: add `is_active` check after upsert, before JWT issuance.
- Email normalization: `email.lower()` on all DB lookups and upserts.

## Deletions

- None.

## Cascading consequences

- `backend/app/api/v1/auth.py` is still in Stream A scope — no scope change, but the implementation now includes the exchange-code store and the `/microsoft/token` endpoint.
- `frontend/app/(auth)/callback/page.tsx` is still in Stream B scope — no scope change, but it now calls `POST /auth/microsoft/token` instead of parsing query params.
- All other in-scope files unchanged in scope.
