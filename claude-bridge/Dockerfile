# PulseOps Claude Bridge — container image for Railway.
#
# Runs the Claude Code CLI in headless mode with the PulseOps MCP server,
# authenticated by a Claude SUBSCRIPTION via CLAUDE_CODE_OAUTH_TOKEN (NOT an
# Anthropic API key — do not set ANTHROPIC_API_KEY here, it would override the
# subscription token and switch to API billing).
#
# IMPORTANT: the build context must be the REPO ROOT (this Dockerfile copies both
# claude-bridge/ and mcp-servers/). On Railway:
#   - Dockerfile Path  = claude-bridge/Dockerfile
#   - Root Directory   = <repo root> (leave empty/default; do NOT set it to claude-bridge)
FROM node:20-slim

# Python (bridge + the pulseops MCP server) and TLS certs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Claude Code CLI (global) — puts `claude` on PATH.
RUN npm install -g @anthropic-ai/claude-code

WORKDIR /app

# Install Python deps first for better layer caching.
COPY claude-bridge/requirements.txt /app/claude-bridge/requirements.txt
COPY mcp-servers/pulseops/requirements.txt /app/mcp-servers/pulseops/requirements.txt
COPY mcp-servers/m365/requirements.txt /app/mcp-servers/m365/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages \
        -r /app/claude-bridge/requirements.txt \
        -r /app/mcp-servers/pulseops/requirements.txt \
        -r /app/mcp-servers/m365/requirements.txt

# App code.
COPY claude-bridge/ /app/claude-bridge/
COPY mcp-servers/ /app/mcp-servers/

# Claude Code (non-bare, so it reads CLAUDE_CODE_OAUTH_TOKEN) needs a writable
# HOME for its config dir. Bind on :: (IPv6, dual-stack) — Railway's private
# network is IPv6-only, so 0.0.0.0 would be unreachable from the backend.
ENV HOME=/app \
    BRIDGE_HOST=:: \
    PYTHONIOENCODING=utf-8 \
    PYTHONUNBUFFERED=1

# Railway injects $PORT at runtime; bridge.py reads it. EXPOSE is documentation.
EXPOSE 8765

CMD ["python3", "/app/claude-bridge/bridge.py"]
