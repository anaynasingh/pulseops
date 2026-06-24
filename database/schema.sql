-- ============================================================
-- PulseOps — Full PostgreSQL Schema
-- Run AFTER pgvector_setup.sql
-- ============================================================

-- ============================================================
-- ENUMS
-- ============================================================

CREATE TYPE user_role AS ENUM ('admin', 'contributor', 'viewer', 'requester');
CREATE TYPE project_status AS ENUM (
    'intake', 'todo', 'in_progress', 'blocked',
    'review', 'done', 'potential'
);
CREATE TYPE priority_level AS ENUM ('low', 'medium', 'high', 'urgent');
CREATE TYPE health_status AS ENUM ('healthy', 'at_risk', 'delayed', 'blocked');
CREATE TYPE intake_status AS ENUM ('pending', 'confirmed', 'rejected');
CREATE TYPE summary_type AS ENUM ('daily', 'weekly', 'executive', 'blocker');
CREATE TYPE entity_type AS ENUM (
    'project', 'task', 'comment', 'meeting',
    'email', 'attachment', 'user'
);

-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT UNIQUE NOT NULL,
    name            TEXT NOT NULL,
    password_hash   TEXT,                    -- NULL if OAuth only
    role            user_role DEFAULT 'contributor',
    avatar_url      TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);

-- ============================================================
-- TEAMS
-- ============================================================

CREATE TABLE IF NOT EXISTS teams (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    description     TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS team_members (
    team_id         UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            user_role DEFAULT 'contributor',
    joined_at       TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (team_id, user_id)
);

-- ============================================================
-- PROJECTS (Kanban cards)
-- ============================================================

CREATE TABLE IF NOT EXISTS projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT NOT NULL,
    description     TEXT,
    status          project_status DEFAULT 'intake',
    priority        priority_level DEFAULT 'medium',
    owner_id        UUID REFERENCES users(id) ON DELETE SET NULL,
    team_id         UUID REFERENCES teams(id) ON DELETE SET NULL,
    progress_pct    INT DEFAULT 0 CHECK (progress_pct >= 0 AND progress_pct <= 100),
    due_date        DATE,
    tags            TEXT[] DEFAULT '{}',
    stakeholders    TEXT[] DEFAULT '{}',    -- free-text or emails
    next_action     TEXT,
    risks           TEXT,
    blockers        TEXT,
    health_score    INT DEFAULT 100 CHECK (health_score >= 0 AND health_score <= 100),
    latest_update   TEXT,
    kanban_order    INT DEFAULT 0,          -- ordering within column
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_projects_status    ON projects (status);
CREATE INDEX IF NOT EXISTS idx_projects_priority  ON projects (priority);
CREATE INDEX IF NOT EXISTS idx_projects_owner     ON projects (owner_id);
CREATE INDEX IF NOT EXISTS idx_projects_team      ON projects (team_id);
CREATE INDEX IF NOT EXISTS idx_projects_due_date  ON projects (due_date);
CREATE INDEX IF NOT EXISTS idx_projects_tags      ON projects USING GIN (tags);
-- Full-text search index
CREATE INDEX IF NOT EXISTS idx_projects_fts ON projects
    USING GIN (to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, '')));

-- ============================================================
-- PROJECT ASSIGNMENTS (many-to-many)
-- ============================================================

CREATE TABLE IF NOT EXISTS project_assignments (
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (project_id, user_id)
);

-- ============================================================
-- PROJECT DEPENDENCIES
-- ============================================================

CREATE TABLE IF NOT EXISTS project_dependencies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    depends_on_id   UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, depends_on_id),
    CHECK (project_id <> depends_on_id)
);

-- ============================================================
-- TASKS (subtasks within projects)
-- ============================================================

CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    description     TEXT,
    status          project_status DEFAULT 'todo',
    priority        priority_level DEFAULT 'medium',
    assigned_to     UUID REFERENCES users(id) ON DELETE SET NULL,
    due_date        DATE,
    is_completed    BOOLEAN DEFAULT FALSE,
    completed_at    TIMESTAMPTZ,
    last_reminded_at TIMESTAMPTZ,
    kanban_order    INT DEFAULT 0,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_project    ON tasks (project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_assigned   ON tasks (assigned_to);
CREATE INDEX IF NOT EXISTS idx_tasks_status     ON tasks (status);

-- ============================================================
-- COMMENTS (threaded, on projects or tasks)
-- ============================================================

CREATE TABLE IF NOT EXISTS comments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE CASCADE,
    task_id         UUID REFERENCES tasks(id) ON DELETE CASCADE,
    parent_id       UUID REFERENCES comments(id) ON DELETE CASCADE, -- threading
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body            TEXT NOT NULL,
    mentions        UUID[] DEFAULT '{}',   -- user IDs mentioned
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    CHECK (project_id IS NOT NULL OR task_id IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_comments_project ON comments (project_id);
CREATE INDEX IF NOT EXISTS idx_comments_task    ON comments (task_id);
CREATE INDEX IF NOT EXISTS idx_comments_user    ON comments (user_id);

-- ============================================================
-- ATTACHMENTS
-- ============================================================

CREATE TABLE IF NOT EXISTS attachments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type     entity_type NOT NULL,
    entity_id       UUID NOT NULL,
    uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    filename        TEXT NOT NULL,
    url             TEXT NOT NULL,
    size_bytes      BIGINT,
    mime_type       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attachments_entity ON attachments (entity_type, entity_id);

-- ============================================================
-- ACTIVITY LOGS (audit trail)
-- ============================================================

CREATE TABLE IF NOT EXISTS activity_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type     entity_type NOT NULL,
    entity_id       UUID NOT NULL,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          TEXT NOT NULL,   -- e.g. 'moved', 'commented', 'priority_changed'
    old_value       TEXT,
    new_value       TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_entity   ON activity_logs (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_activity_user     ON activity_logs (user_id);
CREATE INDEX IF NOT EXISTS idx_activity_created  ON activity_logs (created_at DESC);

-- ============================================================
-- NOTIFICATIONS
-- ============================================================

CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            TEXT NOT NULL,   -- 'mention', 'assignment', 'blocked', 'due_soon', etc.
    title           TEXT NOT NULL,
    body            TEXT,
    entity_type     entity_type,
    entity_id       UUID,
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications (user_id, is_read, created_at DESC);

-- ============================================================
-- PROJECT HEALTH (AI-generated scores)
-- ============================================================

CREATE TABLE IF NOT EXISTS project_health (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id          UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    health_status       health_status DEFAULT 'healthy',
    health_score        INT DEFAULT 100 CHECK (health_score >= 0 AND health_score <= 100),
    risk_score          INT DEFAULT 0   CHECK (risk_score >= 0 AND risk_score <= 100),
    delivery_confidence INT DEFAULT 100 CHECK (delivery_confidence >= 0 AND delivery_confidence <= 100),
    reasoning           TEXT,
    evaluated_at        TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_project ON project_health (project_id, evaluated_at DESC);

-- ============================================================
-- AI SUMMARIES
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_summaries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type     entity_type NOT NULL,
    entity_id       UUID NOT NULL,
    summary_type    summary_type NOT NULL,
    body            TEXT NOT NULL,
    model_used      TEXT DEFAULT 'gpt-4o',
    token_count     INT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_summaries_entity ON ai_summaries (entity_type, entity_id, created_at DESC);

-- ============================================================
-- AI INSIGHTS
-- ============================================================

CREATE TABLE IF NOT EXISTS ai_insights (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id          UUID REFERENCES projects(id) ON DELETE CASCADE,
    insight_type        TEXT NOT NULL,  -- 'blocker', 'risk', 'next_action', 'velocity', 'recommendation'
    body                TEXT NOT NULL,
    confidence_score    FLOAT DEFAULT 0.8 CHECK (confidence_score >= 0 AND confidence_score <= 1),
    is_dismissed        BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_insights_project ON ai_insights (project_id, created_at DESC);

-- ============================================================
-- REQUEST INTAKE (AI-processed natural language requests)
-- ============================================================

CREATE TABLE IF NOT EXISTS request_intake (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    raw_input               TEXT NOT NULL,
    generated_title         TEXT,
    generated_description   TEXT,
    project_type            TEXT,
    suggested_tags          TEXT[] DEFAULT '{}',
    suggested_subtasks      JSONB DEFAULT '[]',
    suggested_next_steps    TEXT[],
    suggested_due_date      DATE,
    suggested_priority      priority_level,
    suggested_owners        TEXT[] DEFAULT '{}',
    suggested_stakeholders  TEXT[] DEFAULT '{}',
    ai_reasoning            TEXT,
    -- Human confirmation fields
    user_confirmed_priority priority_level,
    intake_status           intake_status DEFAULT 'pending',
    project_id              UUID REFERENCES projects(id) ON DELETE SET NULL,  -- set when confirmed
    submitted_by            UUID REFERENCES users(id) ON DELETE SET NULL,
    confirmed_by            UUID REFERENCES users(id) ON DELETE SET NULL,
    confirmed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intake_status ON request_intake (intake_status, created_at DESC);

-- ============================================================
-- MEETING TRANSCRIPTS
-- ============================================================

CREATE TABLE IF NOT EXISTS meeting_transcripts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id      UUID REFERENCES projects(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    raw_transcript  TEXT NOT NULL,
    source          TEXT DEFAULT 'manual',  -- 'zoom', 'teams', 'google_meet', 'manual'
    summary         TEXT,
    action_items    JSONB DEFAULT '[]',     -- [{task, owner, deadline, priority}]
    decisions       TEXT[] DEFAULT '{}',
    blockers        TEXT[] DEFAULT '{}',
    attendees       TEXT[] DEFAULT '{}',
    meeting_date    DATE,
    tasks_created   BOOLEAN DEFAULT FALSE,
    uploaded_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_meetings_project ON meeting_transcripts (project_id, created_at DESC);

-- ============================================================
-- EMAIL INGESTION
-- ============================================================

CREATE TABLE IF NOT EXISTS email_ingestion (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subject             TEXT,
    raw_body            TEXT NOT NULL,
    sender              TEXT,
    recipients          TEXT[] DEFAULT '{}',
    received_at         TIMESTAMPTZ,
    summary             TEXT,
    extracted_tasks     JSONB DEFAULT '[]',     -- [{title, assignee, due_date, priority}]
    extracted_people    TEXT[] DEFAULT '{}',
    extracted_deadlines JSONB DEFAULT '[]',     -- [{date, context}]
    extracted_blockers  TEXT[] DEFAULT '{}',
    tasks_created       BOOLEAN DEFAULT FALSE,
    processed_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_created ON email_ingestion (created_at DESC);

-- ============================================================
-- REFRESH TRIGGER: updated_at auto-update
-- ============================================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_users_updated_at         BEFORE UPDATE ON users            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_teams_updated_at         BEFORE UPDATE ON teams            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_projects_updated_at      BEFORE UPDATE ON projects         FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_tasks_updated_at         BEFORE UPDATE ON tasks            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER trg_comments_updated_at      BEFORE UPDATE ON comments         FOR EACH ROW EXECUTE FUNCTION update_updated_at();
