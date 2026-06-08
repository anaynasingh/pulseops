-- ============================================================
-- PulseOps — Development Seed Data
-- ============================================================

-- Users
INSERT INTO users (id, email, name, role, avatar_url) VALUES
    ('11111111-0000-0000-0000-000000000001', 'anayna@pulseops.ai',  'Anayna Singh',   'admin',       'https://api.dicebear.com/7.x/avataaars/svg?seed=anayna'),
    ('11111111-0000-0000-0000-000000000002', 'stephen@pulseops.ai', 'Stephen Cole',   'contributor', 'https://api.dicebear.com/7.x/avataaars/svg?seed=stephen'),
    ('11111111-0000-0000-0000-000000000003', 'tom@pulseops.ai',     'Tom Rivera',     'contributor', 'https://api.dicebear.com/7.x/avataaars/svg?seed=tom'),
    ('11111111-0000-0000-0000-000000000004', 'priya@pulseops.ai',   'Priya Mehta',    'viewer',      'https://api.dicebear.com/7.x/avataaars/svg?seed=priya'),
    ('11111111-0000-0000-0000-000000000005', 'james@pulseops.ai',   'James Whitmore', 'requester',   'https://api.dicebear.com/7.x/avataaars/svg?seed=james')
ON CONFLICT (email) DO NOTHING;

-- Team
INSERT INTO teams (id, name, description, created_by) VALUES
    ('22222222-0000-0000-0000-000000000001', 'AI Platform Team', 'Core AI engineering and product team', '11111111-0000-0000-0000-000000000001')
ON CONFLICT DO NOTHING;

-- Team members
INSERT INTO team_members (team_id, user_id, role) VALUES
    ('22222222-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000001', 'admin'),
    ('22222222-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000002', 'contributor'),
    ('22222222-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000003', 'contributor'),
    ('22222222-0000-0000-0000-000000000001', '11111111-0000-0000-0000-000000000004', 'viewer')
ON CONFLICT DO NOTHING;

-- Projects (one per Kanban column)
INSERT INTO projects (id, title, description, status, priority, owner_id, team_id, progress_pct, due_date, tags, next_action, risks, health_score, created_by) VALUES
    (
        '33333333-0000-0000-0000-000000000001',
        'Accounting AI Agent',
        'Build an AI agent that classifies expenses and detects financial anomalies using ML models and GPT-4o.',
        'intake', 'high',
        '11111111-0000-0000-0000-000000000001',
        '22222222-0000-0000-0000-000000000001',
        0, CURRENT_DATE + 30,
        ARRAY['ai','accounting','ml'],
        'Define requirements and select data sources',
        'Access to financial data may require compliance review',
        90,
        '11111111-0000-0000-0000-000000000001'
    ),
    (
        '33333333-0000-0000-0000-000000000002',
        'PulseOps Backend API',
        'Design and implement the FastAPI backend with PostgreSQL, pgvector, and OpenAI integrations.',
        'in_progress', 'urgent',
        '11111111-0000-0000-0000-000000000002',
        '22222222-0000-0000-0000-000000000001',
        45, CURRENT_DATE + 14,
        ARRAY['backend','fastapi','api'],
        'Complete authentication endpoints and project CRUD',
        'pgvector indexing performance at scale',
        78,
        '11111111-0000-0000-0000-000000000001'
    ),
    (
        '33333333-0000-0000-0000-000000000003',
        'Customer Analytics Dashboard',
        'Build an interactive analytics dashboard for customer success teams with real-time metrics.',
        'todo', 'medium',
        '11111111-0000-0000-0000-000000000003',
        '22222222-0000-0000-0000-000000000001',
        0, CURRENT_DATE + 45,
        ARRAY['analytics','dashboard','frontend'],
        'Create wireframes and get design sign-off',
        NULL,
        95,
        '11111111-0000-0000-0000-000000000001'
    ),
    (
        '33333333-0000-0000-0000-000000000004',
        'API Rate Limiting System',
        'Implement distributed rate limiting across all API gateways using Redis and token bucket algorithm.',
        'blocked', 'high',
        '11111111-0000-0000-0000-000000000002',
        '22222222-0000-0000-0000-000000000001',
        30, CURRENT_DATE + 7,
        ARRAY['backend','infrastructure','api'],
        'Waiting on DevOps to provision Redis cluster',
        'Redis cluster provisioning delayed by 2 weeks',
        40,
        '11111111-0000-0000-0000-000000000001'
    ),
    (
        '33333333-0000-0000-0000-000000000005',
        'Meeting Intelligence Module',
        'Build the meeting transcript analysis pipeline using OpenAI to extract action items and decisions.',
        'review', 'high',
        '11111111-0000-0000-0000-000000000001',
        '22222222-0000-0000-0000-000000000001',
        85, CURRENT_DATE + 3,
        ARRAY['ai','meetings','nlp'],
        'Peer review of transcript parsing accuracy',
        NULL,
        88,
        '11111111-0000-0000-0000-000000000001'
    ),
    (
        '33333333-0000-0000-0000-000000000006',
        'SSO Integration (Okta)',
        'Integrate Okta SSO for enterprise authentication across all PulseOps environments.',
        'done', 'medium',
        '11111111-0000-0000-0000-000000000002',
        '22222222-0000-0000-0000-000000000001',
        100, CURRENT_DATE - 5,
        ARRAY['auth','security','enterprise'],
        NULL,
        NULL,
        100,
        '11111111-0000-0000-0000-000000000001'
    ),
    (
        '33333333-0000-0000-0000-000000000007',
        'Multi-Agent Orchestration Framework',
        'Research and prototype a multi-agent system for autonomous operational workflows using LangGraph.',
        'potential', 'low',
        '11111111-0000-0000-0000-000000000001',
        '22222222-0000-0000-0000-000000000001',
        0, NULL,
        ARRAY['ai','agents','research'],
        'Evaluate LangGraph vs AutoGen vs CrewAI',
        NULL,
        95,
        '11111111-0000-0000-0000-000000000001'
    )
