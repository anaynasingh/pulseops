-- PulseOps — Migration 002: intake project-vs-task classification
-- Adds the AI-classification column the intake confirm flow routes on.
--
-- Idempotent: safe to run repeatedly. Mirrors the startup auto-migration in
-- app/main.py run_migrations() so cold starts and manual runs stay in sync.
--
-- Column: request_intake.suggested_item_type — "project" | "task" (nullable;
-- legacy rows created before this column default to "project" at confirm time).

ALTER TABLE request_intake ADD COLUMN IF NOT EXISTS suggested_item_type TEXT;
