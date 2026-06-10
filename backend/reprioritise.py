import sys
sys.path.insert(0, '.')
import asyncio
from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.models import Task, PriorityLevel
import uuid

# Task Planner — due Jun 15 (5 days)
# Focus: demo-ready for Tom + fix Stephen's CORS blocker
TP_PRIORITIES = {
    # URGENT — must ship before Jun 15
    "28d7dad2-ae16-4638-991e-d53752c6d873": "urgent",  # Fix CORS - Stephen can't log in
    "a26d2f33-45f5-451f-b8bb-6908cf850e48": "urgent",  # Show Task Planner to Tom
    # HIGH — important but not blocking
    "577d4ba1-dae5-4a9d-9d52-f2050c7e33d1": "high",   # Test Railway fully + feedback
    "b457ec45-36e3-42ff-8da5-b2a55a02d9e6": "high",   # Retire task status (done today)
    "705a6cf1-f405-4146-b64f-e77f8e8497a7": "high",   # Self-service Claude/MCP (done today)
    "0ef660b7-b734-4ba9-9cff-8dfda8de5c0b": "high",   # Mobile responsive (done today)
    "963010ea-7268-4f73-af35-a40ae6bfcfc7": "high",   # Scope chatbot (done today)
    # MEDIUM — nice to have by deadline
    "da73e54e-46c0-4d26-af94-23cf90a9923d": "medium", # Add logging for transcripts
    # LOW — post-deadline, not critical
    "1323782a-57ea-4b5e-9f57-292796f1143f": "low",    # Switch to Codex UI
    "114127ae-75c0-423a-b4fe-ed92bf2b2a0d": "low",    # Pre-Tom catch-up (already happened)
    "c2589ae0-3a6a-4985-b870-d8acc9bb07a4": "low",    # Change meeting times
    "a1ab0cb5-5346-4552-b53a-2904025c1ca6": "high",   # Session persistence (done today)
}

# Forage — due Jun 18 (8 days)
# Focus: demo mode + pluggable Foragers architecture + ground truth pipeline
FORAGE_PRIORITIES = {
    # URGENT — must ship for Tom demos
    "fefb80e1-c8c6-437e-8349-025bf14d84f9": "urgent", # Build demo mode into Forage
    "9603e644-6a8b-442a-b95a-f684b16ac701": "urgent", # Design pluggable Foragers architecture
    # HIGH — core deliverables
    "b3a09512-7921-42ba-b93d-1ad1badad2ba": "high",   # Compare RAG vs agentic approaches
    "f148625e-31a1-4bdb-bb6a-82333b0dc737": "high",   # Build AI human component (Edgar)
    "6db8fe65-5f0d-4c56-a665-c504ca476fb6": "high",   # Forage human feedback interface
    "62295acc-d084-4a88-9cc5-f2d2c8a3ec71": "high",   # Build ground truth dataset
    # MEDIUM — important but can slip slightly
    "84ca54b4-8583-47cd-82ae-677f22ebd30d": "medium", # Write Forage design doc
    "250a4a5a-3182-47fd-baac-154b6ef2d29b": "medium", # Build cost calculator widget
    "a8c86984-d15f-4687-9630-f115c26f42fa": "medium", # Take on RRP project
    # LOW — deprioritised (Tailscale/Cloudflare dropped in favour of OpenRouter)
    "3d48c295-9eb4-4509-ac05-e545985316fa": "low",    # Investigate Tailscale
    "090f5ca6-c42e-4e6c-8d06-afbe6d827091": "low",    # Investigate Cloudflare
    "b33a1d79-be4e-4a0e-9e1a-fa5bf52bb2be": "low",    # Add reviewer comments
    "bb9039d1-0e05-4ab4-abb7-6c4151c3ae1b": "low",    # Update review queue UI
}

ALL_UPDATES = {**TP_PRIORITIES, **FORAGE_PRIORITIES}
P = {"urgent": PriorityLevel.urgent, "high": PriorityLevel.high, "medium": PriorityLevel.medium, "low": PriorityLevel.low}

async def reprioritise():
    async with AsyncSessionLocal() as session:
        updated = 0
        for task_id, priority in ALL_UPDATES.items():
            await session.execute(
                update(Task)
                .where(Task.id == uuid.UUID(task_id))
                .values(priority=P[priority])
            )
            updated += 1
        await session.commit()
        print(f"Updated {updated} tasks")
        print()

        # Print summary
        for project_name, task_ids in [("Task Planner (Jun 15)", TP_PRIORITIES), ("Forage (Jun 18)", FORAGE_PRIORITIES)]:
            print(f"=== {project_name} ===")
            for p in ["urgent", "high", "medium", "low"]:
                ids = [tid for tid, pri in task_ids.items() if pri == p]
                if ids:
                    tasks = (await session.execute(select(Task).where(Task.id.in_([uuid.UUID(i) for i in ids])))).scalars().all()
                    for t in tasks:
                        print(f"  [{p.upper()}] {t.title[:65]}")
            print()

asyncio.run(reprioritise())
