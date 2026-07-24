# Round 1 → round 2 preservation check (2026-07-08)

4 modified lines (8 +/- lines) in `diff -u round_1/plan.md round_2/plan.md`, categorised against round_1/change-request.md:

| # | Hunk | Category | Whitelist item |
|---|------|----------|----------------|
| 1 | **Streams** header: "Three parallel streams" → "Three write-disjoint streams, built sequentially A → B → C" | Authorised | Change 4 (R1-4) |
| 2 | Stream A headless-guard bullet: widened to ANY silent-acquisition failure; typed exception/sentinel instead of error string from `_get_token()` (Bearer-header plumbing named) | Authorised | Changes 1+2 (R1-1, R1-2) |
| 3 | Stream A case-enumeration line: m365 case (6) extended with silent-refresh-failure immediate-error behaviour | Authorised | Change 1 (R1-1) |
| 4 | Integration gate step (7): smoke prompt forces a real MCP tool call and asserts a tool-derived result | Authorised | Change 3 (R1-3) |

Unauthorised additions: none. Unauthorised deletions: none. Unauthorised modifications: none.
Verdict: PASS — all hunks map to the whitelist. Copies (`round_2/plan.md`, `plan.md`) byte-identical; scope lint clean.
