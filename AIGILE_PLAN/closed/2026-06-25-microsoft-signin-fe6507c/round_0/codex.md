**Findings**

- **High: Callback route mismatch.** The plan redirects to `/auth/callback`, but `frontend/app/(auth)/callback/page.tsx` would route as `/callback`, because `(auth)` is a route group. Existing scoped pages confirm this pattern: links use `/signup` and `/login`, not `/auth/signup` or `/auth/login`. OAuth success would likely land on a missing route.

- **High: The callback contract is internally contradictory.** The plan says the backend callback returns the existing `TokenResponse` JSON shape, but also says it redirects with `access_token` and `user` query params. `TokenResponse` is a JSON response model, while the new flow expects URL parsing. This is a false-parallel trap between backend and frontend streams.

- **High: Disabled users can be re-enabled by omission.** Current password login blocks inactive accounts before issuing a JWT. The OAuth sequence says upsert user, then issue JWT, with no `is_active` check. An inactive existing user matched by `ms_oid` or email would regain access.

- **High: JWT-in-query is a credential exposure risk.** Current auth returns the JWT in a response body; the plan moves it into the redirect URL. That exposes it to browser history, logs, referrers, and back-button recovery. The planned `user=<json>` also has unspecified encoding for `UUID` and `datetime` fields in `UserOut`.

- **Medium: Microsoft identity binding is under-specified.** The plan uses `AZURE_TENANT_ID=common`, looks up by `ms_oid`, then falls back to email. With `User.email` unique and default contributor role, the plan lacks acceptance criteria for allowed tenants/domains, personal Microsoft accounts, absent or differing email claims, case normalization, and account-linking safety.

- **Medium: `/signup` behavior is not defined after removing backend signup.** The existing signup page posts to `/auth/signup`, and login links users there. The plan scopes the signup page but does not define whether it redirects to SSO, becomes unavailable, or is removed.

- **Medium: OAuth error paths have no frontend/backend acceptance contract.** Current login has inline error handling. The OAuth plan only specifies the success callback with `code` and `state`; it does not define behavior for Microsoft `error`, missing state cookie, token exchange failure, inactive user, or malformed user claims.

No patches were written or proposed.

Thread ID: 019ef3d5-78d1-7ae1-9dd4-330df371d912
