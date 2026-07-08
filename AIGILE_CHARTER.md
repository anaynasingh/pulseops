---
project: pulseops
created: 2026-06-03
mode: Build
source: ag-init + code analysis 2026-06-03
last_promoted: 2026-06-03
---

# AIGILE_CHARTER.md

## Vision

- [2026-06-03] PulseOps is an AI-powered team operations and workflow intelligence platform. It transforms unstructured inputs — emails, meeting transcripts, free-text requests — into structured, trackable work items via a Kanban board, with semantic search, AI-generated insights, and a context-aware assistant. The goal is to reduce the manual overhead of project coordination for teams by letting AI handle the extraction, prioritisation, and routing of operational work.

## Hard Specs

- Python 3.11+ backend (FastAPI, SQLAlchemy async, pgvector)
- Next.js 14+ App Router frontend (TypeScript, Tailwind, dnd-kit)
- PostgreSQL with pgvector for all persistence and semantic search
- OpenRouter (GPT-4o) for LLM inference — no direct OpenAI API calls. Claude-via-claude-bridge (Claude Code subscription OAuth token; no Anthropic API key) is a sanctioned second inference path [amended 2026-07-08, claude-bridge-live]
- HuggingFace `all-MiniLM-L6-v2` (384-dim) for embeddings — free tier
- JWT auth with bearer tokens
- All schema changes via numbered migration files — no ad-hoc ALTER TABLE
- MCP servers for external integrations (M365, pulseops-native)

## Constraints

- [2026-06-03] OpenRouter API key required for the GPT-4o AI features — no offline fallback. The Claude assistant path authenticates via `CLAUDE_CODE_OAUTH_TOKEN` (subscription, second sanctioned inference path) [amended 2026-07-08, claude-bridge-live]
- [2026-06-03] Supabase required for pgvector — local Postgres without pgvector extension will not work for semantic search
- [2026-06-03] Frontend uses npm (not bun) due to Windows path issues with postinstall scripts — use `npm install --ignore-scripts`

## Objectives

- [ ] Complete backend API — all routers functional with working DB layer (auth, projects, tasks, kanban, ai, search, analytics)
- [ ] Frontend connected to live backend — no mock data
- [x] [2026-06-26] AI Intake flow working end-to-end: raw text → structured card → human confirmation → project created
- [ ] Meeting Intelligence working: transcript upload → action items, decisions, tasks extracted
- [ ] Email Intelligence working: email ingestion → tasks, people, deadlines extracted
- [ ] Semantic search working: pgvector cosine similarity on projects and tasks
- [ ] AI Assistant panel connected to GPT-4o with project context
- [ ] Kanban drag-and-drop persisting to DB

## Discovered Capabilities

> Moved to AIGILE_PLAN/CAPABILITIES.md. CHARTER contains Vision, Hard Specs, Constraints, Objectives, and Success Criteria only.

## Challenged Decisions

> Moved to AIGILE_DECISIONS.md. CHARTER contains Vision, Hard Specs, Constraints, Objectives, and Success Criteria only.

## Deferred

> Moved to AIGILE_PLAN/DEFERRED.md. CHARTER contains Vision, Hard Specs, Constraints, Objectives, and Success Criteria only.

## Under Consideration

> Moved to AIGILE_PLAN/CONSIDERATIONS.md. CHARTER contains Vision, Hard Specs, Constraints, Objectives, and Success Criteria only.

## Success Criteria

- All 8 Kanban columns render and persist drag-and-drop order
- AI Intake produces a structured card with >80% accuracy on test inputs
- Semantic search returns relevant results for natural language queries
- Meeting transcript → task extraction completes in <10 seconds (applies to the GPT-4o extraction pipeline; the interactive Claude assistant path is exempt — multi-step tool runs legitimately take longer)
- Auth flow (signup, login, JWT) works end-to-end
- API docs at /docs fully reflect all live endpoints
