# Round 0 determinations — Codex plan challenge (2026-07-07)

Thread: 019f3ce5-fbfb-7311-b016-7531c8709799. Orchestrator confirmed all dispositions verbatim ("confirm").

| ID | Sev | Disposition | Reasoning |
|----|-----|-------------|-----------|
| C1 | HIGH | ABSORB-PLAN | Integration gate gains a real-path smoke: docker-run with real secrets → `POST /chat` returning an actual Claude reply — proves headless CLAUDE_CODE_OAUTH_TOKEN auth, MCP server startup, and the tool allow-list before deploy. Also closes the ag-challenge round-1 residual MEDIUM ("claude -p first-run trust/auth unvalidated in-container"). |
| C2 | HIGH | ABSORB-PLAN | Stream A adds a headless guard to mcp-servers/m365/server.py (file already in scope): when no cached account is available, skip the blocking interactive device flow and return an immediate auth-error string ("token cache missing — re-seed per runbook") instead of hanging /chat to the 540s timeout. Case-enumeration entry (6) updated to match the guarded behaviour. |
| C3 | HIGH | ABSORB-PLAN | Stream C's CHARTER edit extends to the Constraints line ("OpenRouter API key required for all AI features" — AIGILE_CHARTER.md:28), second location of the same Orchestrator-approved amendment. |
| C4 | MEDIUM | ABSORB-PLAN | Same CHARTER edit adds a clarifying clause to the Success Criteria "<10 seconds" line: it applies to the GPT-4o extraction pipeline; the interactive Claude assistant path is exempt. |
| C5 | MEDIUM | BUILD-NOTE | Streams are semantically dependent though write-disjoint. Managed operationally: all three are orchestrator-direct in one session, executed A → B → C sequentially; the integration gate re-checks docs against landed code. No plan-text change beyond a build-order note. |
| C6 | LOW | ABSORB-PLAN | `urllib3` pinned alongside `requests` in mcp-servers/m365/requirements.txt (both imported directly by server.py). |

Rejected alternatives: none — no REJECT dispositions this round.
