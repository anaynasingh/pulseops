-- 005_block_reminders.sql
-- Time-block reminders: stamp when a scheduled block's "starting" reminder was sent.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS block_reminded_at TIMESTAMPTZ;
-- Ensure the hourly-reminder dedup column exists (migration 001 parity safeguard).
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS last_reminded_at TIMESTAMPTZ;
