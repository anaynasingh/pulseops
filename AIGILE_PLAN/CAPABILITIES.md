## Discovered Capabilities

<!-- Promoted from HISTORY learnings via probe gate. -->
<!-- Format: - [date] insight - burst: <name> -->

- [2026-06-25] The AI assistant is now actionable at the individual-task level: /ai/chat builds per-user task context (open/overdue/due-today/due-week/urgent/high counts + relevance-sorted listing), so it can answer "what should I focus on today / my overdue / my top priorities" with real data, not just project summaries - burst: assistant-task-prompts
- [2026-06-26] AI Intake is now end-to-end functional: confirm classifies project-vs-task (AI suggestion + user override + parent-project picker), creates real persisted Task rows under a new or existing project, logs activity to both dashboard feeds, and busts the kanban cache so the board reflects new work without a manual reload - burst: intake-functional
- [2026-06-26] AI Intake confirm now auto-assigns ownership: a new project's owner_id and every created task's assigned_to default to the confirming user, with a three-state override contract (omit the field => creator; explicit null => ownerless/unassigned; explicit UUID => that user) via Pydantic model_fields_set. Applies to project Routes 1+3 and the task loop; an existing project's owner (Route 2) is never mutated - burst: intake-default-assignee
- [2026-07-06] MCP + agents authenticate once and stay connected forever: the permanent per-user `User.api_key` is now accepted as a bearer on ALL REST endpoints (not just the hosted SSE path), and the local pulseops MCP server uses it instead of email/password→JWT. SSO users (who have no password) can now use the local MCP at all - burst: mcp-longlived-apikey
- [2026-07-06] Marker-gated synthetic-user seeding against the shared live dev DB is a proven, repeatable test pattern (`seeded_api_keys`: `@pulseops.test` emails, `_run`/`AsyncSessionLocal`, own-rows-only teardown) — lets auth/credential paths be tested without a JWT and without risking real rows, even while the main suite is RED - burst: mcp-longlived-apikey
- [2026-07-06] Two-adversarial-pass verification (completed Codex plan-challenge + Opus build-challenge with fix authority) is a viable ship gate when the Codex code-review gate is environmentally unavailable - burst: mcp-longlived-apikey

