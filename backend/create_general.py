import sys
sys.path.insert(0, '.')
import asyncio
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.models import User, Project, Task, PriorityLevel, ProjectStatus

# Tasks that are general/admin — not tied to a specific product
# Identified by title keywords
GENERAL_KEYWORDS = [
    "meeting time", "meeting tim",
    "pre-tom", "pre tom",
    "show task planner to tom",
    "ask tom",
    "send .env",
    "work with hannah",
    "test fable",
    "railway admin access",
    "open router access",
    "openrouter access",
    "test railway task planner",
    "test task planner",
    "dmarc",
    "s3 bucket",
    "aws s3",
]

async def run():
    async with AsyncSessionLocal() as session:
        # Get Mark as owner (General = org-level, Mark is lead)
        mark = (await session.execute(select(User).where(User.email == "mark.clement@prospect33.com"))).scalar_one()

        # Create General project
        result = await session.execute(select(Project).where(Project.title == "General — Admin & Misc"))
        general = result.scalar_one_or_none()
        if not general:
            general = Project(
                title="General — Admin & Misc",
                description="Tasks that don't belong to a specific product. Meeting logistics, admin work, cross-team coordination, one-offs.",
                status=ProjectStatus.in_progress,
                priority=PriorityLevel.low,
                owner_id=mark.id,
                progress_pct=0,
            )
            session.add(general)
            await session.flush()
            print(f"Created project: General — Admin & Misc")
        else:
            print(f"Project already exists: General — Admin & Misc")

        # Find and move general tasks
        all_tasks = (await session.execute(select(Task))).scalars().all()
        moved = []
        for task in all_tasks:
            if task.project_id == general.id:
                continue  # already in General
            title_lower = task.title.lower()
            if any(kw in title_lower for kw in GENERAL_KEYWORDS):
                task.project_id = general.id
                moved.append(task.title)

        await session.commit()
        print(f"\nMoved {len(moved)} tasks to General:")
        for t in moved:
            print(f"  - {t}")

asyncio.run(run())
