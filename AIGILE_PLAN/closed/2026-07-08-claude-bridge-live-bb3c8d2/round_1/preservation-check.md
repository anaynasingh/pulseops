# Round 0 → round 1 preservation check (2026-07-07)

6 hunks in `diff -u round_0/plan.md round_1/plan.md`, categorised against round_0/change-request.md:

| # | Hunk | Category | Whitelist item |
|---|------|----------|----------------|
| 1 | **Streams** header gains "Build order is A → B → C sequential (all orchestrator-direct, single session): write-sets are disjoint but the streams are semantically dependent." | Authorised | Change 5 (C5) |
| 2 | New Stream A export bullet: m365 server.py headless guard (no blocking device flow when cache empty; immediate auth-error string) | Authorised | Change 2 (C2) |
| 3 | Stream A requirements bullet: `urllib3` pinned alongside `requests>=2.31` | Authorised | Change 6 (C6) |
| 4 | Stream A m365 case (6): guarded immediate-error behaviour replaces "device-flow fallback prints to stderr" | Authorised | Change 2 (C2) |
| 5 | Stream C CHARTER bullet extended: Constraints line (AIGILE_CHARTER.md:28) amendment + Success Criteria <10s clarifying clause | Authorised | Changes 3+4 (C3, C4) |
| 6 | Integration gate: new step (7) — docker-run with real secrets → `POST /chat` smoke returning an actual Claude reply | Authorised | Change 1 (C1) |

Unauthorised additions: none. Unauthorised deletions: none. Unauthorised modifications: none.
Verdict: PASS — all hunks map 1:1 to the whitelist. Copies (`round_1/plan.md`, `plan.md`) byte-identical; scope lint clean.
