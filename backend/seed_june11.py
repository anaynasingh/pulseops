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
    result = await session.execute(select(Project).where(Project.title == title).limit(1))
    return result.scalar_one_or_none()


async def seed():
    async with AsyncSessionLocal() as session:
        anayna = await get_user(session, "anayna.singh@prospect33.com")
        stephen = await get_user(session, "stephen.kamau@prospect33.com")
        mark = await get_user(session, "mark.clement@prospect33.com")

        tp = await get_project(session, "Task Planner App")
        rrp = await get_project(session, "RRP - Regulatory Reporting")
        infra = await get_project(session, "P33 Infrastructure")
        aigile = await get_project(session, "AIGile - Framework Development")

        p = PriorityLevel
        s = ProjectStatus

        tasks = [
            # ANAYNA
            (
                "Fix AI chatbot — allow project listing, less strict scoping",
                "Stephen tried to paste a project title and ask the chatbot about it — it refused due to overly strict out-of-context guardrails. The chatbot should allow questions about projects, tasks, and team work. Current implementation is too aggressive. Review and relax the out-of-scope rules so normal project queries work.",
                p.high, tp, date(2026, 6, 11), anayna
            ),
            (
                "Add conversation history to AI chatbot",
                "Stephen noted the AI assistant resets context after every message — it doesn't remember what was said earlier in the same chat. Add conversation history so the chatbot maintains context within a session. June 11 meeting feedback.",
                p.high, tp, date(2026, 6, 13), anayna
            ),
            (
                "Build full regression test suite for Task Planner app",
                "Mark's request from June 11 meeting. Currently only 3 manual tests exist (out-of-context, dedup, delete guardrails). Need a proper automated regression suite covering: all guardrails, authentication, task CRUD, privacy, MCP tools, and chatbot behaviour. Run automatically each time a change is deployed.",
                p.high, tp, date(2026, 6, 15), anayna
            ),
            (
                "Implement RBAC hard controls — database-level access control",
                "Mark's key feedback from June 11 meeting. Current guardrails are 'soft controls' (LLM prompt instructions) — LLMs can ignore these when context is large. Need 'hard controls' at the database level: when a user logs in, their user ID is captured and they can only write to DB rows they own/have access to. Even if LLM tries to delete someone else's task, the SQL query itself fails. Stephen suggested: LLM returns a status → passed to a function → function updates DB (no direct DB access for LLM). Research RBAC (Role-Based Access Control) patterns.",
                p.high, tp, date(2026, 6, 15), anayna
            ),
            # STEPHEN
            (
                "Switch RRP to use Carlo's atomizer — skip own pipeline",
                "Decision from June 11 meeting. Stephen has 49 items in review queue. Mark decided: don't build own atomization pipeline — use Carlo's existing DB directly. Stephen's job: add FIBO integration on top of Carlo's atoms and generate the knowledge graph. Carlo becomes responsible for atoms in his DB. This saves significant build time.",
                p.high, rrp, date(2026, 6, 16), stephen
            ),
            (
                "Deploy RRP burst 25",
                "Stephen has burst 25 (deployment work) almost ready. Target: deploy tomorrow (June 12) or Monday.",
                p.high, rrp, date(2026, 6, 12), stephen
            ),
            (
                "Extract DMARC report and analyse — send to Mark",
                "DMARC email reports are flooding Mark's inbox (2-3/day). Mark wrote a filter rule. Stephen to extract one DMARC report, check what's inside it, and send findings to Mark. June 11 action item.",
                p.medium, infra, date(2026, 6, 12), stephen
            ),
            # MARK
            (
                "Push AIGile update — Fable support + new Delegate skill",
                "Mark is updating AIGile to: (1) Use Fable model when available, auto-revert to Opus after June 22nd when Fable leaves subscription. (2) Add new 'Delegate' skill — replaces old 'Handover'. Old handover = create doc for Claude Code to read (misleadingly named). New delegate = send work to another builder (Codex, human, etc.). Stephen should wait for this before trying to use Codex for builds. Mark said he would push today.",
                p.high, aigile, date(2026, 6, 11), mark
            ),
            (
                "Build Fable loop architecture — Fable steers, Sonnet for sub-tasks",
                "Mark's architecture concept from June 11 meeting. Design a loop where: Fable acts as the orchestrator/planner (steering), delegates actual coding sub-tasks to Sonnet (cheaper). This avoids context explosion (cost is O(n²) in a loop) and keeps Fable context minimal. Fable clears between bursts via AIGile file-based context preservation. Explore using DeepSeek/Qwen 3.6 for even cheaper sub-agent coding.",
                p.medium, aigile, date(2026, 6, 15), mark
            ),
        ]

        added = 0
        for title, desc, priority, project, due_date, assignee in tasks:
            if not project:
                print(f"  SKIPPED (no project): {title[:50]}")
                continue
            task = Task(
                title=title, description=desc, status=ProjectStatus.todo,
                priority=priority, project_id=project.id,
                assigned_to=assignee.id, due_date=due_date
            )
            session.add(task); added += 1

        await session.commit()
        print(f"SUCCESS: Added {added} tasks from June 11 meeting")
        print("  Anayna: chatbot fix, history, test suite, RBAC")
        print("  Stephen: Carlo atomizer, burst 25 deploy, DMARC")
        print("  Mark: AIGile Fable + delegate skill, Fable loop architecture")

asyncio.run(seed())
