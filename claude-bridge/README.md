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
- The bridge only allows Claude the PulseOps MCP tools — file editing, shell,
  and web tools are disabled for safety.
- Claude requests take longer than GPT-4o replies (it's doing real multi-step
  work) — 30 seconds to a few minutes is normal.
- If the panel says the bridge is not running, start step 3 above.