ON CONFLICT DO NOTHING;

-- Tasks
INSERT INTO tasks (id, project_id, title, status, priority, assigned_to, due_date, created_by) VALUES
    ('44444444-0000-0000-0000-000000000001', '33333333-0000-0000-0000-000000000002', 'Set up FastAPI project structure', 'done', 'high', '11111111-0000-0000-0000-000000000002', CURRENT_DATE - 3, '11111111-0000-0000-0000-000000000001'),
    ('44444444-0000-0000-0000-000000000002', '33333333-0000-0000-0000-000000000002', 'Implement JWT authentication', 'in_progress', 'urgent', '11111111-0000-0000-0000-000000000002', CURRENT_DATE + 2, '11111111-0000-0000-0000-000000000001'),
    ('44444444-0000-0000-0000-000000000003', '33333333-0000-0000-0000-000000000002', 'Create PostgreSQL models', 'todo', 'high', '11111111-0000-0000-0000-000000000002', CURRENT_DATE + 5, '11111111-0000-0000-0000-000000000001'),
    ('44444444-0000-0000-0000-000000000004', '33333333-0000-0000-0000-000000000002', 'Build project CRUD endpoints', 'todo', 'high', '11111111-0000-0000-0000-000000000003', CURRENT_DATE + 7, '11111111-0000-0000-0000-000000000001'),
    ('44444444-0000-0000-0000-000000000005', '33333333-0000-0000-0000-000000000005', 'Parse Zoom transcript format', 'done', 'medium', '11111111-0000-0000-0000-000000000001', CURRENT_DATE - 2, '11111111-0000-0000-0000-000000000001'),
    ('44444444-0000-0000-0000-000000000006', '33333333-0000-0000-0000-000000000005', 'Extract action items with GPT-4o', 'done', 'high', '11111111-0000-0000-0000-000000000001', CURRENT_DATE - 1, '11111111-0000-0000-0000-000000000001'),
    ('44444444-0000-0000-0000-000000000007', '33333333-0000-0000-0000-000000000005', 'Review extraction accuracy on 10 sample transcripts', 'in_progress', 'high', '11111111-0000-0000-0000-000000000003', CURRENT_DATE + 1, '11111111-0000-0000-0000-000000000001')
ON CONFLICT DO NOTHING;

