# Round 2 determinations — Codex plan challenge (2026-07-08)

Thread: 019f3ce5-fbfb-7311-b016-7531c8709799. Orchestrator confirmed all dispositions verbatim ("confirm").

| ID | Sev | Disposition | Reasoning |
|----|-----|-------------|-----------|
| R2-1 | HIGH | ABSORB-PLAN | Device flow gated behind explicit opt-in `M365_ALLOW_DEVICE_FLOW=1` (set only during the one-time local seeding run); server/headless context (flag unset) always takes the fail-fast typed-exception path. Runbook seeding step names the flag — resolves the guard-vs-runbook contradiction without losing the seeding path. |
| R2-2 | MEDIUM | ABSORB-PLAN | Integration-gate step (7): when M365 creds are present, the smoke also forces an m365 tool call (e.g. `get_my_profile`) and asserts a tool-derived result — both MCP servers proven before deploy. |
| R2-3 | LOW | ABSORB-PLAN | Case (6) reworded to match the typed-exception contract: the guard raises; the TOOL returns the "token cache missing/expired — re-seed per runbook" message. |

Rejected alternatives: none.

**Revision mechanics note:** round-3 revision applied as orchestrator-direct targeted edits (3 whitelisted lines) rather than a full Plan-agent regeneration — lower drift risk for a 3-line delta; preservation check still runs on the full diff.
