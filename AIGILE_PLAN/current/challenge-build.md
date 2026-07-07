# Build Adversarial Challenge

## Round 1 — 2026-07-06
**Model:** opus (Prosecution frame)

## Fixed
| Sev | Vector | Location | Defect | Fix applied |
|-----|--------|----------|--------|-------------|
| — | — | — | None | — |

## Findings (unfixed — require gate decision)
| Sev | Vector | Location | Indictment |
|-----|--------|----------|------------|
| — | — | — | No defects found |

## Verdict
Prosecuted all three vectors against the actual code; no indictment sustained.

- **deps.py:37-68** — JWT isolation holds: `decode_token` returns a dict for any signature-valid token, None only on JWTError; `if payload is not None:` captures every valid JWT (missing sub → 401, missing/inactive user → 401), none fall through to api_key. JWT happy path byte-equivalent to pre-diff. api_key branch does one DB lookup, writes `_user_cache[str(user.id)]`; `time`/`select`/`User` imported; empty-token `if token:` guard present and backstops FastAPI empty-credential.
- **test_regression.py:685-771** — seed/cleanup imports valid; `User(...)` fields all exist; `UserRole.contributor` real; teardown marker-gated to the two `@pulseops.test` emails (no real row deletable); cleanup-first guarantees fresh is_active=False; api_key constants 43 chars (< String(64)); `_run` loop pattern is pre-existing repo standard.
- **server.py** — no surviving reference to `_login`/`_get_token`/`_token`/`EMAIL`/`PASSWORD`; `_request` signature + return intact; all callers use `.status_code`/`.json()`/`.text` unaffected; `httpx`/`Any`/`sys` still imported; py_compile passes.
- **claude-settings.json / SETUP.md / .env.example** — JSON valid; m365 block byte-unchanged; no residual EMAIL/PASSWORD in PulseOps section; M365 doc section untouched.
