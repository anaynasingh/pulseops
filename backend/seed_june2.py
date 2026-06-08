import sys
sys.path.insert(0, '.')
import asyncio
from datetime import date
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import User, Project, Task, PriorityLevel, ProjectStatus, UserRole


async def _find_or_create_user_by_email(session, email: str) -> User:
    """Find user by email or create a placeholder account with a name derived from the email."""
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user:
        return user
    name = email.split("@")[0].replace(".", " ").title()
    user = User(name=name, email=email, role=UserRole.contributor, is_active=True)
    session.add(user)
    await session.flush()
    return user


async def add_june2_tasks():
    async with AsyncSessionLocal() as session:
        try:
            # Get user
            result = await session.execute(select(User).where(User.email == "anayna.singh@prospect33.com"))
            user = result.scalar_one()
            user_id = user.id

            # Get existing projects
            result = await session.execute(select(Project).where(Project.title == "Forage - AI Document Extraction"))
            forage = result.scalar_one_or_none()
            forage_id = forage.id if forage else None

            # Create RRP project if not exists
            result = await session.execute(select(Project).where(Project.title == "RRP - Regulatory Reporting"))
            rrp = result.scalar_one_or_none()
            if not rrp:
                rrp = Project(
                    title="RRP - Regulatory Reporting",
                    description="AI-powered regulatory reporting pipeline. Atomizes regulatory documents with FIBO ontology. Moving to OpenRouter for full context window support.",
                    status=ProjectStatus.in_progress,
                    priority=PriorityLevel.high,
                    owner_id=user_id,
                    progress_pct=30
                )
                session.add(rrp)
                await session.flush()
            rrp_id = rrp.id

            # Create Task Planner project if not exists
            result = await session.execute(select(Project).where(Project.title == "PulseOps - Task Planner App"))
            tp = result.scalar_one_or_none()
            if not tp:
                tp = Project(
                    title="PulseOps - Task Planner App",
                    description="AI-native task management and workflow intelligence platform. First AIGile project for Anayna.",
                    status=ProjectStatus.in_progress,
                    priority=PriorityLevel.high,
                    owner_id=user_id,
                    progress_pct=60
                )
                session.add(tp)
                await session.flush()
            tp_id = tp.id

            # Create LRR project if not exists
            result = await session.execute(select(Project).where(Project.title == "LRR - Standalone Alert Review"))
            lrr = result.scalar_one_or_none()
            if not lrr:
                lrr = Project(
                    title="LRR - Standalone Alert Review",
                    description="Standalone Loan Review and Reporting application. Separate from TTR, includes Kanban board and anomaly review queue.",
                    status=ProjectStatus.in_progress,
                    priority=PriorityLevel.high,
                    owner_id=user_id,
                    progress_pct=70
                )
                session.add(lrr)
                await session.flush()
            lrr_id = lrr.id

            # All June 2 tasks - (title, desc, priority, project_id, due_date, assignee_email)
            tasks = [
                (
                    "QA task planner app - test all features & find bugs",
                    "Full QA pass on PulseOps task planner: go through entire UI, test every feature, use Claude Code to find and run test cases. Also test multi-user scenarios (currently only single-user tested). Goal: get it working smoothly ASAP so team can start using it.",
                    "high", tp_id, date(2026, 6, 4), "anayna.singh@prospect33.com"
                ),
                (
                    "Install AIGile via WSL on Windows 11",
                    "AIGile requires bash commands - must use WSL (Windows Subsystem for Linux) on Windows 11. Steps: (1) Set up WSL, (2) Use Claude Code to fetch and install AIGile repo - tell Claude: fetch the repo and install it in this directory + provide Git URL. Desktop Claude Code will NOT work for this.",
                    "high", tp_id, date(2026, 6, 5), "anayna.singh@prospect33.com"
                ),
                (
                    "Use task planner as first AIGile project",
                    "Once task planner is working and AIGile is installed: (1) Adopt AIGile on task planner repo, (2) AIGile creates charter template based on codebase, (3) Link GitHub repo to Claude, (4) Ask Claude to suggest features, (5) Build better charter iteratively. This is Anayna's first real AIGile adoption.",
                    "medium", tp_id, date(2026, 6, 7), "anayna.singh@prospect33.com"
                ),
                (
                    "Set up practice repo for AIGile conversion",
                    "Before converting any real project to AIGile, do a trial run on a practice/test repository. Mark offered to support when Anayna is ready. Agreed in meeting: practice repo first, then apply to real projects.",
                    "medium", tp_id, date(2026, 6, 7), "anayna.singh@prospect33.com"
                ),
                (
                    "FIX: Anomaly detection flagging wrong field (time vs rare counterparty)",
                    "CRITICAL BUG: First trade in exception/anomaly queue is flagged for the WRONG reason. Ground truth: trade should flag because it is a RARE COUNTERPARTY (counterparty that has never done this type of trade before). Current behaviour: system flags based on TIME as anomalous field. None of the fields are picking up the rare counterparty signal. How to check: click anomaly details -> top left corner shows ground truth category.",
                    "high", lrr_id, date(2026, 6, 5), "stephen.kamau@prospect33.com"
                ),
                (
                    "FIX: LRR Kanban and alert review panel height alignment",
                    "UI bug: bottom of the Kanban board and the alert review detail panel are not aligned. The height of the detail panel is slightly bigger than the Kanban. Root cause: 4th Escalate board for admin view adds extra height. Fix: ensure all panel bottoms align at the same height, whether escalate board is kept or removed.",
                    "medium", lrr_id, date(2026, 6, 5), "stephen.kamau@prospect33.com"
                ),
                (
                    "BLOCKED: Wait for Veronica realistic RRP test data",
                    "BLOCKED: RRP efficiency queue needs realistic test data from Veronica (similar to HSBC data). Currently just converting existing feeds with no specific regime. Once Veronica delivers, put data behind the try with a normal record button in the app to populate realistic thread data.",
                    "medium", rrp_id, None, "stephen.kamau@prospect33.com"
                ),
                (
                    "Get RRP working on OpenRouter - drop local LLM",
                    "DECISION from June 2 meeting: Move RRP from local LLM to OpenRouter. Reason: local LLM max context is 128K (some only 64K). FIBO alone is 36K tokens - impossible to fit FIBO + reg document simultaneously on local model. OpenRouter gives 1M+ context = no chunking needed. Model: ChatGPT GPT-4o Mini on OpenRouter for FIBO prompt caching (load FIBO once, cached, subsequent prompts = 10% cost). No Tailscale needed anymore.",
                    "high", rrp_id, date(2026, 6, 5), "mark.clement@prospect33.com"
                ),
                (
                    "Create RRP handover document for Stephen using AIGile skill",
                    "Test the AIGile handover document skill (never used before) to generate a developer handover doc for RRP. First get OpenRouter working in RRP, then generate the handover doc, then hand off to Stephen. Stephen needs documentation on how RRP works before he can take it on.",
                    "high", rrp_id, date(2026, 6, 7), "mark.clement@prospect33.com"
                ),
                (
                    "Ask Tom: what is the hourly reminder time-management technique called?",
                    "Tom mentioned a technique he used in the past: reminders every hour telling you what you should be working on. Mark thinks this should be opt-in only (not everyone wants hourly interruptions). NOT MVP - future feature for task planner. Mark to ask Tom for the name of the technique so it can be researched and potentially added later.",
                    "low", tp_id, date(2026, 6, 5), "mark.clement@prospect33.com"
                ),
            ]

            priority_map = {"high": PriorityLevel.high, "medium": PriorityLevel.medium, "low": PriorityLevel.low}
            added = 0
            updated = 0
            for title, desc, priority, project_id, due_date, assignee_email in tasks:
                # Always resolve the real user — create their account if it doesn't exist yet
                assignee = await _find_or_create_user_by_email(session, assignee_email)
                assignee_id = assignee.id

                # If a task with this title already exists in the project, fix its assignee
                # instead of creating a duplicate
                existing = await session.execute(
                    select(Task).where(Task.title == title, Task.project_id == project_id)
                )
                task = existing.scalar_one_or_none()
                if task:
                    task.assigned_to = assignee_id
                    updated += 1
                else:
                    task = Task(
                        title=title,
                        description=desc,
                        status=ProjectStatus.todo,
                        priority=priority_map[priority],
                        project_id=project_id,
                        assigned_to=assignee_id,
                        due_date=due_date,
                    )
                    session.add(task)
                    added += 1

            await session.commit()
            print(f"SUCCESS: Added {added} new tasks, fixed assignee on {updated} existing tasks from June 2 meeting")
            print("  Anayna: QA task planner, Install AIGile via WSL, First AIGile project, Practice repo")
            print("  Stephen: Fix anomaly detection bug, Fix LRR alignment, Wait for Veronica data")
            print("  Mark: RRP to OpenRouter, RRP handover doc, Ask Tom about technique")

        except Exception as e:
            await session.rollback()
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(add_june2_tasks())
