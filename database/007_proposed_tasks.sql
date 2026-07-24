-- 007_proposed_tasks.sql
-- Meeting-transcript task intake: proposed_tasks store + Graph poll bookkeeping.
--
-- The transcript poll ingests Teams transcripts via Microsoft Graph (per-user
-- delegated token), extracts action items with GPT-4o, and stages them here as
-- per-user PROPOSED tasks. The dashboard bell lists pending proposals; confirm
-- creates real tasks rows.
--
-- NOTE: the LIVE database's enum type is prioritylevel (no underscore) - the
-- live tables were created via the ORM (SAEnum default name), and the ORM
-- binds ::prioritylevel casts. schema.sql's priority_level exists in the DB
-- but is NOT what tasks/projects columns use. Verified against the live DB
-- 2026-07-23 (first deploy failed with DatatypeMismatchError).

CREATE TABLE IF NOT EXISTS proposed_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transcript_id UUID REFERENCES meeting_transcripts(id) ON DELETE CASCADE,
    meeting_title TEXT,
    meeting_date DATE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    priority prioritylevel DEFAULT 'medium',
    assignee_hint VARCHAR(255),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_task_id UUID,
    dedup_status VARCHAR(20),
    dedup_existing_task_id UUID,
    proposed_at TIMESTAMPTZ DEFAULT now(),
    handled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_proposed_tasks_user_status
    ON proposed_tasks (user_id, status);
CREATE INDEX IF NOT EXISTS idx_proposed_tasks_transcript
    ON proposed_tasks (transcript_id);

-- Graph ingestion bookkeeping on meeting_transcripts.
ALTER TABLE meeting_transcripts ADD COLUMN IF NOT EXISTS graph_transcript_id VARCHAR(255);
ALTER TABLE meeting_transcripts ADD COLUMN IF NOT EXISTS graph_meeting_id VARCHAR(255);
ALTER TABLE meeting_transcripts ADD COLUMN IF NOT EXISTS truncated BOOLEAN DEFAULT FALSE;
-- Extraction-state marker: extraction success <=> extracted_at IS NOT NULL.
-- A zero-action-item success is extracted_at set with action_items = '[]'.
ALTER TABLE meeting_transcripts ADD COLUMN IF NOT EXISTS extracted_at TIMESTAMPTZ;

-- Per-transcript dedup key. UNIQUE so two concurrent polls cannot both pass a
-- check-then-insert: the constraint (not the app) is the dedup guarantee.
-- Partial-WHERE form matches the idx_users_ms_oid / idx_users_api_key convention.
CREATE UNIQUE INDEX IF NOT EXISTS idx_meeting_transcripts_graph_transcript_id
    ON meeting_transcripts (graph_transcript_id) WHERE graph_transcript_id IS NOT NULL;

-- Per-user poll cursor: advances to poll-start only when that user's entire
-- iteration completes without exception.
ALTER TABLE users ADD COLUMN IF NOT EXISTS m365_last_transcript_poll TIMESTAMPTZ;

-- Corrective for tables created by the first (broken) version of this
-- migration, which declared priority as priority_level: the ORM binds
-- ::prioritylevel, so the mismatch aborts every proposal INSERT.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='proposed_tasks' AND column_name='priority'
               AND udt_name='priority_level') THEN
    ALTER TABLE proposed_tasks ALTER COLUMN priority DROP DEFAULT;
    ALTER TABLE proposed_tasks ALTER COLUMN priority TYPE prioritylevel USING priority::text::prioritylevel;
    ALTER TABLE proposed_tasks ALTER COLUMN priority SET DEFAULT 'medium';
  END IF;
END $$;
