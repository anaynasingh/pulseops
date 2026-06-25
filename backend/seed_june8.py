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
        session.add(u)
        await session.flush()
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

            tp = await get_project(session, "Task Planner App")
            rrp = await get_project(session, "RRP - Regulatory Reporting")
            lrr = await get_project(session, "LRR - Standalone Alert Review")
            ttr = await get_project(session, "TTR - Trade Tracking & Reporting")
            forage = await get_project(session, "Forage - AI Document Extraction")

            # June 8 tasks: (title, desc, priority, project, due_date, assignee)
            tasks = [
                # ANAYNA — Task Planner fixes
                (
                    "Add light/dark mode toggle",
                    "Tom will specifically ask for a light background. Add switchable light/dark mode to the Task Planner app. Light mode should be the option when toggled. Dark mode is current default.",
                    "high", tp, date(2026, 6, 9), anayna
                ),
                (
                    "Add 'Retire / Not Required' task status",
                    "Currently tasks can only be marked complete. Need a way to retire/abandon a task without completing it. Mark's feedback: 'What if we decide to abandon something? We should be able to retire a task without completing it - move it to Not Required.' Add this as a separate status/action distinct from complete.",
                    "high", tp, date(2026, 6, 9), anayna
                ),
                (
                    "Fix Gantt chart - proper deadlines, expand/collapse, dependencies",
                    "Gantt chart issues from June 8 demo: (1) All tasks default to 1-month timeline when no deadline set - fix with real deadlines. (2) Add proper dependency ordering - task B cannot start until task A is done. (3) Add expand/collapse - summary view by default (project bars), click to expand subtasks below, Expand All / Collapse All buttons. Mark: 'with one view you could have summary or detailed view, just two clicks away.'",
                    "high", tp, date(2026, 6, 10), anayna
                ),
                (
                    "Fix CORS - add Stephen's URL to backend whitelist",
                    "Stephen is getting a 500 error when trying to log in to the Railway app. Root cause: CORS issue - Stephen's frontend URL is not whitelisted on the backend. Add his URL to ALLOWED_ORIGINS in the Railway backend environment variables.",
                    "high", tp, date(2026, 6, 9), anayna
                ),
                (
                    "Send login credentials to Mark and Stephen via Teams",
                    "Mark asked Anayna to email/Teams-message the Task Planner Railway login credentials. Mark and Stephen need them to access and test the deployed app. Email or Teams message: URL + email + password for each person.",
                    "urgent", tp, date(2026, 6, 9), anayna
                ),
                (
                    "Fix focus reminder - showing wrong tasks",
                    "During demo the reminder pop-up showed 'no incomplete tasks' even though tasks existed. It was showing group tasks instead of personal ones. Fix reminder to only show tasks assigned to the logged-in user, ordered by priority.",
                    "medium", tp, date(2026, 6, 10), anayna
                ),

                # STEPHEN — Task Planner
                (
                    "Send meeting transcript API to Anayna",
                    "Anayna requested this again during the June 8 meeting - the dashboard reminder was flagging it. Stephen agreed to send it. This API allows the Task Planner to reliably fetch Teams meeting transcripts instead of relying on unreliable Microsoft Graph search.",
                    "high", tp, date(2026, 6, 9), stephen
                ),

                # STEPHEN — RRP
                (
                    "Run RRP Section 4 extraction on OpenRouter",
                    "Mark has set up the next AIGile burst to run on Section 4 of EMEA regulation (not the whole doc, to save AI credits) across 3-4 OpenRouter models. Stephen to run this extraction to create atoms and test the pipeline. Won't cost too many credits since it's just Section 4. Check if it runs cleanly before doing the full document.",
                    "high", rrp, date(2026, 6, 10), stephen
                ),
                (
                    "Run /ag-plan on RRP to understand current state",
                    "Mark: 'Run ag-plan and ask it where it's up to and what needs doing next - it should work out what to do.' Stephen to run AIGile's /ag-plan on the RRP repo to get a clear picture of what has been done and what the next steps are before diving into code changes.",
                    "high", rrp, date(2026, 6, 9), stephen
                ),
                (
                    "Build RRP graph visualisation view",
                    "Stephen wants to build a first stage where you can view the full knowledge graph (atoms + FIBO connections), then scroll/click into parts of it to drill down. Mark agreed. This gives users a way to see the complete regulatory universe and navigate it visually before doing queries.",
                    "medium", rrp, date(2026, 6, 12), stephen
                ),
                (
                    "Update RRP README - commands are out of date",
                    "Mark confirmed the README is very outdated. Commands Stephen tried to follow don't match the actual files in the repo. Mark: 'I haven't updated that README in a long time - probably very out of date.' Update README with current commands, file structure, and how to run the extraction pipeline.",
                    "medium", rrp, date(2026, 6, 10), stephen
                ),

                # STEPHEN — TTR
                (
                    "Run HEEL on TTR classifier",
                    "Mark assigned this to Stephen. Once true positives and false positives are known, they can train the classifier using human feedback - same approach used for the anomaly detector. This improves auto-classification rate and reduces human review needed. Mark will handle the UI; Stephen handles the data science integration.",
                    "medium", ttr, date(2026, 6, 12), stephen
                ),

                # MARK — TTR
                (
                    "Push TTR combined intelligence UI to dev branch",
                    "Mark built the new TTR combined intelligence view in Codex (not Claude). Needs to push it to the dev branch. Challenge: work was done in Codex so needs to be patched back into the AIGile-managed branch. Combined intelligence view brings classifier + anomaly detector together in one screen, replaces the two separate queue screens.",
                    "high", ttr, date(2026, 6, 9), mark
                ),
                (
                    "Fix TTR Gantt re-render bug",
                    "Bug observed during demo: after closing trade detail screen, the screen was not re-rendering correctly. Mark: 'It still thinks the trade details are still up - that's weird.' Investigate and fix the re-render issue in the combined intelligence view.",
                    "medium", ttr, date(2026, 6, 10), mark
                ),
                (
                    "Tweak TTR confidence algorithm for auto-classifier",
                    "Mark wants to adjust the algorithm for determining confidence in a classification answer. Goal: push more items into the auto-classifier (less requiring human review). The more that gets auto-classified correctly, the more value the product demonstrates. Mark will do this alongside the UI work.",
                    "medium", ttr, date(2026, 6, 12), mark
                ),

                # MARK — Forage + Admin
                (
                    "Write Forage design doc (combined intelligence approach)",
                    "Mark has a design written for Forage. Plans to apply same pattern as TTR: built-in help section + demo mode. Stopped working on Forage on Friday to focus on TTR. Will resume after pushing TTR changes. Write the design document to align the team before building.",
                    "medium", forage, date(2026, 6, 12), mark
                ),
                (
                    "Change Monday/Friday dev meeting times",
                    "Mark cannot make 10am on Mondays and Fridays. Needs to reschedule the recurring dev meeting to a time he can attend. Friday meetings may also not be needed separately since the Tom weekly already happens on Fridays. Mark also wants to try moving the Tom weekly meeting to an earlier time.",
                    "low", tp, date(2026, 6, 9), mark
                ),
            ]

            added = 0
            for title, desc, priority, project, due_date, assignee in tasks:
                if project is None:
                    print(f"  SKIPPED (no project): {title}")
                    continue
                p_map = {"urgent": PriorityLevel.urgent, "high": PriorityLevel.high, "medium": PriorityLevel.medium, "low": PriorityLevel.low}
                task = Task(
                    title=title,
                    description=desc,
                    status=ProjectStatus.todo,
                    priority=p_map[priority],
                    project_id=project.id,
                    assigned_to=assignee.id,
                    due_date=due_date
                )
                session.add(task)
                added += 1

            await session.commit()
            print(f"SUCCESS: Added {added} tasks from June 8 meeting")
            print("  Anayna (6): Light/dark mode, Retire task, Gantt fix, CORS, send creds, reminder fix")
            print("  Stephen (5): Transcript API, RRP extraction, ag-plan, graph viz, README, HEEL")
            print("  Mark (4): Push TTR UI, re-render bug, confidence algo, Forage design, meeting reschedule")

        except Exception as e:
            await session.rollback()
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

asyncio.run(seed())
