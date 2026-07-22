# Plan Adversarial Challenge

## Round 1 — 2026-07-07
**Model:** opus (Prosecution)

## Fixed
| Sev | Vector/Lens | Location | Defect | Fix applied |
|-----|-------------|----------|--------|-------------|
| MEDIUM | V3 scope blindspot / V1 pre-mortem | Stream B scope (plan.md:26-28) | No `.dockerignore` exists (verified: `NO .dockerignore`) and the integration gate runs `docker build .` from repo root. Without one the build context ships `.git/`, `backend/`, `frontend/node_modules/`, venvs, `__pycache__`, and any on-disk `.env` / `claude-bridge/.mcp-config.json` / `claude-bridge/workdir/` into the image — slow context and a secret-leak vector on local dev builds. Not in any stream's write-set. | Added `.dockerignore` (repo root) to Stream B files-WRITTEN with rationale, and to the Shared-files write-set line `B = {…, .dockerignore}`. Both plan copies. |

## Findings (unfixed — require gate decision)
| Sev | Vector/Lens | Location | Indictment |
|-----|-------------|----------|------------|
| CRITICAL | V1 pre-mortem / V2 false assumption | plan.md:14, 21, 32, 52 (binding contract `HOST=0.0.0.0`) | Railway private networking is IPv6-only: a service is only reachable at `*.railway.internal` if it listens on `::`. The contract defaults `BRIDGE_HOST=0.0.0.0` (IPv4 only) and every enumerated case + the docker-run gate asserts `0.0.0.0:<port>` binding, entrenching the bug. On live, backend `httpx.post("http://<bridge>.railway.internal:<port>/chat")` (ai.py:707-717) gets `ConnectError` → 503 (ai.py:720-724) → frontend prints "Claude bridge isn't running on your machine. Start it with cd claude-bridge / python bridge.py" (AIAssistantPanel.tsx:109). Claude mode never works on the live deployment and the CHARTER "Email/Meeting Intelligence (Claude path)" objective is missed. Fixing the export contract is a design change B and C consume, so gate-only. |
| MEDIUM | V1 pre-mortem | plan.md:21 case (4); server.py:57-72, 88-99 | The plan's M365_CLIENT_SECRET "public-client vs confidential" branch is unsound. When `M365_CLIENT_SECRET` is set, `_build_app()` returns `ConfidentialClientApplication`, but the auth fallback uses `initiate_device_flow`/`acquire_token_by_device_flow` — a PublicClientApplication flow. A cache seeded by the runbook's public-client device-code login will not silently refresh under a confidential client, and the device-flow fallback path can't run on it. The runbook lists `M365_CLIENT_SECRET` as merely "optional" with no warning; setting it silently kills token refresh and every m365 tool returns an auth-error string after the seeded token expires. |
| MEDIUM | V1 pre-mortem | plan.md:16 ("headless-permission risk already mitigated"); bridge.py:176-185, 220 | Assumes `claude -p` runs clean in a fresh container. Unverified in-container: (a) first-run trust-folder/onboarding gate with a brand-new `HOME=/data` may block before config is seeded on the volume → subprocess hangs to `CLAUDE_TIMEOUT_SECONDS` (540s) → every request 504; (b) `CLAUDE_CODE_OAUTH_TOKEN` headless auth for `-p` is assumed to be honored but never validated inside the image. No step seeds/validates `~/.claude` first-run state on the volume. Gate step (3) only checks `claude --version`, which does not exercise auth or the trust gate. |
| MEDIUM | V3 scope blindspot | AIAssistantPanel.tsx:109-110; ai.py:723 (both outside declared scope) | Two user-facing strings hardcode "run the bridge on your own machine — cd claude-bridge / python bridge.py". Once the bridge is a hosted Railway service these are actively wrong, and a genuine connectivity failure (see CRITICAL) misdirects debugging to the user's laptop. Frontend is excluded; ai.py is declared "no backend code change needed" (plan.md:12) — so nothing in the plan touches or even flags this drift. |
| LOW | V3 scope blindspot | plan.md:29, 32; top-level `nixpacks.toml` (exists: `nodejs_20`) + top-level `railway.json` (frontend `cd frontend && npm start`) | Correct build of the new service rests entirely on a manual Railway UI step (Config File Path = `claude-bridge/railway.json`) that is not encodable in JSON. If the operator omits it, Railway auto-detects from repo root and applies the top-level NIXPACKS `railway.json` / `nixpacks.toml` — deploying the frontend start command into the bridge service. The plan documents the UI step but has no defence-in-depth if it is missed. |
| LOW | V2 false assumption | plan.md:44 (Stream C README note) | "Railway edge timeout risk on long runs … over-limit surfaces the existing friendly 504." Backend→bridge traffic uses private networking (`*.railway.internal`), which does not traverse Railway's public edge proxy, so the edge-timeout framing is inaccurate. Real ceilings are the backend httpx timeout (ai.py:709, 600s) and `CLAUDE_TIMEOUT_SECONDS` (540s). Misleading operator guidance in the runbook. |

### Round-1 higher-model fix (opus)

