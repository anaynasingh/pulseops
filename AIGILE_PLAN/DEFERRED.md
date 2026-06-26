## Deferred

<!-- Format: - [date] item - trigger: <condition> -->

- [2026-06-25] /ai/chat date buckets (overdue / due-today / due-this-week / per-task labels) use the server date (`date.today()`), not the user's local date - trigger: shipping to users outside the server timezone, or first timezone-related "wrong day" report. Fix: send client local date/timezone in the `/ai/chat` request (frontend `api.ts` + `AIAssistantPanel` + backend `_ChatRequest`) and bucket from it. Source: assistant-task-prompts probe R1/R2 Codex MEDIUM.
- [2026-06-25] /ai/chat task context is one fixed relevance slice (cap 40), not intent-aware - trigger: users with very large backlogs, or if priority/due-date/blocked questions need more precise retrieval. Fix: branch retrieval by prompt intent. Source: assistant-task-prompts probe R2 + PENDING correction.
- [2026-06-26] Project.progress_pct is not recalculated on task creation (create_task AND intake task→existing) or deletion — only on task PATCH (update_task) when is_completed/status changes. A project at 100% stays shown complete after new todo tasks are added. Trigger: a "project shows complete but has open tasks" report, or when progress accuracy on board/dashboard/AI-context matters. Fix: extract the count-based recalc from tasks.py update_task into a shared helper and call it on task create/delete and intake confirm. Source: intake-functional probe round 2 Codex C3 (MEDIUM, pre-existing app-wide behaviour, out of intake burst scope).

