-- 002_microsoft_oauth.sql
-- Adds Microsoft Azure AD identity column to users table.
-- ms_oid stores the Azure Object ID (stable across email changes).
-- Partial unique index allows multiple NULL values (existing password-only users).

ALTER TABLE users ADD COLUMN IF NOT EXISTS ms_oid TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_ms_oid
    ON users (ms_oid)
    WHERE ms_oid IS NOT NULL;
