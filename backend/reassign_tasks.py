import sys
sys.path.insert(0, '.')
import asyncio
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import User, Task

STEPHEN_TASKS = [
    "Provide API key for Abraham",
    "Assist Anayna with Claude",
    "Take on RRP project",
    "Update review queue UI - side panel",
    "Add reviewer comments",
    "Investigate Tailscale",
    "Investigate Cloudflare",
    "Check and compare log engine",
    "Wait for Veronica to create realistic",
    "Update ALM anomaly detection",
    "Investigate why time is dominant",
    "Bring classifier and anomaly detector",
    "FIX: Anomaly detection flagging",
    "FIX: LRR Kanban and alert review",
    "BLOCKED: Wait for Veronica",
    "Create test_trades table",
    "Fix SHAP explanation",
    "Provide Anayna with meeting transcription API",
]

MARK_TASKS = [
    "Build cost calculator widget",
    "Review Stephen's GTL UI changes",
    "Update Agile from v8.2",
    "Create Agile handover document for Stephen",
    "Create RRP handover document",
    "Get RRP working with OpenRouter",
    "Get RRP working on OpenRouter",
    "Ask Tom for the name of the hourly",
    "Ask Tom: what is the hourly",
    "Review and merge GitHub pre-agile",
    "TTR UI - analysis pass",
    "Build AI human component",
    "Design pluggable Foragers",
    "Pre-Tom catch-up",
]

async def reassign():
    async with AsyncSessionLocal() as session:
        stephen = (await session.execute(select(User).where(User.email == "stephen.kamau@prospect33.com"))).scalar_one_or_none()
        mark = (await session.execute(select(User).where(User.email == "mark.clement@prospect33.com"))).scalar_one_or_none()

        if not stephen or not mark:
            print("ERROR: Stephen or Mark not found")
            return

        all_tasks = (await session.execute(select(Task))).scalars().all()

        s_count = 0
        m_count = 0

        for task in all_tasks:
            matched = False
            for prefix in STEPHEN_TASKS:
                if task.title.startswith(prefix):
                    task.assigned_to = stephen.id
                    s_count += 1
                    matched = True
                    break
            if not matched:
                for prefix in MARK_TASKS:
                    if task.title.startswith(prefix):
                        task.assigned_to = mark.id
                        m_count += 1
                        break

        await session.commit()

        # Final count
        from sqlalchemy import func
        result = await session.execute(
            select(User.name, func.count(Task.id).label('c'))
            .join(Task, Task.assigned_to == User.id, isouter=True)
            .where(User.email.in_(['anayna.singh@prospect33.com','stephen.kamau@prospect33.com','mark.clement@prospect33.com']))
            .group_by(User.id, User.name)
        )
        print("Reassignment complete!")
        print(f"  Moved {s_count} tasks → Stephen, {m_count} tasks → Mark")
        print()
        print("Final task counts:")
        for name, count in result.all():
            print(f"  {name}: {count} tasks")

asyncio.run(reassign())
