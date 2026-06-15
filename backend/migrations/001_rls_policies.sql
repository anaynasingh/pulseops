-- PulseOps — Row Level Security (RLS) Policies
-- Run this once in the Supabase SQL editor.
--
-- Design:
--   • app.current_user_id is set per-transaction by FastAPI (via get_db_for_user).
--   • If the variable is empty/missing (migrations, seeding, admin scripts),
--     all operations are allowed — so existing tooling keeps working.
--   • FORCE ROW LEVEL SECURITY makes policies apply even to the postgres superuser,
--     ensuring the locker lock is real, not bypassed by the connection role.
--
-- Tables protected: tasks, projects
-- Tables left open: users, teams, activity_logs, ai_insights, etc. (read/audit data)

-- ── Helper function ────────────────────────────────────────────────────────────
-- Returns the current user's UUID from the session variable, or NULL if unset.

CREATE OR REPLACE FUNCTION app_user_id() RETURNS uuid
  LANGUAGE sql STABLE
AS $$
  SELECT NULLIF(current_setting('app.current_user_id', true), '')::uuid
$$;

-- Returns true if the current session user is an admin.
CREATE OR REPLACE FUNCTION app_user_is_admin() RETURNS boolean
  LANGUAGE sql STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM users
    WHERE id = app_user_id()
    AND role = 'admin'
  )
$$;


-- ══════════════════════════════════════════════════════════════════════════════
-- TASKS
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks FORCE ROW LEVEL SECURITY;

-- SELECT: everyone can read tasks that aren't private, OR tasks they own.
-- (matches the app-layer privacy filter already in place)
DROP POLICY IF EXISTS tasks_select ON tasks;
CREATE POLICY tasks_select ON tasks
  FOR SELECT
  USING (
    app_user_id() IS NULL                          -- no user ctx (migration/admin)
    OR is_private = false
    OR assigned_to = app_user_id()
    OR created_by  = app_user_id()
    OR app_user_is_admin()
  );

-- INSERT: any authenticated user may create a task (created_by enforced in app).
DROP POLICY IF EXISTS tasks_insert ON tasks;
CREATE POLICY tasks_insert ON tasks
  FOR INSERT
  WITH CHECK (
    app_user_id() IS NULL                          -- migration/admin bypass
    OR true                                        -- any logged-in user may create
  );

-- UPDATE: only assignee, creator, or admin.
DROP POLICY IF EXISTS tasks_update ON tasks;
CREATE POLICY tasks_update ON tasks
  FOR UPDATE
  USING (
    app_user_id() IS NULL
    OR assigned_to = app_user_id()
    OR created_by  = app_user_id()
    OR app_user_is_admin()
  );

-- DELETE: same rule as update.
DROP POLICY IF EXISTS tasks_delete ON tasks;
CREATE POLICY tasks_delete ON tasks
  FOR DELETE
  USING (
    app_user_id() IS NULL
    OR assigned_to = app_user_id()
    OR created_by  = app_user_id()
    OR app_user_is_admin()
  );


-- ══════════════════════════════════════════════════════════════════════════════
-- PROJECTS
-- ══════════════════════════════════════════════════════════════════════════════

ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;

-- SELECT: all projects are readable (team visibility).
DROP POLICY IF EXISTS projects_select ON projects;
CREATE POLICY projects_select ON projects
  FOR SELECT
  USING (true);

-- INSERT: any authenticated user may create a project.
DROP POLICY IF EXISTS projects_insert ON projects;
CREATE POLICY projects_insert ON projects
  FOR INSERT
  WITH CHECK (
    app_user_id() IS NULL
    OR true
  );

-- UPDATE: only owner, creator, or admin.
DROP POLICY IF EXISTS projects_update ON projects;
CREATE POLICY projects_update ON projects
  FOR UPDATE
  USING (
    app_user_id() IS NULL
    OR owner_id  = app_user_id()
    OR created_by = app_user_id()
    OR app_user_is_admin()
  );

-- DELETE: same rule as update.
DROP POLICY IF EXISTS projects_delete ON projects;
CREATE POLICY projects_delete ON projects
  FOR DELETE
  USING (
    app_user_id() IS NULL
    OR owner_id  = app_user_id()
    OR created_by = app_user_id()
    OR app_user_is_admin()
  );
