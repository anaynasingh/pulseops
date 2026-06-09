import sys
sys.path.insert(0, '.')
import asyncio
from datetime import date
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.models import User, Project, Task, PriorityLevel, ProjectStatus, UserRole


async def get_user(session, email):
    result = await session.execute(select(User).where(User.email == email))
    u = result.scalar_one_or_none()
    if not u:
        name = email.split("@")[0].replace(".", " ").title()
        u = User(name=name, email=email, role=UserRole.contributor, is_active=True)
        session.add(u); await session.flush()
    return u


async def get_project(session, title):
    result = await session.execute(select(Project).where(Project.title == title))
    return result.scalar_one_or_none()


async def seed():
    async with AsyncSessionLocal() as session:
        try:
            anayna = await get_user(session, "anayna.singh@prospect33.com")
            stephen = await get_user(session, "stephen.kamau@prospect33.com")
            mark = await get_user(session, "mark.clement@prospect33.com")

            tp     = await get_project(session, "Task Planner App")
            rrp    = await get_project(session, "RRP - Regulatory Reporting")
            ttr    = await get_project(session, "TTR - Trade Tracking & Reporting")
            forage = await get_project(session, "Forage - AI Document Extraction")

            # Find or create AIGile project
            aigile = await get_project(session, "AIGile - Framework Development")
            if not aigile:
                aigile = Project(
                    title="AIGile - Framework Development",
                    description="AIGile methodology improvements: Codex↔Claude handover skill, retrospective hardening, AGENTS.md.",
                    status=ProjectStatus.in_progress, priority=PriorityLevel.medium,
                    owner_id=mark.id, progress_pct=60
                )
                session.add(aigile); await session.flush()

            p = PriorityLevel
            s = ProjectStatus

            tasks = [
                # ── ANAYNA — Task Planner ────────────────────────────────────────
                (
                    "Fix session persistence — logout on refresh (Railway)",
                    "BUG: Stephen tested Railway app and gets logged out every time he refreshes the page. Session/JWT is not being persisted correctly in the browser. Fix auth token storage so users stay logged in across refreshes. Likely needs token stored in localStorage or httpOnly cookie that survives page reload.",
                    p.urgent, tp, date(2026, 6, 9), anayna
                ),
                (
                    "Add self-service Claude/MCP connection at login",
                    "Currently only Anayna's Claude is connected to the app. Mark and Stephen can't use AI features. Mark: 'You shouldn't have to do it for every user — make it self-service.' Add a step during login/onboarding where each user can connect their own Claude instance to the app. Should take ~5 minutes per user. Mark said this is the right approach rather than Anayna manually setting it up for each person.",
                    p.high, tp, date(2026, 6, 9), anayna
                ),
                (
                    "Make Task Planner mobile responsive",
                    "Stephen tried the app on his phone in the morning — it's not mobile responsive. The layout breaks on small screens. Add responsive Tailwind classes so the dashboard, task list, Kanban board etc. work properly on mobile. Stephen's feedback from June 9 meeting.",
                    p.high, tp, date(2026, 6, 12), anayna
                ),
                (
                    "Scope AI chatbot to app-only questions",
                    "Stephen's feedback: The AI chatbot on the right side of the app should only answer questions related to the app, projects, and tasks. If someone asks something outside scope, it should politely decline and say 'we don't do that here.' Add a system prompt constraint to the chatbot endpoint so it stays focused on task management and team workflows only.",
                    p.medium, tp, date(2026, 6, 12), anayna
                ),
                (
                    "Switch to Codex for frontend UI redesign",
                    "Anayna raised that Claude Code isn't producing very appealing UI designs. Mark agreed — Codex is better for UI work in his experience. Try using Codex (instead of Claude Code) to redesign and improve the frontend UI, especially the dashboard, task cards, and Gantt chart visual styling.",
                    p.medium, tp, date(2026, 6, 13), anayna
                ),

                # ── STEPHEN — RRP ────────────────────────────────────────────────
                (
                    "Complete RRP burst 23 full document atomization and review results",
                    "Stephen started burst 23 which is running the FULL EMEA regulation document atomization (not just Section 4). At the June 9 meeting it was 80% complete after 1 hour (~3000 items processed). Let the run complete, then review results: did it work correctly? What was the cost? What quality are the atoms? Mark was originally planning Section 4 first to test costs — now we need to assess full doc results.",
                    p.urgent, rrp, date(2026, 6, 9), stephen
                ),
                (
                    "Try Organisation Access level on OpenRouter API",
                    "Stephen has been using 'User Full Access' which now works for most meetings. Mark suggested also trying 'Organisation Access' level which might give access to ALL meetings including the dev meeting and Tom Tuesday meeting. Current status: dev meeting and Tom Tuesday still not pulling via transcript API because they're flagged as internal (all @prospect33.com attendees).",
                    p.medium, rrp, date(2026, 6, 10), stephen
                ),
                (
                    "Test Railway Task Planner fully and send feedback to Anayna",
                    "Stephen confirmed Railway app now works but found the refresh/logout bug. Continue testing all features: dashboard, Kanban board, Gantt chart, AI intake, task completion, light mode. Send structured feedback to Anayna with any bugs or UX issues found.",
                    p.medium, tp, date(2026, 6, 10), stephen
                ),

                # ── STEPHEN — TTR ────────────────────────────────────────────────
                (
                    "Implement HEEL for TTR rules/alerts classifier",
                    "Mark assigned this to Stephen. HEEL (Human-Empowered Entity Learning) needs to be implemented for the TTR rules/alerts classifier — same approach used for the anomaly detector. This allows the classifier to learn from human feedback on true positives and false positives, improving accuracy over time.",
                    p.high, ttr, date(2026, 6, 13), stephen
                ),
                (
                    "Generate more rule alerts to balance TTR dataset",
                    "CRITICAL DATA ISSUE: TTR has ~2,000 anomaly detections but only ~200 rule alerts. The classifier is heavily biased toward anomaly detection because of this imbalance. Need to generate significantly more rule alerts to balance the training data before HEEL can work effectively. Mark flagged this in the June 9 meeting.",
                    p.high, ttr, date(2026, 6, 12), stephen
                ),

                # ── MARK — TTR handover ──────────────────────────────────────────
                (
                    "Send TTR Railway link + .env file to Stephen, Tom, Carlo for feedback",
                    "Mark has TTR (Accurate) deployed on Railway with the new combined intelligence view and tour/demo mode. Two actions: (1) Send .env file to Stephen with all OpenRouter API keys including the reg-reasoning key. (2) Send the TTR Railway link to Stephen, Tom, and Carlo and ask them to look at it and give feedback. Mark told Tom yesterday and showed him the app.",
                    p.urgent, ttr, date(2026, 6, 9), mark
                ),

                # ── MARK — Forage ────────────────────────────────────────────────
                (
                    "Build Forage human feedback and ground truth capture interface",
                    "Mark is building a test piece to simulate human accuracy as a baseline. Before we can measure AI performance vs human on document extraction, we need to know what human accuracy looks like. Anayna offered to do 5 documents/day but Mark said there's no system to capture it yet in a structured way. Build the interface in the next 2-3 days. Will start with loan documents only (not red notices yet). Once live, all 3 team members can start contributing.",
                    p.high, forage, date(2026, 6, 12), mark
                ),
                (
                    "Build demo mode into Forage app",
                    "Tom is lining up demos for Forage, Accurate (TTR), and AIGile — more than a week away. Mark wants to build demo mode into Forage (same as TTR) so the app is always demo-ready without needing to create PowerPoints. Mark: 'Much easier to ensure we are always demo ready if the demo is built into the app itself.' Do this before the first demo.",
                    p.high, forage, date(2026, 6, 16), mark
                ),

                # ── MARK — AIGile ────────────────────────────────────────────────
                (
                    "Build Codex to Claude AIGile handover skill",
                    "Currently when Mark does Codex bursts (e.g. TTR UI work), he has to manually tell AIGile exactly what Codex changed so it can process them. Build a proper skill: write an AGENTS.md file in the repo so Codex picks up instructions and communicates back to Claude what it did. Goal: enable seamless Codex bursts within AIGile workflow without manual intervention. Mark is already writing the AGENTS.md.",
                    p.medium, aigile, date(2026, 6, 13), mark
                ),
            ]

            added = 0
            for title, desc, priority, project, due_date, assignee in tasks:
                if not project:
                    print(f"  SKIPPED (no project): {title[:50]}")
                    continue
                task = Task(
                    title=title, description=desc, status=s.todo,
                    priority=priority, project_id=project.id,
                    assigned_to=assignee.id, due_date=due_date
                )
                session.add(task); added += 1

            await session.commit()
            print(f"SUCCESS: Added {added} tasks from June 9 meeting")
            print("  Anayna (5): Session fix, Claude self-service, mobile, chatbot scope, Codex UI")
            print("  Stephen (5): RRP atomization, org API, Railway test, HEEL, dataset balance")
            print("  Mark (4): Send .env + TTR link, Forage feedback UI, Forage demo mode, AIGile skill")

        except Exception as e:
            await session.rollback()
            print(f"ERROR: {e}")
            import traceback; traceback.print_exc()

asyncio.run(seed())
