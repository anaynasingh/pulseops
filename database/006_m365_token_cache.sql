-- 006_m365_token_cache.sql
-- Per-user Microsoft Graph token storage for the in-app AI Assistant.
--
-- Previously the assistant shared ONE Microsoft token (Anayna's), so every user's
-- "read my email / summarize my meeting" hit her mailbox. This stores each user's
-- OWN MSAL token cache (encrypted at rest with M365_TOKEN_ENC_KEY), captured via the
-- /auth/microsoft/connect flow, so the assistant reads that user's own mailbox.
ALTER TABLE users ADD COLUMN IF NOT EXISTS m365_token_cache TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS m365_connected_at TIMESTAMPTZ;
