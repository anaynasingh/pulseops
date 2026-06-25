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


async def get_or_create_project(session, title, description, status, priority, owner_id, progress=0):
    result = await session.execute(select(Project).where(Project.title == title))
    p = result.scalar_one_or_none()
    if not p:
        p = Project(title=title, description=description, status=status, priority=priority, owner_id=owner_id, progress_pct=progress)
        session.add(p); await session.flush()
    return p


async def seed():
    async with AsyncSessionLocal() as session:
        anayna = await get_user(session, "anayna.singh@prospect33.com")
        stephen = await get_user(session, "stephen.kamau@prospect33.com")
        mark = await get_user(session, "mark.clement@prospect33.com")

        tp = await get_or_create_project(session, "Task Planner App", "AI task management platform", ProjectStatus.in_progress, PriorityLevel.high, anayna.id, 65)
        prep = await get_or_create_project(session, "PREP - Recruiting Platform", "AI recruitment platform with email, scheduling, and interview management", ProjectStatus.intake, PriorityLevel.high, anayna.id, 10)
        infra = await get_or_create_project(session, "P33 Infrastructure", "AWS migration, Railway setup, Cloudflare DNS, unified SSO landing page", ProjectStatus.in_progress, PriorityLevel.medium, stephen.id, 40)

        p = PriorityLevel
        s = ProjectStatus

        tasks = [
            # ── ANAYNA — Task Planner improvements ─────────────────────────────
            (
                "Add task reassignment — reallocate tasks to different person",
                "Feature request from June 10 meeting. Currently you can change priority/due date/description but cannot reassign a task to a different person. Add a reassign option in the task detail view and via Claude MCP. Mark: 'We should eat our own dog food and put this change request into the app.'",
                p.urgent, tp, date(2026, 6, 11), anayna
            ),
            (
                "Build task deduplication + smart update agent",
                "When all three team members upload the same meeting notes, the same task gets created 3 times. Build an AI agent that: (1) checks if a similar task already exists before creating a new one, (2) suggests updates to existing tasks based on meeting context — e.g. if a task says 'allow organising by project' and the demo just showed it works, agent suggests marking it complete. IMPORTANT: agent should SUGGEST updates, user confirms — no auto-apply.",
                p.high, tp, date(2026, 6, 13), anayna
            ),
            (
                "Add MCP guardrails — users can only edit their own tasks",
                "SECURITY: Currently Claude via MCP can edit/delete any task for any user. Mark raised: what stops someone from asking Claude to delete all tasks, or change Tom's deadlines to make him overdue? Fix: enforce task ownership at the API level — you can only edit/delete tasks assigned to you (or where you are a collaborator). Claude via MCP must obey the same restrictions as the UI.",
                p.high, tp, date(2026, 6, 12), anayna
            ),
            (
                "Build private tasks feature",
                "Feature from June 10 meeting. By default all tasks are visible to the whole team in Team view. Add a private flag to tasks: when marked private, only the creator and explicitly shared users can see it. Use case: Tom wants to assign a sensitive task to one person without others seeing it. Mark: 'By default all tasks visible to everybody, but you should be able to share a private task with someone specific.'",
                p.medium, tp, date(2026, 6, 15), anayna
            ),

            # ── ANAYNA — P33 Landing Page ───────────────────────────────────────
            (
                "Build P33 unified app landing page (SSO for all Railway apps)",
                "New project. Mark wants a single sign-on landing page for all P33 apps — log in once, access everything (Task Planner, PREP, TTR, LRR, Forage, etc.). Inspired by Kenya's eCitizen. MVP: (1) P33 staff log in once → see directory of all Railway apps (prod + dev versions), (2) External clients only see apps they have been invited to, (3) Hannah/Chege see only finance + recruitment apps. Mark: 'We want to manage access centrally rather than having to manage each app individually.' Work out architecture with Stephen — consider shared auth module.",
                p.high, infra, date(2026, 6, 20), anayna
            ),

            # ── ANAYNA — PREP ───────────────────────────────────────────────────
            (
                "Build PREP candidate application web form",
                "PREP email + scheduling feature from June 10 meeting. Build a web form for candidates to apply: captures name, address, salary expectation, remote/in-office preference, CV/resume upload. On submit: feeds into PREP CV analysis pipeline. Existing AI in PREP: CV analysis vs job spec, job spec review agent, vector DB semantic search, Pete33 chatbot.",
                p.high, prep, date(2026, 6, 18), anayna
            ),
            (
                "Build PREP automated rejection + interview invite emails",
                "Email integration for PREP. Two flows: (1) REJECTED: send polite rejection email — 'not suitable for this role, will keep CV on file in case something comes up'. (2) SHORTLISTED: send interview invite with booking link. Recruiters set this in PREP after reviewing AI screening results. Use the shared HR inbox in Microsoft Azure.",
                p.high, prep, date(2026, 6, 18), anayna
            ),
            (
                "Build PREP interview slot booking system (Calendly alternative)",
                "Build an in-house interview scheduling system (NOT Calendly — it's paid). Interviewers mark available slots in their calendar. Candidates see available slots and book one. Once a slot is booked, it becomes unavailable to other candidates. All interviews logged in the shared HR calendar. Individual interviewers also get a personal calendar invite. Work with Hannah to nail the exact workflow. Round 1 = Hannah/Chege, Round 2 = Monica/Tom or Mark depending on role type.",
                p.high, prep, date(2026, 6, 20), anayna
            ),
            (
                "Review PREP app and improve AI features",
                "Mark asked Anayna to explore the existing PREP app and suggest AI improvements. Existing AI in PREP: CV analysis vs job spec, job spec review agent, vector DB (ask 'which candidates have AI engineering skills?'), Pete33 embedded chatbot. Explore the app, identify gaps, and propose improvements — Mark: 'I don't care about getting what I think, I care about the best process we can get. Get Claude to think of improvements too.'",
                p.medium, prep, date(2026, 6, 17), anayna
            ),
            (
                "Work with Hannah to finalise PREP recruitment workflow",
                "Hannah is the primary user of PREP (along with Chege). She does all Round 1 interviews. Work with her to map out exactly how she wants the email flow, candidate management, and interview booking to work before building. Mark: 'Hannah is probably the best person to work out exactly how she would want that to work.'",
                p.medium, prep, date(2026, 6, 14), anayna
            ),

            # ── MARK ────────────────────────────────────────────────────────────
            (
                "Fix Railway admin access + Open Router access for Stephen and Anayna",
                "URGENT from June 10 meeting. Mark still hasn't given Stephen and Anayna admin access on Railway. Also needs to sort Open Router access for both. Mark said he would do this the morning of June 10. Do both at the same time.",
                p.urgent, infra, date(2026, 6, 10), mark
            ),
            (
                "Test Task Planner app and Claude MCP connection",
                "Mark agreed to test Anayna's Claude MCP setup instructions in the Task Planner app on June 10 morning. Test: (1) log into Railway app, (2) follow the Claude setup instructions (install Claude, connect M365, run the one-line MCP command), (3) verify Claude can read and create tasks in the app.",
                p.high, tp, date(2026, 6, 10), mark
            ),
            (
                "Test Fable model before June 22 free window closes",
                "Fable is Anthropic's 5-series model (watered down Mythos). Available free on subscription until June 22 2026, then pay-per-token. Mark warned it consumes tokens at an extremely rapid rate. Test it on one of our use cases before the window closes. Note: don't rely on it long-term — cost will be very high after June 22.",
                p.low, infra, date(2026, 6, 22), mark
            ),

            # ── STEPHEN ─────────────────────────────────────────────────────────
            (
                "Send Mark CSV of all AWS S3 bucket contents",
                "Stephen to create a CSV listing all P33 items stored in AWS S3 buckets. Send to Mark so they can decide together: keep, migrate to Railway/Cloudflare, or delete. Goal is to get off AWS almost entirely (reduce from ~£350/month to under £70/month).",
                p.medium, infra, date(2026, 6, 11), stephen
            ),
            (
                "Move contract app + Goldie app from AWS to Railway",
                "Two remaining apps on AWS: the contract app and the Goldie app. Move both to Railway. Stephen confirmed this is feasible.",
                p.medium, infra, date(2026, 6, 13), stephen
            ),
            (
                "Move DNS from Lot50 to Cloudflare",
                "Migrate P33 DNS from current provider (Lot50/ALot50) to Cloudflare. Stephen is handling this as part of the AWS migration work.",
                p.medium, infra, date(2026, 6, 14), stephen
            ),
            (
                "Delete BNY extraction instance from AWS",
                "The old BNY Mellon document extraction instance has been sitting unused on AWS for ~6 months. Forage replaces it. Mark confirmed: delete it, no longer needed. We have the repo so the code is preserved.",
                p.low, infra, date(2026, 6, 12), stephen
            ),
        ]

        added = 0
        for title, desc, priority, project, due_date, assignee in tasks:
            task = Task(title=title, description=desc, status=ProjectStatus.todo, priority=priority, project_id=project.id, assigned_to=assignee.id, due_date=due_date)
            session.add(task); added += 1

        await session.commit()
        print(f"SUCCESS: Added {added} tasks from June 10 meeting")
        print("  Anayna (9): Task reassignment, dedup agent, MCP guardrails, private tasks, P33 landing page, PREP (4 tasks)")
        print("  Mark (3): Railway/OR access, test MCP, test Fable")
        print("  Stephen (4): AWS S3 CSV, move apps, Cloudflare DNS, delete BNY")

asyncio.run(seed())
