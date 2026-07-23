# Preservation check — round 1 → round 2 (completed 2026-07-23)

Method: `diff round_1/plan.md round_2/plan.md` mapped hunk-by-hunk against
`round_1/change-request.md` (11-item whitelist). File was left empty by the
interrupted 2026-07-22 session; check performed and recorded 2026-07-23.

| Hunk (plan.md line) | Content | Whitelist item(s) | Verdict |
|---|---|---|---|
| 28 (Stream A DB spec) | `extracted_at TIMESTAMPTZ NULL` column + extraction-state contract (success ⟺ extracted_at IS NOT NULL) in 007 + run_migrations mirror | 2 | AUTHORISED |
| 29 (Stream A impl notes) | R1-1 poll serialization (max_instances=1 + shared asyncio.Lock, 409 contract); R1-3 window-independent retry sweep; R1-4 calendarView @odata.nextLink pagination; R1-5 task-move dual recalc; C1/C4 reuse+retry sentences restated in `extracted_at` terms | 1, 3, 4, 5, 11 | AUTHORISED |
| 45 (Stream B contract) | R1-6 distinct query keys + prefix invalidation; R1-7 vitest resolve.alias '@'; R1-8 refetchInterval 60_000 | 6, 7, 8 | AUTHORISED |
| 54 (Integration gate #4) | Overlapping-poll serialization test required | 9 | AUTHORISED |
| 56 (Integration gate #6) | Zero-action-item extraction success is terminal case added | 10 | AUTHORISED |

Deletions: none (matches whitelist). All other plan content preserved verbatim
(diff touches only lines 28-29, 45, 54, 56). Scope lists, stream decomposition,
executors, dependencies: unchanged, as required.

**Verdict: PASS — no unauthorised edits.** `current/plan.md` verified byte-identical
to `round_2/plan.md` (promotion confirmed).
