# Orchestrator redirects: mcp-longlived-apikey (redirected from assignable-users-sso follow-up)

## 2026-07-06T13:20:00Z | round_0 | strategic

**Redirect:** Orchestrator abandoned the invoked burst goal (assignable-users-sso follow-up — fix the `GET /users/` password_hash filter) mid-/ag-plan and set a new goal: "I want a system where I connect once and then the MCP stays connected forever. Fuck these JWT tokens."
**AI prior action:** about to run the preflight gate for the assignable-users-sso fix plan.
**Impact:** replaced the entire burst — became `mcp-longlived-apikey` (backend `get_current_user` api_key bearer fallback + local pulseops MCP server switched from email/password→JWT to `PULSEOPS_API_KEY`).
**Evidence at redirect time:** none (frustration-driven); the AI then grounded it by investigation (deps.py was JWT-only; mcp_server.py SSE path already accepted the api_key; the local server's password login was dead for SSO users).

## 2026-07-06T13:35:00Z | round_0 | clarifying

**Redirect:** Orchestrator asked "why do we still need a jwt token?" — challenging the AI's framing that tests needed a JWT to obtain the api_key.
**AI prior action:** had posed a JWT-for-tests decision (mint helper vs manual vs login shim) as a Critical blocker.
**Impact:** dissolved the blocker — the AI reframed to seed a known api_key directly (zero JWT), which became the shipped `TestApiKeyAuth` seeded-fixture approach and clarified the JWT=browser-session / api_key=machine-credential split for the user.

## 2026-07-06T13:45:00Z | round_ship | tactical

**Redirect:** After the Codex adversarial code-review hung twice, Orchestrator directed "recommend proceeding on the two adversarial passes that already completed cleanly."
**AI prior action:** waiting/polling the hung Codex review.
**Impact:** cancelled the hung review; verification accepted on the completed Codex plan-challenge + Opus build-challenge (PASS_CLEAN); steer=SHIP. Endorsed the AI's own recommendation (low counter-AI) but set the verification path.
