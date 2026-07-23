## Discovered Capabilities

<!-- Promoted from HISTORY learnings via probe gate. -->
<!-- Format: - [date] insight - burst: <name> -->

- [2026-06-25] The AI assistant is now actionable at the individual-task level: /ai/chat builds per-user task context (open/overdue/due-today/due-week/urgent/high counts + relevance-sorted listing), so it can answer "what should I focus on today / my overdue / my top priorities" with real data, not just project summaries - burst: assistant-task-prompts
- [2026-06-26] AI Intake is now end-to-end functional: confirm classifies project-vs-task (AI suggestion + user override + parent-project picker), creates real persisted Task rows under a new or existing project, logs activity to both dashboard feeds, and busts the kanban cache so the board reflects new work without a manual reload - burst: intake-functional
- [2026-06-26] AI Intake confirm now auto-assigns ownership: a new project's owner_id and every created task's assigned_to default to the confirming user, with a three-state override contract (omit the field => creator; explicit null => ownerless/unassigned; explicit UUID => that user) via Pydantic model_fields_set. Applies to project Routes 1+3 and the task loop; an existing project's owner (Route 2) is never mutated - burst: intake-default-assignee
- [2026-07-06] MCP + agents authenticate once and stay connected forever: the permanent per-user `User.api_key` is now accepted as a bearer on ALL REST endpoints (not just the hosted SSE path), and the local pulseops MCP server uses it instead of email/password→JWT. SSO users (who have no password) can now use the local MCP at all - burst: mcp-longlived-apikey
- [2026-07-06] Marker-gated synthetic-user seeding against the shared live dev DB is a proven, repeatable test pattern (`seeded_api_keys`: `@pulseops.test` emails, `_run`/`AsyncSessionLocal`, own-rows-only teardown) — lets auth/credential paths be tested without a JWT and without risking real rows, even while the main suite is RED - burst: mcp-longlived-apikey
- [2026-07-06] Two-adversarial-pass verification (completed Codex plan-challenge + Opus build-challenge with fix authority) is a viable ship gate when the Codex code-review gate is environmentally unavailable - burst: mcp-longlived-apikey

- [2026-07-23] Meeting Intelligence end-to-end (transcript-intake-bell): Graph transcript auto-poll (10-min APScheduler) → GPT-4o action-item extraction → per-user proposed-tasks bell → explicit-lists confirm creating real kanban tasks with pre-add dedup. CHARTER objective marked complete.
- [2026-07-23] Backend per-user delegated Microsoft Graph access: MSAL SerializableTokenCache from encrypted User.m365_token_cache, acquire_token_silent, re-encrypt on rotation (graph_service.acquire_user_token). Reusable for any Graph-backed feature (calendar, mail).
- [2026-07-23] Frontend test harness live: vitest + RTL + jsdom, '@' alias per tsconfig; first FE tests green (7/7). Resolves DEFERRED [2026-06-25] "no frontend component test harness".
- [2026-07-23] RLS-safe aggregate recalc pattern: recalc_project_progress on a plain service AsyncSessionLocal (no RLS ctx), post-commit, best-effort - reusable for derived aggregates the caller doesn't own.
- [2026-07-23] Constraint-backed ingest dedup pattern: partial UNIQUE index + INSERT ... ON CONFLICT DO NOTHING (meeting_transcripts.graph_transcript_id) - safe under concurrent replicas.
- [2026-07-23] Peer ag-review --wait completes synchronous adversarial review in-ceiling in this env (Codex adversarial-review historically hangs) - dependable code-review gate.
