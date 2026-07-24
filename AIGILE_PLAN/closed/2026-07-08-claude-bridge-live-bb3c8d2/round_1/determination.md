# Round 1 determinations — Codex plan challenge (2026-07-08)

Thread: 019f3ce5-fbfb-7311-b016-7531c8709799. Orchestrator confirmed all dispositions verbatim ("confirm").

| ID | Sev | Disposition | Reasoning |
|----|-----|-------------|-----------|
| R1-1 | HIGH | ABSORB-PLAN | Widen the m365 headless guard: short-circuit on ANY silent-acquisition failure (empty cache, expired/revoked/invalid refresh token), not just "no cached account". The blocking interactive device flow is never entered in headless/server context. |
| R1-2 | HIGH | ABSORB-PLAN | Specify the error-propagation mechanism: the guard must NOT return an error string from `_get_token()` (it would be sent as a Bearer header via `_graph_request()` at server.py:117). Instead raise a typed exception (or return a sentinel checked by callers) so each tool returns the clear "token cache missing/expired — re-seed per runbook" message. |
| R1-3 | MEDIUM | ABSORB-PLAN | Integration-gate step (7): the /chat smoke prompt must force a real MCP tool call (e.g. "list my recent meeting transcripts") and assert a tool-derived result, proving mcp__pulseops (and where creds present mcp__m365) are callable — not merely that Claude replies. |
| R1-4 | LOW | ABSORB-PLAN | Streams header rephrased: "Three write-disjoint streams, built sequentially A → B → C" — removes the stale "parallel" claim. |

Rejected alternatives: none — no REJECT dispositions this round.
