# Round 2 → round 3 preservation check (2026-07-08)

4 modified lines (8 +/- lines) in `diff -u round_2/plan.md round_3/plan.md`, categorised against round_2/change-request.md:

| # | Hunk | Category | Whitelist item |
|---|------|----------|----------------|
| 1 | Stream A headless-guard bullet: device flow gated behind `M365_ALLOW_DEVICE_FLOW=1` opt-in (seeding only; unset in server context) | Authorised | Change 1 (R2-1) |
| 2 | Stream A m365 case (6): guard raises typed exception; TOOL returns the message (no error string from `_get_token()`) | Authorised | Change 3 (R2-3) |
| 3 | Stream C runbook seeding sentence: run with `M365_ALLOW_DEVICE_FLOW=1` | Authorised | Change 1 (R2-1) |
| 4 | Integration gate step (7): m365 tool call (e.g. `get_my_profile`) also forced + asserted when M365 creds present | Authorised | Change 2 (R2-2) |

Unauthorised additions: none. Unauthorised deletions: none. Unauthorised modifications: none.
Verdict: PASS. Copies (`round_3/plan.md`, `plan.md`) byte-identical; scope lint clean. Revision applied as orchestrator-direct targeted edits per round_2/determination.md mechanics note.
