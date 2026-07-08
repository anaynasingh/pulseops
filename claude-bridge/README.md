# PulseOps ↔ Claude Code Bridge

Connects the AI Assistant chatbot inside PulseOps to **your own Claude Code** on this machine.

When the chat panel is switched to **Claude Code** mode, your message travels:

```
Chat panel  →  PulseOps backend (/ai/claude-chat)  →  this bridge (localhost:8765)
            →  claude -p (headless, with PulseOps MCP tools)  →  reply back to the panel
```

Because Claude runs with the PulseOps MCP server, it can genuinely **act** on your
workspace: read meeting transcripts, create tasks on the Kanban board, move projects,
check the dashboard, and so on — using your existing Claude Code login (no extra API key).

## Setup (one time)

1. Make sure Claude Code is installed and logged in (`claude --version` should work).
2. Install bridge dependencies:
   ```
   cd claude-bridge
   pip install -r requirements.txt
   ```
3. Configure your PulseOps MCP token (used by the MCP tools when Claude acts for you):
   ```
   copy .env.example .env
   ```
   then edit `.env` and set `PULSEOPS_API_KEY` to your personal MCP token —
   it's shown in the PulseOps sidebar under "Claude" setup (or `GET /api/v1/auth/api-key`).

## Run

Start the three pieces (each in its own terminal):

```
# 1. PulseOps backend
cd backend && uvicorn app.main:app --reload --port 8001

# 2. PulseOps frontend
cd frontend && npm run dev

# 3. Claude bridge
cd claude-bridge && python bridge.py
```

Open PulseOps, click the ✦ AI Assistant, and click the engine badge in the panel
header to switch from **GPT-4o** to **Claude Code**. Then try:

> read the meeting transcripts and create tasks on the kanban board

## Notes

- Follow-up messages continue the same Claude session (`--resume`), so Claude
  remembers the conversation until you press **clear** in the panel.
- The bridge only allows Claude the PulseOps + M365 MCP tools — file editing,
  shell, and web tools are disabled for safety.
- Claude requests take longer than GPT-4o replies (it's doing real multi-step
  work) — 30 seconds to a few minutes is normal.
- If the panel says the bridge is not running, start step 3 above (local dev)
  or check the Railway `claude-bridge` service (prod).

## Deploy on Railway

The bridge runs as its **own Railway service**, so Claude mode works on the live
deployment (not just when your laptop is running).

### Service setup

1. New service in the Railway project, from this repo.
2. **Root Directory = repo root** (the image needs both `claude-bridge/` and
   `mcp-servers/`) and **Config File Path = `claude-bridge/railway.json`**.
   Both are set in the service's Settings UI. If you skip the Config File Path,
   Railway auto-detects the top-level `railway.json`/`nixpacks.toml` and would
   build the frontend into this service.
3. Attach a **volume mounted at `/data`** — it holds the Claude session state
   and the M365 token cache across redeploys.
4. Environment variables:

   | Variable | Value |
   |---|---|
   | `CLAUDE_CODE_OAUTH_TOKEN` | Output of `claude setup-token` run locally (subscription auth — no Anthropic API key anywhere) |
   | `PULSEOPS_API_URL` | Backend private URL + `/api/v1`, e.g. `http://<backend>.railway.internal:8080/api/v1` |
   | `PULSEOPS_API_KEY` | **Required** — your permanent MCP token from `GET /api/v1/auth/api-key` (the bridge refuses to start without it) |
   | `M365_CLIENT_ID` | Azure app (public client) ID — omit to run without email tools |
   | `M365_TENANT_ID` | Your tenant ID |
   | `M365_TOKEN_CACHE` | `/data/m365-token.json` |
   | `HOME` | `/data` (keeps `~/.claude` session state on the volume — this is what makes `--resume` survive redeploys) |

   Leave `M365_CLIENT_SECRET` unset for the device-code public-client app.
   `BRIDGE_HOST` is NOT needed: the image bakes `BRIDGE_HOST=::` so the container
   answers over Railway's IPv6-only private networking; `PORT` is injected by Railway.

5. On the **backend** service, set `CLAUDE_BRIDGE_URL` to the bridge's private
   URL, e.g. `http://<bridge>.railway.internal:<port>`.

### One-time M365 setup (device code)

1. Azure App Registration: **public client** with device-code flow enabled,
   delegated permissions **Mail.Read, Mail.ReadWrite, Calendars.Read**
   (`Mail.ReadWrite` is needed by `mark_email_read`), admin-consented.
2. Seed the token cache **locally** (device flow needs a browser and is disabled
   in the container):
   ```
   cd mcp-servers/m365
   M365_ALLOW_DEVICE_FLOW=1 M365_CLIENT_ID=<id> M365_TENANT_ID=<tenant> \
     M365_TOKEN_CACHE=./m365-token.json python server.py
   # complete the device-code login in the browser, then Ctrl-C
   ```
3. Copy `m365-token.json` to the volume at `/data/m365-token.json` (e.g. via a
   one-off shell on the service).
4. MSAL silently refreshes the token on use. If the cache goes unused for
   ~90 days the refresh token expires — re-run step 2 and replace the file.
   When the cache is missing/expired the email tools return a clear
   "re-seed per runbook" error instead of hanging.

### Timeouts

Backend↔bridge traffic stays on Railway private networking (no public edge
proxy). The effective ceilings are the backend's HTTP timeout (600s) and the
bridge's `CLAUDE_TIMEOUT_SECONDS` (default 540s) — keep `CLAUDE_MAX_TURNS` /
`CLAUDE_TIMEOUT_SECONDS` conservative; an over-limit run surfaces the friendly
504 in the panel.
