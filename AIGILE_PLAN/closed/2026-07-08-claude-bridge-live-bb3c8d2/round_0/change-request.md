# Round 0 → round 1 change-request whitelist

Authorised changes ONLY — everything else in the plan is preserved verbatim.

## Additions / modifications

1. (C1) **Integration gate**: add a step — docker-run with real secrets (`CLAUDE_CODE_OAUTH_TOKEN`, `PULSEOPS_API_URL`, `PULSEOPS_API_KEY`, M365 vars) → `POST /chat` smoke that must return an actual Claude reply, proving headless subscription auth, MCP server startup, and the tool allow-list inside the image before deploy. May note it closes the challenge residual "claude -p first-run trust unvalidated".
2. (C2) **Stream A exports**: add a bullet — headless guard in `mcp-servers/m365/server.py`: when silent token acquisition finds no cached account, do NOT enter the blocking interactive device flow; return an immediate auth-error string directing to the runbook re-seed. **Stream A case enumeration**: update m365 case (6) (cache path set but file missing) to reflect the guarded immediate-error behaviour instead of "device-flow fallback prints to stderr".
3. (C3) **Stream C exports**: extend the `AIGILE_CHARTER.md` edit bullet to also amend the Constraints line "OpenRouter API key required for all AI features — no offline fallback" (AIGILE_CHARTER.md:28) with the same sanctioned-second-path amendment.
4. (C4) **Stream C exports**: same CHARTER edit bullet — add a clarifying clause to the Success Criteria "<10 seconds" transcript-extraction line: applies to the GPT-4o extraction pipeline, interactive Claude assistant exempt.
5. (C5) **Streams header or Integration gate**: one sentence noting build order A → B → C sequential (orchestrator-direct, single session); write-sets disjoint but semantically dependent.
6. (C6) **Stream A exports**: the `mcp-servers/m365/requirements.txt` bullet also pins `urllib3` alongside `requests>=2.31`.

## Deletions

None.

## Cascading consequences

No Scope files are dropped; no references to dropped files exist. Change 2 modifies behaviour described for `mcp-servers/m365/server.py`, which is already in Stream A's Scope (files WRITTEN) — authorised. Change 3/4 stay within `AIGILE_CHARTER.md`, already in Stream C's Scope — authorised. No stream decomposition, Executor, or dependency changes are authorised.