CRITICAL binding-contract finding resolved: plan default changed to `HOST = os.getenv("BRIDGE_HOST", "::")` (Railway private networking is IPv6-only), propagated through Stream A export + case enumeration, Stream B consumption text, Stream C runbook, and integration-gate assertions. Both plan copies verified byte-identical.

## Round 2 — 2026-07-07
**Model:** opus (Prosecution)

## Fix verification
CRITICAL fix propagated correctly: yes (Stream A export, case enumeration, Stream B consumption, Stream C runbook, gate `[::]:9999`); no lingering `0.0.0.0` contradiction — remaining mentions are negative references. Copies byte-identical: yes.

## Fixed
| Sev | Vector/Lens | Location | Defect | Fix applied |
|-----|-------------|----------|--------|-------------|
| — | — | — | none | — |

## Findings (unfixed — require gate decision)
| Sev | Vector/Lens | Location | Indictment |
|-----|-------------|----------|------------|
| HIGH | V1 pre-mortem / regression-from-fix | plan.md:14, 21 (binding default `::`); bridge.py:148-149 (`/chat` has no auth), prior default bridge.py:230 (`127.0.0.1`) | The round-1 fix universally defaults `BRIDGE_HOST` to `::`, which on dual-stack hosts (WSL/Linux/macOS, bindv6only=0 verified) binds ALL interfaces, not just loopback. The prior hardcoded `127.0.0.1` bound loopback-only. The `/chat` endpoint is UNAUTHENTICATED and shells out to `claude -p` with MCP access to the user's PulseOps board and Outlook mail/calendar (`--allowedTools mcp__pulseops,mcp__m365`). On any shared LAN, a local-dev run now exposes an unauthenticated endpoint that can read the user's email and manipulate their task board via `http://<dev-ip>:8765/chat`. The fix correctly solves prod but silently regresses the local-dev security posture. Recommended remediation (contract change B and C consume, hence gate-only): keep the CODE default at `127.0.0.1` and have Railway/the Dockerfile set `BRIDGE_HOST=::` explicitly, OR keep `::` default but add an inbound-auth guard on `/chat` and document the LAN exposure loudly. |
| MEDIUM | V1 pre-mortem / gate precision | plan.md:53 (gate: `PORT=9999 → binds [::]:9999`, `GET /health → 200`) | The `::` dual-stack acceptance of IPv4-mapped connections depends on kernel `bindv6only=0`, which the plan never pins or asserts inside the container. If a future base image or runtime sets `bindv6only=1`, the `::` socket rejects IPv4 and the gate's `curl localhost` fails misleadingly — or passes via `::1` while masking the difference. The gate should either assert `bindv6only=0` in the image or curl the IPv6 loopback explicitly (`curl -g http://[::1]:9999/health`) so it actually exercises the `::` bind path Railway depends on. |
| LOW | V3 scope blindspot | plan.md:29, 52 (`.dockerignore` round-1 addition; contents unspecified) | The added `.dockerignore` has no specified contents, and the Dockerfile COPYs the sibling `mcp-servers/` tree and pip-installs its requirements files. An over-broad ignore pattern (e.g. excluding `mcp-servers/`, `**/*.json`, or `**/requirements.txt`) would silently break the `docker build` at COPY/pip time. The plan should constrain `.dockerignore` to exclude only `.git/`, `frontend/node_modules/`, venvs, `__pycache__`, `**/.env`, `claude-bridge/.mcp-config.json`, and `claude-bridge/workdir/`. |

Round-1 MEDIUM/LOW findings re-checked: none escalated. The hardcoded-strings MEDIUM (AIAssistantPanel.tsx:109 / ai.py:723) is slightly de-risked by the binding fix but the strings remain factually wrong for the hosted path.

### Round-2 gate — Orchestrator design ruling (2026-07-07)

HIGH resolved by ruling: code default reverts to `127.0.0.1` (loopback-safe local runs; `/chat` is unauthenticated), Dockerfile bakes `ENV BRIDGE_HOST=::` so containers are reachable over Railway's IPv6-only private networking. Chosen over `::`-everywhere+auth and `::`-everywhere+docs-only. Round-2 MEDIUM (gate curls IPv6 loopback explicitly) and LOW (.dockerignore contents constrained) folded into the same plan edit. Both copies verified identical; scope lint clean.

## Round 3 — 2026-07-07
**Model:** opus (Prosecution — final verification)

## Fix verification
Ruling propagated consistently (Stream A contract, cases 1/5/6, Stream B ENV + consumption line, Stream C runbook, integration gate `[::]`/loopback assertions); no residual text claims the code default is `::`; copies byte-identical. No new Critical/High introduced.

## Fixed
| Sev | Vector/Lens | Location | Defect | Fix applied |
|-----|-------------|----------|--------|-------------|
| MEDIUM | gate-methodology | plan.md:53 | `curl -g http://[::1]:9999/health` did not state execution context; host-side curl via `docker run -p` (IPv4-only userland publish) would false-fail the IPv6 assertion. | Gate text now pins execution inside the container (`docker exec <ctr> curl -g http://[::1]:9999/health`). Applied by orchestrator post-round to both copies. |

## Findings (unfixed — require gate decision)
| Sev | Vector/Lens | Location | Indictment |
|-----|-------------|----------|------------|
| — | — | — | none |
