import sys
sys.path.insert(0, '.')
import asyncio
from sqlalchemy import select, delete
from app.db.session import AsyncSessionLocal
from app.models.models import Project, Task, ActivityLog

DELETE_TITLES = [
    'Develop Mobile Notification System for Project Alerts',
    'Develop PulseOps Mobile App with Notifications',
    'Fridaymeeting',
    'AI task planner',
    'Dev Meeting',
    'GTL / Forage / TTR Demo Prep',
    'Dev Meeting - June 1 Action Items',
    'PulseOps - Task Planner App',
    'Ai Task Management Platform',
    'General',
]

async def cleanup():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Project).where(Project.title.in_(DELETE_TITLES)))
        projects = result.scalars().all()
        proj_ids = [p.id for p in projects]

        print(f"Found {len(proj_ids)} projects to delete:")
        for p in projects:
            print(f"  - {p.title}")

        # Delete tasks
        task_del = await session.execute(delete(Task).where(Task.project_id.in_(proj_ids)))
        tasks_removed = task_del.rowcount

        # Delete activity logs
        for pid in proj_ids:
            await session.execute(delete(ActivityLog).where(ActivityLog.entity_id == pid))

        # Delete projects
        proj_del = await session.execute(delete(Project).where(Project.id.in_(proj_ids)))
        projs_removed = proj_del.rowcount

        await session.commit()
        print(f"\nDeleted {projs_removed} projects and {tasks_removed} old tasks")

        # Remaining
        remaining = await session.execute(select(Project.title, Project.created_at).order_by(Project.created_at))
        print("\nRemaining projects:")
        for title, created in remaining.all():
            date_str = created.strftime("%Y-%m-%d") if created else "unknown"
            print(f"  [{date_str}] {title}")

asyncio.run(cleanup())
