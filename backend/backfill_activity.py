import sys
sys.path.insert(0, '.')
import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, delete
from app.db.session import AsyncSessionLocal
from app.models.models import User, Project, Task, ActivityLog

async def backfill():
    async with AsyncSessionLocal() as session:
        try:
            # Get users
            anayna_res = await session.execute(select(User).where(User.email == "anayna.singh@prospect33.com"))
            anayna = anayna_res.scalar_one_or_none()

            stephen_res = await session.execute(select(User).where(User.email == "stephen.kamau@prospect33.com"))
            stephen = stephen_res.scalar_one_or_none()

            mark_res = await session.execute(select(User).where(User.email == "mark.clement@prospect33.com"))
            mark = mark_res.scalar_one_or_none()

            def get_user(assigned_to_id):
                if mark and assigned_to_id == mark.id:
                    return mark
                if stephen and assigned_to_id == stephen.id:
                    return stephen
                return anayna

            # Clear existing activity logs to avoid duplication
            await session.execute(delete(ActivityLog))

            logs = []
            now = datetime.now(timezone.utc)

            # Log all projects
            proj_res = await session.execute(select(Project).order_by(Project.created_at))
            projects = proj_res.scalars().all()

            for i, proj in enumerate(projects):
                owner = get_user(proj.owner_id)
                offset = timedelta(minutes=len(projects) - i)
                logs.append(ActivityLog(
                    entity_type="project",
                    entity_id=proj.id,
                    user_id=owner.id if owner else (anayna.id if anayna else None),
                    action="created",
                    new_value=proj.title,
                    meta={"project_title": proj.title, "priority": proj.priority.value},
                    created_at=now - offset
                ))

            # Log all tasks
            task_res = await session.execute(select(Task).order_by(Task.created_at))
            tasks = task_res.scalars().all()

            for i, task in enumerate(tasks):
                owner = get_user(task.assigned_to)
                offset = timedelta(seconds=len(tasks) - i)
                logs.append(ActivityLog(
                    entity_type="task",
                    entity_id=task.id,
                    user_id=owner.id if owner else (anayna.id if anayna else None),
                    action="task_created",
                    new_value=task.title[:80],
                    meta={"task_title": task.title, "priority": task.priority.value, "project_id": str(task.project_id)},
                    created_at=now - offset
                ))

            for log in logs:
                session.add(log)

            await session.commit()
            print(f"SUCCESS: Created {len(logs)} activity log entries")
            print(f"  {len(projects)} project logs")
            print(f"  {len(tasks)} task logs")

        except Exception as e:
            await session.rollback()
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(backfill())
