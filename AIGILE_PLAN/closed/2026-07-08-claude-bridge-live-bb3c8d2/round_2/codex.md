# Codex plan challenge — round 2 (2026-07-08, resumed)

Thread: 019f3ce5-fbfb-7311-b016-7531c8709799 (turn 019f3fcc-afe8-7f42-874f-b16e602be61e)
Invocation: codex-review task --resume --prompt-file /tmp/codex-plan-round2-1783481803.txt (exit 0)

**Findings**

- **HIGH (R2-1)**: The new headless guard conflicts with the M365 cache-seeding runbook. The plan says server.py:88 must never enter device flow on empty cache, but Stream C still says to seed the cache by running the M365 server and completing device code. If that interactive path is removed unconditionally, there is no specified way to create `/data/m365-token.json`.

- **MEDIUM (R2-2)**: R1-3 is only partially closed. The revised `/chat` smoke example forces a PulseOps tool call ("list my recent meeting transcripts"), but it does not force an M365 tool call. That still leaves the email/calendar side of server.py:236 unproven before deploy, despite the plan claiming both MCP servers are verified.

- **LOW (R2-3)**: R1-2 is mostly addressed, but the plan still contains conflicting wording in the case enumeration: "the headless guard returns an immediate auth-error string." The earlier typed-exception/sentinel wording is the safer contract; the later wording could mislead implementation back toward the error-string-as-token failure at server.py:117.

R1-1 and R1-4 are addressed: the guard scope now covers failed silent acquisition with cached accounts, and the stale "parallel" framing is fixed to sequential A → B → C.
