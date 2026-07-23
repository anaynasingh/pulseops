# Adversarial code review — transcript-intake-bell (2026-07-23)

**Reviewer:** peer (ag-review dispatcher, .aigile/model-roles.yaml Reviewer=peer; non-Codex adapter, no Codex job id)
**Mode:** branch review, --base 52c42f2..HEAD, synchronous --wait, completed inside the 10-min ceiling
**Verdict:** 3 findings (1 Medium/High security, 2 Low). No Critical. No contract violations — reviewer explicitly verified C1–C8, R1-1..R1-8, RLS bypass policy (`app_user_id() IS NULL` in migrations/001_rls_policies.sql), expire_on_commit safety, and the confirm overlap/ownership checks as sound.

## Findings and dispositions

1. **[Medium/High, security] TLS verification disabled on Graph calls** (graph_service.py:73, `httpx.AsyncClient(verify=False)`).
   Disposition: DEFERRED to Orchestrator — matches the documented repo-wide corporate-proxy convention (ai_service.py:14 comment; m365/server.py:163 uses the identical pattern for the same graph.microsoft.com host, and the plan mandated a verbatim port). Not a regression introduced by this diff. Recommended follow-up: repo-wide env-driven TLS toggle burst.

2. **[Low, efficiency] Retry sweep re-extracts failing transcripts once per user per tick, and twice within one user's tick.**
   Disposition: FIXED (commit after review) — shared per-tick `attempted_extractions` set across the calendar loop, the retry sweep, and all users; test added (37/37).

3. **[Low, type accuracy] `ProposedTask.transcript_id`/`meeting_title` non-null in TS but nullable in the backend schema.**
   Disposition: FIXED (same commit) — types now `string | null`; bell grouping falls back to "Untitled meeting"; tsc clean, vitest 7/7.

## Related ag-challenge build round 1 (opus/Prosecution) unfixed findings
- Medium: catch-all "Meeting Action Items" project check-then-create race (needs unique-index migration) — for steer.
- Medium: poison-meeting permanent Graph 4xx pins a user's poll cursor (skip-vs-fail design call) — for steer.
- Low: (superseded — the double-extraction half was fixed by the peer-review fix above.)
