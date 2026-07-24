# Round 2 → round 3 change-request whitelist

Authorised changes ONLY — everything else preserved verbatim.

1. (R2-1) **Stream A headless-guard bullet**: device flow is not removed — it is gated behind explicit opt-in `M365_ALLOW_DEVICE_FLOW=1`, used only for the one-time interactive cache seeding; with the flag unset (server/headless context) the guard always takes the fail-fast path. **Stream C runbook sentence**: seeding step runs the m365 server (or login helper) with `M365_ALLOW_DEVICE_FLOW=1` + `M365_TOKEN_CACHE` pointed at a file.
2. (R2-2) **Integration gate step (7)**: when M365 creds are present, the smoke also forces an m365 tool call (e.g. "who am I in Outlook" → `get_my_profile`) and asserts a tool-derived result.
3. (R2-3) **Stream A case enumeration, m365 case (6)**: reword — the guard raises the typed exception; the TOOL returns the immediate "token cache missing/expired — re-seed per runbook" message (no error string from `_get_token()`).

## Deletions
None.

## Cascading consequences
No Scope changes; all edits inside existing Stream A/C export text and the Integration gate. The new `M365_ALLOW_DEVICE_FLOW` env var is implemented in `mcp-servers/m365/server.py` (already in Stream A scope) and documented in `claude-bridge/README.md` + `claude-bridge/.env.example` (already in C/A scope respectively).
