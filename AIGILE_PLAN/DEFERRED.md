## Deferred

<!-- Format: - [date] item - trigger: <condition> -->

- [2026-06-25] /ai/chat date buckets (overdue / due-today / due-this-week / per-task labels) use the server date (`date.today()`), not the user's local date - trigger: shipping to users outside the server timezone, or first timezone-related "wrong day" report. Fix: send client local date/timezone in the `/ai/chat` request (frontend `api.ts` + `AIAssistantPanel` + backend `_ChatRequest`) and bucket from it. Source: assistant-task-prompts probe R1/R2 Codex MEDIUM.
- [2026-06-25] /ai/chat task context is one fixed relevance slice (cap 40), not intent-aware - trigger: users with very large backlogs, or if priority/due-date/blocked questions need more precise retrieval. Fix: branch retrieval by prompt intent. Source: assistant-task-prompts probe R2 + PENDING correction.

