# Self-review (Opus pre-pass) — assistant-task-prompts

No Critical or High findings. Nothing absorbed before Codex (Low/Medium surfaced as informational).

- **F1 Medium** `ai.py` sort key — latent fragility only if `due_date` were ever a `datetime` (column is `Date`, so safe in practice). Not active.
- **F2 Low** `ai.py` — header counts (`len`, overdue_n, due_today_n) computed on the post-slice 15-task window; if a user has >15 open tasks, "N open" understates and there's no "showing 15 of N" indicator.
- **F3 Low** `ai.py` — task titles interpolated into LLM context unescaped (prompt-injection surface). Pre-existing pattern (project titles/blockers already injected at lines 783-785); bounded — user's own data, reply returned only to that user.
- **F4 Low** `ai.py` — query has no `.limit()`; loads all open tasks into memory before Python sort+slice. Projects query above uses `.limit(30)`.
- **F5 Low** frontend — "What's due this week?" has no first-class 7-day bucket in the context labels (OVERDUE / TODAY / due <date> / none); LLM infers it from raw dates.
- **F6 note (not a defect)** — `is_private` intentionally not filtered: query is scoped to `assigned_to == current_user.id`, so only the user's own tasks; no cross-user leakage.
