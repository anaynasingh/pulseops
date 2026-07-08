# PulseOps Claude Bridge — Railway service image.
# Build context must be the repo root: the image needs both claude-bridge/ and
# mcp-servers/ as siblings (bridge.py resolves REPO_ROOT = parent of its dir).
#   docker build -f claude-bridge/Dockerfile .
FROM python:3.12-slim

# Node 20 + the Claude Code CLI (headless `claude -p`, auth via CLAUDE_CODE_OAUTH_TOKEN)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get purge -y gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY claude-bridge/requirements.txt claude-bridge/requirements.txt
COPY mcp-servers/pulseops/requirements.txt mcp-servers/pulseops/requirements.txt
COPY mcp-servers/m365/requirements.txt mcp-servers/m365/requirements.txt
RUN pip install --no-cache-dir \
    -r claude-bridge/requirements.txt \
    -r mcp-servers/pulseops/requirements.txt \
    -r mcp-servers/m365/requirements.txt

COPY claude-bridge/ claude-bridge/
COPY mcp-servers/ mcp-servers/

# Railway private networking is IPv6-only — the container must listen on ::.
# Bare local runs (outside this image) keep bridge.py's loopback default.
ENV BRIDGE_HOST=::
# HOME is deliberately NOT set here: the Railway service sets HOME=/data (volume)
# so ~/.claude session state and the M365 token cache survive redeploys.

# bridge.py writes .mcp-config.json and workdir/ into its own directory at startup
WORKDIR /app/claude-bridge
CMD ["python", "bridge.py"]
