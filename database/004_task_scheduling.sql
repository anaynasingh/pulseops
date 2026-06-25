-- 004_task_scheduling.sql
-- Franklin Covey time-blocking: schedule tasks into specific time slots.
-- scheduled_at = block start (UTC); duration_minutes = block length.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_at TIMESTAMPTZ;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS duration_minutes INTEGER DEFAULT 60;

CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at
    ON tasks (assigned_to, scheduled_at)
    WHERE scheduled_at IS NOT NULL;
