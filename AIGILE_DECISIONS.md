## Challenged Decisions

<!-- Format: - [date] decision - challenge: <summary> -->
<!--           ruling: <accepted/rejected/modified> - <rationale> -->

- [2026-07-07] Deployment target is Railway - challenge: Under Consideration since 2026-06-03 (Railway vs Vercel+Railway vs self-hosted).
  ruling: accepted - backend + frontend already auto-deploy on Railway from P33-AI master; claude-bridge burst adds a third Railway service. De facto reality recorded as decided.
- [2026-07-07] M365 MCP integration depth: email + calendar read, single-user, wired into the Claude bridge - challenge: Under Consideration since 2026-06-03 (server existed but no flow used it).
  ruling: accepted - m365 MCP (MSAL device-code, delegated Mail.Read + Calendars.Read) attaches to the claude-bridge service alongside pulseops. Meeting transcripts stay sourced from the PulseOps store, NOT Graph. Multi-user out of scope.
- [2026-07-07] CHARTER Hard Spec "OpenRouter (GPT-4o) for all LLM inference" to be amended to sanction Claude-via-bridge (subscription auth, no Anthropic API key) as a second inference path - challenge: PR #21 + claude-bridge-live burst make Claude a second path; spec is stale.
  ruling: modified - amendment approved by Orchestrator at /ag-plan 2026-07-07; CHARTER edit lands with the claude-bridge-live burst.