-- Activity logs
INSERT INTO activity_logs (entity_type, entity_id, user_id, action, old_value, new_value) VALUES
    ('project', '33333333-0000-0000-0000-000000000002', '11111111-0000-0000-0000-000000000002', 'status_changed', 'todo', 'in_progress'),
    ('project', '33333333-0000-0000-0000-000000000004', '11111111-0000-0000-0000-000000000002', 'status_changed', 'in_progress', 'blocked'),
    ('project', '33333333-0000-0000-0000-000000000006', '11111111-0000-0000-0000-000000000002', 'status_changed', 'review', 'done'),
    ('task',    '44444444-0000-0000-0000-000000000002', '11111111-0000-0000-0000-000000000002', 'status_changed', 'todo', 'in_progress');

-- AI Insights
INSERT INTO ai_insights (project_id, insight_type, body, confidence_score) VALUES
    ('33333333-0000-0000-0000-000000000004', 'blocker',         'API Rate Limiting is blocked on Redis provisioning. Consider requesting expedited provisioning or evaluating in-process rate limiting as a temporary solution.', 0.92),
    ('33333333-0000-0000-0000-000000000002', 'recommendation',  'Backend API is 45% complete with 14 days remaining. Current velocity suggests on-track delivery if authentication is completed by end of week.', 0.85),
    ('33333333-0000-0000-0000-000000000005', 'next_action',     'Meeting Intelligence Module is in review at 85% — schedule a 30-min accuracy review session to unblock final approval.', 0.88);

-- Project health records
INSERT INTO project_health (project_id, health_status, health_score, risk_score, delivery_confidence, reasoning) VALUES
    ('33333333-0000-0000-0000-000000000002', 'healthy',   78, 22, 80, 'On track with good velocity. Authentication blocker is manageable.'),
    ('33333333-0000-0000-0000-000000000004', 'blocked',   40, 75, 35, 'Hard dependency on external Redis provisioning with no ETA. Risk of missing deadline is high.'),
    ('33333333-0000-0000-0000-000000000005', 'healthy',   88, 12, 92, 'Nearly complete, in final review. Low risk of delay.');

-- Sample meeting transcript
INSERT INTO meeting_transcripts (project_id, title, raw_transcript, source, summary, action_items, decisions, attendees, meeting_date, uploaded_by) VALUES
    (
        '33333333-0000-0000-0000-000000000002',
        'Backend API Sprint Planning',
        'Anayna: Welcome everyone to the sprint planning. Let''s review what we need to accomplish this week.
Stephen: I''ll handle the JWT authentication system. Should be done by Wednesday.
Tom: I can take on the project CRUD endpoints. I''ll need the database schema finalized first.
Anayna: Good. Stephen, can you also set up the pgvector embedding pipeline by Friday?
Stephen: That''s aggressive but doable. I''ll need Tom to review the schema first.
Tom: I''ll have the schema reviewed by Monday. Also, we should add rate limiting to the AI endpoints.
Anayna: Agreed. Let''s add that as a task. Tom, can you own that?
Tom: Sure. And we should plan a demo for next Tuesday for the stakeholders.
Anayna: Perfect. Stephen will present the auth system, Tom presents the API structure.',
        'manual',
        'Sprint planning session for Backend API. Team committed to JWT auth by Wednesday, CRUD endpoints following schema review, and pgvector pipeline by Friday. Demo scheduled for next Tuesday.',
        '[{"task": "Implement JWT authentication", "owner": "Stephen Cole", "deadline": "Wednesday", "priority": "urgent"}, {"task": "Review database schema", "owner": "Tom Rivera", "deadline": "Monday", "priority": "high"}, {"task": "Build project CRUD endpoints", "owner": "Tom Rivera", "deadline": "end of week", "priority": "high"}, {"task": "Set up pgvector embedding pipeline", "owner": "Stephen Cole", "deadline": "Friday", "priority": "high"}, {"task": "Add rate limiting to AI endpoints", "owner": "Tom Rivera", "deadline": "next sprint", "priority": "medium"}, {"task": "Prepare stakeholder demo", "owner": "Stephen Cole", "deadline": "next Tuesday", "priority": "medium"}]',
        ARRAY['Use PostgreSQL for all relational data', 'pgvector for embeddings', 'Demo on Tuesday'],
        ARRAY['Anayna Singh', 'Stephen Cole', 'Tom Rivera'],
        CURRENT_DATE - 2,
        '11111111-0000-0000-0000-000000000001'
    );
