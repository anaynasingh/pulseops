# Preservation check — round 0 → round 1

Every changed hunk categorised against change-request.md. Verdict: ALL AUTHORISED. No unauthorised additions, deletions, or modifications.

| Hunk | Change | Authorised by |
|------|--------|---------------|
| Streams intro | "+ merge together / never ship frontend vs old backend" | M1 (CR #7) |
| Stream A scope: ai.py | Literal coercion, require_writer, import _can_edit_project | H1 + M2 (CR #1, #4) |
| Stream A scope: tests | fix BASE_URL 8001, DB-seeded pending intakes | H2 (CR #2) |
| Excluded line | add _can_edit_project to reused-not-edited list | H1 (CR #1) |
| Endpoint note | dependency get_current_user → require_writer | H1 (CR #1) |
| Omit-vs-null note | "coerced to project when null/legacy" | M2 (CR #4) |
| Route 1 | explicit project field list (ai.py:191-201) | M4 (CR #5) |
| Route 2 | _can_edit_project gate → 403; no project fields mutated | H1 (CR #1) |
| Route 3 | explicit override survival (title/desc/priority/owner/team/tags/due/next) | M4 (CR #5) |
| Case 5 | "200-path" → "201-path" | accuracy fix consistent with declared status 201 |
| Case 8 (new) | 403 unauthorized target | H1 (CR #1, additions) |
| Side effects | wording `tasks._log_activity` → `_log_activity` | consistency, no scope change |
| Serialization discipline (new para) | selectinload(assignee, project) before serialize | H3 (CR #3) |
| Classification para | Literal + field_validator + null/legacy → project | M2 (CR #4) |
| Stream A dependency line | name the three reused helpers | H1 (CR #1) |
| Stream B scope: page.tsx | + gating, state reset | M3 (CR #6) |
| Stream B State reset + gating clauses (new) | reset on analyze/discard; disable button | M3 (CR #6) |
| Shared files | add _can_edit_project to reused-not-edited list | H1 (CR #1) |
| Integration gate: merge-together clause (new) | A+B together | M1 (CR #7) |
| Integration gate: button disabled clause | type=task+existing+no-project | M3 (CR #6) |
| Integration gate: test line | 8001, +403, +M2 edge cases, DB seeding | H1+H2+M2 (CR #1,#2,#4) |

No Scope files dropped; write sets remain disjoint (backend-only vs frontend-only). projects.py still read-only/imported.
