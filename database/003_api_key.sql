-- 003_api_key.sql
-- Adds long-lived API key to users for MCP authentication.
ALTER TABLE users ADD COLUMN IF NOT EXISTS api_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_api_key
    ON users (api_key)
    WHERE api_key IS NOT NULL;
