## Under Consideration

- [2026-06-03] Deployment target (Railway vs Vercel+Railway vs self-hosted) - needs: decision on hosting budget and whether prod deploy is in scope
- [2026-06-03] M365 MCP server integration depth — server exists but unclear which flows use it - needs: review of mcp-servers/m365/server.py scope
- [2026-06-25] Project-scoped AI assistant variant — "what do I need to do in THIS project" when the panel is opened inside a project (reuse the project_id already passed to /ai/chat) - needs: decision on whether this is a near-term burst (then move to DEFERRED with a trigger) or speculative. Source: assistant-task-prompts plan deferral.
- [2026-07-06] Long-term MCP credential model — keep accepting a permanent, plaintext, un-revocable bearer (`User.api_key`) or move to short-lived/rotatable/scoped MCP tokens - needs: an explicit position before the rotate/revoke burst is scoped (revoke-only vs full rotation vs scoped tokens). Risk accepted this burst on the basis the key was already full-access via the SSE path. Source: mcp-longlived-apikey.

