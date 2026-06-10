import sys
sys.path.insert(0, '.')
import asyncio
from sqlalchemy import text
from app.db.session import engine

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_tasks_assigned_to ON tasks(assigned_to)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON tasks(project_id)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_is_completed ON tasks(is_completed)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
    "CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id)",
    "CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)",
    "CREATE INDEX IF NOT EXISTS idx_projects_kanban_order ON projects(kanban_order)",
    "CREATE INDEX IF NOT EXISTS idx_activity_logs_entity_id ON activity_logs(entity_id)",
    "CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_transcript_logs_user_id ON transcript_search_logs(user_id)",
]

async def create_indexes():
    async with engine.begin() as conn:
        for idx in INDEXES:
            await conn.execute(text(idx))
            name = idx.split("idx_")[1].split(" ")[0]
            print(f"  OK: {name}")
    print("All indexes created")

asyncio.run(create_indexes())
