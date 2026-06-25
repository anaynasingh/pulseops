## Burst Plan
**Goal:** Make the AI assistant's quick-prompt buttons task-focused and give the chat endpoint real per-user task context so those prompts return useful, task-specific answers.
**CHARTER alignment:** AI-powered team operations / workflow intelligence — the assistant becomes actionable at the individual-task level, not just project-level.
**Streams:** two (frontend prompts + backend context). Files are disjoint → parallel-safe.

### Stream A - frontend-quick-prompts
- Scope (files WRITTEN):
  - `frontend/components/ai/AIAssistantPanel.tsx`
- Excluded: every other frontend file; all backend.
- Change: replace the 4 strings in `QUICK_PROMPTS` (lines 31-36) with task-focused prompts:
  1. `"What should I focus on today?"`
  2. `"What are my overdue tasks?"`
  3. `"What are my top priorities right now?"`
  4. `"What's due this week?"`
- Exports: none (internal const). The buttons send these strings verbatim to `aiApi.chat`, unchanged plumbing.
- Dependency: none (works standalone; answer quality depends on Stream B but no code dependency).
- Builder: claude

### Stream B - backend-task-context
- Scope (files WRITTEN):
  - `backend/app/api/v1/ai.py`
- Excluded: `ai_service.py`, models, schemas, every other backend/frontend file. No new endpoint, no schema change.
- Change: in the `query`/`summarize` branch of `POST /ai/chat` (after projects context is built, ~lines 769-786, before `CHAT_SYSTEM`), add a query for the current user's actionable tasks and append a "Your tasks" section to `context`:
  - Query: `select(Task).where(Task.assigned_to == current_user.id, Task.is_completed == False, Task.status != "cancelled")` joined/loaded for project title, ordered by `due_date` (nulls last), `limit(15)`.
  - Context lines per task: title, priority, due_date (or "no due date"), overdue flag (`due_date < date.today()`), project title.
  - Add a one-line header summary: total open tasks, # overdue, # due today.
  - Reuses existing imports (`Task` line 14, `date` already used line 780, `selectinload`/`select` already imported). Reuses the `Task.assigned_to == current_user.id` pattern already present in the dedupe/confirm branches.
- Case enumeration (read-path, mandatory): (1) user has tasks → task section rendered; (2) user has zero assigned/open tasks → render "You have no open assigned tasks." not an empty/absent section; (3) tasks with null due_date → "no due date", not crash on comparison; (4) overdue subset; (5) empty workspace (no projects) → task section still appended independently of the projects-empty branch.
- Exports: `/ai/chat` reply now reflects task data; response shape unchanged (`{"reply": ...}`).
- Dependency: none on Stream A.
- Builder: claude

**Shared files:** none (Stream A frontend-only, Stream B backend-only — disjoint writers, verified).
**Integration gate:** both build clean (`tsc --noEmit` + `next build` for A; backend imports/route smoke for B); clicking each new prompt returns a task-aware answer (manual/browser check); off-topic/empty-task paths still behave.
**Deferred to next Burst:** project-scoped variant ("what do I need to do in THIS project") when the assistant is opened inside a project — would use the existing `project_id` already passed to `/ai/chat`; not in scope now.
