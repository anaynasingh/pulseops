# PulseOps MCP Servers — Setup Guide

This guide walks you through setting up both MCP servers so Claude Code can directly talk to PulseOps and your Microsoft 365 account.

---

## PulseOps MCP Setup

This server lets Claude read and write directly to your PulseOps workspace.

### Steps

**1. Install dependencies**
```
cd mcp-servers/pulseops
pip install -r requirements.txt
```

**2. Configure your API key**
```
cp .env.example .env
```
Grab your personal API key from PulseOps (**Settings → MCP Token**) and paste it into `.env`. This key is long-lived — you set it once and never have to reconnect:
```
PULSEOPS_API_URL=http://localhost:8001/api/v1
PULSEOPS_API_KEY=your-api-key-from-pulseops-settings
```

**3. Test the server**
```
python server.py
```
You should see: `PulseOps MCP server ready` printed to the terminal. Press Ctrl+C to stop.

**4. Use with Claude Code**
Copy the `pulseops` server block from `mcp-servers/claude-settings.json` into your own `.claude/settings.json` (that is the file Claude Code actually reads — it is user-local and gitignored). Claude Code will auto-start the server. Fill in `PULSEOPS_API_KEY` in that env block (or use the `.env` file approach above).

---

## Microsoft 365 MCP Setup

This server lets Claude read your Outlook email and calendar. It uses Microsoft's secure browser-based login — your password never touches the server.

### Step 1 — Register an Azure app

You need to register a free app in Azure so the server can talk to Microsoft Graph.

1. Go to [https://portal.azure.com](https://portal.azure.com)
2. In the search bar, type **"App registrations"** and click it
3. Click **"+ New registration"**
4. Fill in:
   - **Name:** `PulseOps MCP`
   - **Supported account types:** Select **"Accounts in this organizational directory only"** (or "Multitenant" if you want to allow personal Microsoft accounts too)
   - **Redirect URI:** Leave blank
5. Click **Register**
6. On the overview page, copy two values:
   - **Application (client) ID** — this becomes `M365_CLIENT_ID`
   - **Directory (tenant) ID** — this becomes `M365_TENANT_ID`

### Step 2 — Add API permissions

1. In your new app, click **"API permissions"** in the left sidebar
2. Click **"+ Add a permission"**
3. Choose **"Microsoft Graph"**
4. Choose **"Delegated permissions"**
5. Search for and add each of these:
   - `User.Read`
   - `Mail.Read`
   - `Mail.ReadWrite`
   - `Calendars.Read`
   - `OnlineMeetings.Read`
   - `OnlineMeetingTranscript.Read.All` (needed for `get_meeting_transcript`)
   - `Files.Read.All` (needed for `find_meeting_files` / `read_meeting_file` — reading transcript/recording files, incl. meetings you didn't organize)
   - `Sites.Read.All` (needed for `find_meeting_files` on channel/SharePoint meetings)
6. Click **"Add permissions"**
7. Click **"Grant admin consent for [your org]"** — **required** in the prospect33 tenant. `OnlineMeetingTranscript.Read.All` (and, per tenant policy, the mail/calendar scopes too) cannot be user-consented, so an admin must grant consent or nothing works. If you don't have admin rights, send IT this URL to click:
   ```
   https://login.microsoftonline.com/d2df1e4d-b444-4a6f-b465-92b187684c19/adminconsent?client_id=7d7b5cc0-5bf1-4b5b-9988-ca247f3d2173
   ```
   The `/adminconsent` URL grants every permission **declared on the app registration**, so make sure all six above are added (step 5) before the admin clicks — otherwise a missing scope won't get consented.

### Step 3 — Enable public client flows

This allows the device code login flow (the browser-based one-time login).

1. In your app, click **"Authentication"** in the left sidebar
2. Scroll to **"Advanced settings"**
3. Toggle **"Allow public client flows"** to **Yes**
4. Click **Save**

### Step 4 — Configure the server

```
cd mcp-servers/m365
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and fill in (these are the pinned PulseOps values — do **not** substitute another app id):
```
M365_CLIENT_ID=7d7b5cc0-5bf1-4b5b-9988-ca247f3d2173
M365_TENANT_ID=d2df1e4d-b444-4a6f-b465-92b187684c19
```
> The correct app is the one named **"PulseOps"** (`7d7b5cc0…`) — the app registration that is admin-consented in the prospect33 tenant. An older app **"AI Task Management and Workflow Intelligence System"** (`7ba4bd53…`) is NOT consented; do not use it.

### Step 5 — First-time login

```
python server.py
```

The server will display something like:
```
============================================================
M365 Authentication Required
============================================================
To sign in, use a web browser to open the page
https://microsoft.com/devicelogin and enter the code XXXXXXXX
============================================================
```

1. Open that URL in any browser
2. Enter the code shown
3. Log in with your Microsoft 365 work or school account
4. Done — the token is saved to `~/.pulseops_m365_token.json`

On all future runs, the server silently refreshes the token in the background. You only need to do this once (unless the token expires after extended inactivity).

---

## Configuring Claude Code

Both servers are registered in `.claude/settings.json`. Before using them, open that file and fill in the empty strings:

```json
{
  "mcpServers": {
    "pulseops": {
      "command": "python",
      "args": ["mcp-servers/pulseops/server.py"],
      "env": {
        "PULSEOPS_API_URL": "http://localhost:8001/api/v1",
        "PULSEOPS_API_KEY": "your-api-key-from-pulseops-settings"
      }
    },
    "m365": {
      "command": "python",
      "args": ["mcp-servers/m365/server.py"],
      "env": {
        "M365_CLIENT_ID": "7d7b5cc0-5bf1-4b5b-9988-ca247f3d2173",
        "M365_TENANT_ID": "d2df1e4d-b444-4a6f-b465-92b187684c19"
      }
    }
  }
}
```

Alternatively, use `.env` files in each server folder — the servers load them automatically via `python-dotenv`.

---

## Using the MCPs with Claude

Once both servers are running, you can talk to Claude naturally:

- **"Check my Outlook inbox and create tasks in PulseOps for anything that needs action"**
- **"List all blocked projects in PulseOps"**
- **"What meetings do I have this week? Create a project for any that need follow-up"**
- **"Process this email and add tasks to the Q3 Planning project"**
- **"Show me the PulseOps dashboard summary"**
- **"Mark all my unread Outlook emails as read"**
- **"Search PulseOps for anything related to the website redesign"**
- **"Analyze this meeting transcript and create tasks in PulseOps"**

Claude will automatically call the right MCP tools behind the scenes.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'mcp'` | Run `pip install -r requirements.txt` in the server folder |
| `401 Unauthorized` from PulseOps | Re-grab your API key from PulseOps Settings → MCP Token and update `PULSEOPS_API_KEY` in `.env` or `settings.json` |
| `M365_CLIENT_ID is not set` | Copy `.env.example` to `.env`; the pinned app id is `7d7b5cc0-5bf1-4b5b-9988-ca247f3d2173` (app name "PulseOps") |
| Sign-in shows **"Need admin approval"** | This app needs tenant admin consent. Have IT open the `/adminconsent` URL in Step 2.7. Also confirm you're using `7d7b5cc0…` (app "PulseOps"), not the old `7ba4bd53…` app |
| Device code flow shows an error | Make sure "Allow public client flows" is enabled in Azure |
| Token expired | Delete `~/.pulseops_m365_token.json` and re-run `python server.py` to re-authenticate |
| Claude Code doesn't see the MCP tools | Restart Claude Code after updating `settings.json` |
