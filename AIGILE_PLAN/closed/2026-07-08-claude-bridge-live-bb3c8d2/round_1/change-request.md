# Round 1 → round 2 change-request whitelist

Authorised changes ONLY — everything else in the plan is preserved verbatim.

## Additions / modifications

1. (R1-1) **Stream A exports, headless-guard bullet**: guard triggers on ANY silent-token-acquisition failure (empty cache OR cached account whose `acquire_token_silent()` fails — expired/revoked/invalid refresh token), not only "no cached account". The blocking device flow (server.py:88) is never entered in server context. **Stream A case enumeration m365 case (6)**: extend to cover the silent-refresh-failure case with the same immediate-error behaviour.
2. (R1-2) **Same bullet**: specify the mechanism — the guard raises a typed exception (or returns a sentinel checked by callers) rather than returning an error string from `_get_token()`, because `_get_token()`'s return value is used as the `Authorization: Bearer` header by `_graph_request()` (server.py:117); each tool catches it and returns the clear "token cache missing/expired — re-seed per runbook" message.
3. (R1-3) **Integration gate step (7)**: the /chat smoke prompt must force a real MCP tool call (e.g. "list my recent meeting transcripts") and assert a tool-derived result appears in the reply — proving MCP servers start and the allow-list works, not merely that Claude answers.
4. (R1-4) **Streams header**: replace "Three parallel streams" phrasing with "Three write-disjoint streams, built sequentially A → B → C" (keep the rest of the sentence's content).

## Deletions

None.

## Cascading consequences

No Scope files added or dropped. All four changes refine wording inside sections that already exist (Stream A exports + case enumeration, Integration gate, Streams header); files referenced are already in the declared write-sets. No stream decomposition, Executor, or dependency changes are authorised.
