import sys
sys.path.insert(0, '.')
import asyncio
from datetime import date
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import User, Project, Task, PriorityLevel, ProjectStatus, UserRole


async def get_or_create_user(session, email: str) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user
    name = email.split("@")[0].replace(".", " ").title()
    user = User(name=name, email=email, role=UserRole.contributor, is_active=True)
    session.add(user)
    await session.flush()
    return user


async def get_or_create_project(session, title: str, description: str, status: ProjectStatus, priority: PriorityLevel, owner_id, progress: int = 0) -> Project:
    result = await session.execute(select(Project).where(Project.title == title))
    proj = result.scalar_one_or_none()
    if proj:
        return proj
    proj = Project(
        title=title,
        description=description,
        status=status,
        priority=priority,
        owner_id=owner_id,
        progress_pct=progress
    )
    session.add(proj)
    await session.flush()
    return proj


async def seed():
    async with AsyncSessionLocal() as session:
        try:
            anayna = await get_or_create_user(session, "anayna.singh@prospect33.com")
            stephen = await get_or_create_user(session, "stephen.kamau@prospect33.com")
            mark = await get_or_create_user(session, "mark.clement@prospect33.com")

            # Projects
            tp = await get_or_create_project(session,
                "Task Planner App",
                "AI-native task management and workflow intelligence platform. Deployed on Railway for team use.",
                ProjectStatus.in_progress, PriorityLevel.high, anayna.id, 65)

            forage = await get_or_create_project(session,
                "Forage - AI Document Extraction",
                "Pluggable Foragers framework. Forager 1 = Anayna RAG, Forager 2 = Stephen agentic. Supports multiple document types including KYC.",
                ProjectStatus.in_progress, PriorityLevel.high, mark.id, 35)

            rrp = await get_or_create_project(session,
                "RRP - Regulatory Reporting",
                "AI-powered regulatory reporting pipeline with FIBO ontology. Handed to Stephen. 9-hour atomization problem to fix.",
                ProjectStatus.in_progress, PriorityLevel.high, stephen.id, 30)

            lrr = await get_or_create_project(session,
                "LRR - Standalone Alert Review",
                "Standalone alert review app with Kanban board, anomaly queue, and Method Test Pack tab.",
                ProjectStatus.in_progress, PriorityLevel.high, stephen.id, 70)

            ttr = await get_or_create_project(session,
                "TTR - Trade Tracking & Reporting",
                "Trade tracking system. Mark to do UI analysis once Stephen takes over RRP.",
                ProjectStatus.in_progress, PriorityLevel.medium, mark.id, 50)

            # All tasks from June 4 meeting
            tasks = [
                # ANAYNA - Task Planner
                (
                    "Fix multi-user assignment bug in Task Planner",
                    "BUG: Only Anayna exists in the backend DB. UI shows tasks assigned to Mark/Stephen/Anayna but in the database everything maps to Anayna's user ID. Need to create real user accounts for Mark and Stephen and wire up assignment correctly so tasks are actually assigned to the right people.",
                    "high", tp.id, date(2026, 6, 5), anayna.id
                ),
                (
                    "Deploy Task Planner on Railway",
                    "Deploy the Task Planner app on Railway so the whole team can use it. Mark confirmed Anayna has (or will get) admin Railway access. Required before Mark and Stephen can test it themselves.",
                    "high", tp.id, date(2026, 6, 5), anayna.id
                ),
                (
                    "Clean up stale tasks in Task Planner",
                    "Old tasks from old meeting transcripts are polluting the reminder/priority list (e.g. 'clean up dead code in Forage', 'help Stephen on accurate'). Clear these out so the reminder system shows the correct current priorities.",
                    "medium", tp.id, date(2026, 6, 5), anayna.id
                ),
                (
                    "Show Task Planner to Tom in weekly meeting",
                    "Demo the working Task Planner app to Tom in tomorrow's 4-hour weekly meeting. Show: reminder system (15/20/30 min toggle), Kanban board, priority ordering, email task extraction. Mark will handle Forage progress separately.",
                    "high", tp.id, date(2026, 6, 5), anayna.id
                ),
                (
                    "Add logging to meeting transcript search for diagnostics",
                    "Microsoft Graph search is unreliable - sometimes pulls the wrong meeting transcript. Add logging to capture when it gets the right vs wrong meeting so Claude can do diagnostics and find a pattern. Mark: 'It shouldn't be entirely random - maybe there's a pattern to it.'",
                    "medium", tp.id, date(2026, 6, 7), anayna.id
                ),

                # STEPHEN - Meeting transcript API
                (
                    "Provide Anayna with meeting transcription API",
                    "Stephen has a transcription API that can fetch meeting transcripts directly. Promised to give it to Anayna tomorrow (June 5). This will fix the unreliable Microsoft Graph transcript search in the Task Planner.",
                    "high", tp.id, date(2026, 6, 5), stephen.id
                ),

                # FORAGE
                (
                    "Compare RAG vs agentic extraction approaches in Forage",
                    "Anayna to look into Stephen's agentic Forage extraction and compare with her RAG approach. This is the Forager 1 (Anayna RAG) vs Forager 2 (Stephen agentic) comparison. Goal: understand where each technique works best across different document types.",
                    "medium", forage.id, date(2026, 6, 5), anayna.id
                ),
                (
                    "Build AI human component for Edgar daily process feedback",
                    "Mark has designed the component that simulates human work. Next step: build the AI human so the team can start giving feedback on the Edgar daily process. This is the backend foundation for the Forage human-in-the-loop evaluation pipeline.",
                    "high", forage.id, date(2026, 6, 6), mark.id
                ),
                (
                    "Design pluggable Foragers architecture",
                    "DECIDED in June 4 meeting: Forage = overall process, Foragers = pluggable extraction techniques underneath. Current: Forager 1 (Anayna RAG) + Forager 2 (Stephen agentic). Design so any extractor can be inserted. Future forager needed for KYC (photos, passports, driving licenses - OCR-based). Different foraging techniques for different document types.",
                    "high", forage.id, date(2026, 6, 7), mark.id
                ),

                # RRP
                (
                    "Take over RRP from Mark",
                    "Mark is stepping back from active RRP development. Stephen to take over the RRP project. Mark will use the AIGile handover document skill to generate documentation first. Once Stephen has RRP, Mark gets capacity back for TTR UI work.",
                    "high", rrp.id, date(2026, 6, 5), stephen.id
                ),
                (
                    "Fix RRP 9-hour atomization problem",
                    "BLOCKER: Mark's RRP atomization pipeline estimated 9 HOURS to process a single document on OpenRouter. Root cause: atomization + FIBO connection is too slow with current chunking approach. Possible fix: leverage Carlo's atomizer instead of building from scratch. Mark decided to let Stephen investigate this.",
                    "high", rrp.id, date(2026, 6, 7), stephen.id
                ),

                # LRR
                (
                    "Create test_trades table for 15 LRR test threads",
                    "Stephen has 15 anomalous test trades in JSON format (provided by client, worked on with Veronica). Currently NOT in the main trade table (correct - would mess up train/test splits). Mark's suggestion: create a dedicated test_trades table so they can be managed, queried, and added to over time. Stephen agreed to implement this.",
                    "high", lrr.id, date(2026, 6, 5), stephen.id
                ),
                (
                    "Fix SHAP explanation - match anomalies to ground truth root causes",
                    "SHAP feature engineering update: counterparty, settlement, notional, and rate appear in top 3 SHAP values (good). Late trading days + time did not improve score. Next step: build something that matches detected anomalies to root causes in the ground truth table. Problem: the 15 client test trades don't include root cause reasons, just anomaly flags. Need to work around this.",
                    "high", lrr.id, date(2026, 6, 7), stephen.id
                ),

                # TTR
                (
                    "TTR UI - analysis pass (no changes yet)",
                    "Mark will do an analysis pass on the TTR UI once Stephen has taken over RRP and freed up Mark's capacity. No changes at this stage - just analysis and assessment of what needs to be done.",
                    "medium", ttr.id, date(2026, 6, 8), mark.id
                ),

                # GENERAL - Tom meeting prep
                (
                    "Pre-Tom catch-up with team before weekly meeting",
                    "Quick team sync before the 4-hour weekly meeting with Tom on June 5. Mark busy in the morning so catch-up will be in the afternoon (a couple of hours before the Tom meeting). Goal: align on what everyone will present.",
                    "high", tp.id, date(2026, 6, 5), mark.id
                ),
            ]

            added = 0
            for title, desc, priority, project_id, due_date, assignee_id in tasks:
                priority_map = {"high": PriorityLevel.high, "medium": PriorityLevel.medium, "low": PriorityLevel.low}
                task = Task(
                    title=title,
                    description=desc,
                    status=ProjectStatus.todo,
                    priority=priority_map[priority],
                    project_id=project_id,
                    assigned_to=assignee_id,
                    due_date=due_date
                )
                session.add(task)
                added += 1

            await session.commit()
            print(f"SUCCESS: Added {added} tasks from June 4 meeting")
            print("  Anayna (5): Task Planner fixes, Railway deploy, Tom demo, stale tasks, logging")
            print("  Stephen (5): Transcript API, test_trades table, SHAP fix, RRP takeover, RRP atomization")
            print("  Mark (4): Edgar AI human, Foragers architecture, TTR analysis, Tom catch-up")
            print("")
            print("  Projects touched: Task Planner, Forage, RRP, LRR, TTR")

        except Exception as e:
            await session.rollback()
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(seed())
