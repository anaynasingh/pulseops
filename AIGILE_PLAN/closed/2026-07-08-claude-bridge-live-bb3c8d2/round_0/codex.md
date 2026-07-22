# Codex plan challenge — round 0 (2026-07-07)

Thread: 019f3ce5-fbfb-7311-b016-7531c8709799
Invocation: codex-review task --prompt-file /tmp/codex-plan-round0-1783433123.txt (exit 0)

No CRITICAL findings.

**Findings**

- **HIGH**: The integration gate can pass without proving the real execution path. `/health` is static in bridge.py:143, while Claude and MCP servers are only exercised through `/chat` via `subprocess.run` in bridge.py:176. A passing Docker build, health check, and config grep would not catch broken MCP startup, invalid tool allow-list behavior, bad Python/server dependencies, or M365 auth failure before deploy.

- **HIGH**: The M365 "cache missing" negative-path behavior is likely mischaracterized. The plan says a missing cache falls back to device flow and returns an auth error string, but server.py:88 calls blocking device-flow methods, and the bridge only cuts off at `CLAUDE_TIMEOUT_SECONDS` in bridge.py:183. In a headless container, this can become a long `/chat` hang or 504 rather than the documented immediate auth error.

- **HIGH**: The CHARTER amendment is incomplete. The plan amends the Hard Spec at AIGILE_CHARTER.md:20, but leaves the constraint at AIGILE_CHARTER.md:28: "OpenRouter API key required for all AI features." That will conflict with Claude-via-bridge as a sanctioned second inference path using `CLAUDE_CODE_OAUTH_TOKEN`.

- **MEDIUM**: The CHARTER success criteria remain mismatched to the Claude path. AIGILE_CHARTER.md:64 requires meeting transcript task extraction in `<10 seconds`, while the plan explicitly accepts Claude requests taking 30 seconds to minutes. That leaves live acceptance ambiguous.

- **MEDIUM**: The stream independence claim is overstated. Stream B's Dockerfile contract consumes `mcp-servers/m365/requirements.txt`, which Stream A changes; Stream C's docs consume env names and behavior from `bridge.py` and `server.py`. The write sets are disjoint, but the streams are semantically dependent.

- **LOW**: The dependency hardening is only partially applied. server.py:16 directly imports both `requests` and `urllib3`, but the plan only adds `requests` to mcp-servers/m365/requirements.txt, leaving `urllib3` transitive despite the stated rationale.
