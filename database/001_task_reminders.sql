-- 001_task_reminders.sql
-- Adds last_reminded_at to tasks for hourly reminder deduplication.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_tasks_reminder
    ON tasks (assigned_to, is_completed)
    WHERE assigned_to IS NOT NULL AND is_completed = FALSE;
