"""
Full regression test suite for the Task Planner app.

Run against the live local backend:
  uvicorn app.main:app --host 127.0.0.1 --port 8001
  pytest tests/test_regression.py -v

Covers: authentication, task CRUD, privacy, project RBAC, chatbot, MCP (skipped).
"""
import asyncio
import uuid

import pytest
import httpx

BASE = "http://localhost:8001/api/v1"
CLIENT = httpx.Client(timeout=30.0)

# ── Helpers ───────────────────────────────────────────────────────────────────

def login(email, password):
    r = CLIENT.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return r.json()["access_token"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def get_tasks(token, **params):
    r = CLIENT.get(f"{BASE}/tasks/", headers=auth(token), params=params)
    assert r.status_code == 200
    return r.json()

def get_projects(token, **params):
    r = CLIENT.get(f"{BASE}/projects/", headers=auth(token), params=params)
    assert r.status_code == 200
    return r.json()

def patch_task(token, task_id, data):
    return CLIENT.patch(f"{BASE}/tasks/{task_id}", json=data, headers=auth(token))

def delete_task(token, task_id):
    return CLIENT.delete(f"{BASE}/tasks/{task_id}", headers=auth(token))

def patch_project(token, project_id, data):
    return CLIENT.patch(f"{BASE}/projects/{project_id}", json=data, headers=auth(token))

def delete_project(token, project_id):
    return CLIENT.delete(f"{BASE}/projects/{project_id}", headers=auth(token))


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def anayna_token():
    return login("anayna.singh@prospect33.com", "PulseOps2026!")

@pytest.fixture(scope="module")
def stephen_token():
    return login("stephen.kamau@prospect33.com", "StephenP33!2026")

@pytest.fixture(scope="module")
def anayna_task(anayna_token):
    tasks = get_tasks(anayna_token)
    task = next((t for t in tasks if t.get("assignee") and "anayna" in (t["assignee"].get("email", "")).lower()), None)
    assert task, "No task assigned to Anayna found — check DB"
    return task

@pytest.fixture(scope="module")
def stephen_task(anayna_token):
    tasks = get_tasks(anayna_token)
    task = next((t for t in tasks if t.get("assignee") and "stephen" in (t["assignee"].get("email", "")).lower()), None)
    assert task, "No task assigned to Stephen found — check DB"
    return task

@pytest.fixture(scope="module")
def anayna_project(anayna_token):
    """A project owned by Anayna."""
    projects = get_projects(anayna_token)
    project = next((p for p in projects if p.get("owner") and "anayna" in (p["owner"].get("email", "")).lower()), None)
    assert project, "No project owned by Anayna found — check DB"
    return project

@pytest.fixture(scope="module")
def stephen_project(stephen_token):
    """A project owned by Stephen."""
    projects = get_projects(stephen_token)
    project = next((p for p in projects if p.get("owner") and "stephen" in (p["owner"].get("email", "")).lower()), None)
    assert project, "No project owned by Stephen found — check DB"
    return project


# ── 1. Authentication ─────────────────────────────────────────────────────────

class TestAuthentication:
    def test_no_token_rejected(self):
        r = CLIENT.get(f"{BASE}/tasks/")
        assert r.status_code == 401

    def test_invalid_token_rejected(self):
        r = CLIENT.get(f"{BASE}/tasks/", headers={"Authorization": "Bearer fake.token.here"})
        assert r.status_code == 401

    def test_valid_login_returns_token(self, anayna_token):
        assert len(anayna_token) > 50

    def test_unauthenticated_patch_task_rejected(self):
        r = CLIENT.patch(f"{BASE}/tasks/00000000-0000-0000-0000-000000000000", json={"status": "done"})
        assert r.status_code == 401

    def test_unauthenticated_patch_project_rejected(self):
        r = CLIENT.patch(f"{BASE}/projects/00000000-0000-0000-0000-000000000000", json={"status": "done"})
        assert r.status_code == 401

    def test_me_endpoint_returns_user(self, anayna_token):
        r = CLIENT.get(f"{BASE}/auth/me", headers=auth(anayna_token))
        assert r.status_code == 200
        data = r.json()
        assert "email" in data
        assert "anayna" in data["email"].lower()


# ── 2. Task CRUD ──────────────────────────────────────────────────────────────

class TestTaskCRUD:
    _created_task_id = None

    def test_list_tasks_returns_list(self, anayna_token):
        tasks = get_tasks(anayna_token)
        assert isinstance(tasks, list)

    def test_list_tasks_respects_project_filter(self, anayna_token, anayna_task):
        tasks = get_tasks(anayna_token, project_id=anayna_task["project_id"])
        assert all(t["project_id"] == anayna_task["project_id"] for t in tasks)

    def test_create_task(self, anayna_token, anayna_project):
        r = CLIENT.post(f"{BASE}/tasks/", json={
            "title": "_regression_test_task",
            "project_id": anayna_project["id"],
            "status": "todo",
            "priority": "low",
        }, headers=auth(anayna_token))
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["title"] == "_regression_test_task"
        TestTaskCRUD._created_task_id = data["id"]

    def test_patch_created_task(self, anayna_token):
        if not TestTaskCRUD._created_task_id:
            pytest.skip("create_task test did not run")
        r = patch_task(anayna_token, TestTaskCRUD._created_task_id, {"status": "in_progress"})
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

    def test_created_by_field_present(self, anayna_token):
        if not TestTaskCRUD._created_task_id:
            pytest.skip("create_task test did not run")
        r = CLIENT.get(f"{BASE}/tasks/", headers=auth(anayna_token))
        tasks = r.json()
        task = next((t for t in tasks if t["id"] == TestTaskCRUD._created_task_id), None)
        assert task is not None
        assert "created_by" in task

    def test_delete_created_task(self, anayna_token):
        if not TestTaskCRUD._created_task_id:
            pytest.skip("create_task test did not run")
        r = delete_task(anayna_token, TestTaskCRUD._created_task_id)
        assert r.status_code == 204


# ── 3. Task Ownership Guardrails ──────────────────────────────────────────────

class TestTaskOwnershipGuardrails:
    def test_can_edit_own_task(self, anayna_token, anayna_task):
        r = patch_task(anayna_token, anayna_task["id"], {"status": "in_progress"})
        assert r.status_code == 200, f"Should allow editing own task: {r.text}"
        patch_task(anayna_token, anayna_task["id"], {"status": anayna_task["status"]})

    def test_cannot_edit_others_task(self, anayna_token, stephen_task):
        r = patch_task(anayna_token, stephen_task["id"], {"status": "done"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_cannot_delete_others_task(self, anayna_token, stephen_task):
        r = delete_task(anayna_token, stephen_task["id"])
        assert r.status_code == 403

    def test_owner_can_edit_own_task(self, stephen_token, stephen_task):
        r = patch_task(stephen_token, stephen_task["id"], {"status": "in_progress"})
        assert r.status_code == 200
        patch_task(stephen_token, stephen_task["id"], {"status": stephen_task["status"]})

    def test_403_has_helpful_message(self, anayna_token, stephen_task):
        r = patch_task(anayna_token, stephen_task["id"], {"status": "done"})
        assert r.status_code == 403
        assert len(r.json().get("detail", "")) > 10


# ── 4. Privacy Guardrails ─────────────────────────────────────────────────────

class TestPrivacyGuardrails:
    def test_can_make_own_task_private(self, anayna_token, anayna_task):
        r = patch_task(anayna_token, anayna_task["id"], {"is_private": True})
        assert r.status_code == 200
        assert r.json()["is_private"] is True

    def test_private_task_hidden_from_others(self, anayna_token, stephen_token, anayna_task):
        patch_task(anayna_token, anayna_task["id"], {"is_private": True})
        stephen_tasks = get_tasks(stephen_token)
        assert anayna_task["id"] not in [t["id"] for t in stephen_tasks]

    def test_private_task_visible_to_owner(self, anayna_token, anayna_task):
        patch_task(anayna_token, anayna_task["id"], {"is_private": True})
        anayna_tasks = get_tasks(anayna_token)
        assert anayna_task["id"] in [t["id"] for t in anayna_tasks]

    def test_can_make_task_public_again(self, anayna_token, anayna_task):
        r = patch_task(anayna_token, anayna_task["id"], {"is_private": False})
        assert r.status_code == 200
        assert r.json()["is_private"] is False

    def test_cannot_make_others_task_private(self, anayna_token, stephen_task):
        r = patch_task(anayna_token, stephen_task["id"], {"is_private": True})
        assert r.status_code == 403


# ── 5. Project RBAC ───────────────────────────────────────────────────────────

class TestProjectRBAC:
    def test_anyone_can_read_projects(self, stephen_token):
        projects = get_projects(stephen_token)
        assert isinstance(projects, list)

    def test_owner_can_edit_own_project(self, anayna_token, anayna_project):
        original = anayna_project.get("next_action", "")
        r = patch_project(anayna_token, anayna_project["id"], {"next_action": "_regression_test"})
        assert r.status_code == 200
        patch_project(anayna_token, anayna_project["id"], {"next_action": original})

    def test_cannot_edit_others_project(self, anayna_token, stephen_project):
        r = patch_project(anayna_token, stephen_project["id"], {"next_action": "hacked"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_cannot_delete_others_project(self, anayna_token, stephen_project):
        r = delete_project(anayna_token, stephen_project["id"])
        assert r.status_code == 403

    def test_403_message_present(self, anayna_token, stephen_project):
        r = patch_project(anayna_token, stephen_project["id"], {"next_action": "x"})
        assert r.status_code == 403
        assert len(r.json().get("detail", "")) > 10


# ── 6. Progress Auto-Calculation ─────────────────────────────────────────────

class TestProgressAutoCalc:
    def test_progress_updates_on_task_completion(self, anayna_token, anayna_task):
        projects_before = get_projects(anayna_token)
        proj = next((p for p in projects_before if p["id"] == anayna_task["project_id"]), None)
        assert proj, "Project not found"
        before = proj["progress_pct"]

        patch_task(anayna_token, anayna_task["id"], {"is_completed": True})

        projects_after = get_projects(anayna_token)
        proj_after = next((p for p in projects_after if p["id"] == anayna_task["project_id"]), None)
        assert proj_after["progress_pct"] >= before

        patch_task(anayna_token, anayna_task["id"], {"is_completed": False, "status": "todo"})


# ── 7. AI Chatbot ─────────────────────────────────────────────────────────────

class TestChatbot:
    def test_off_topic_refused(self, anayna_token):
        r = CLIENT.post(f"{BASE}/ai/chat", json={"message": "What is the capital of France?"}, headers=auth(anayna_token))
        assert r.status_code == 200
        assert "reply" in r.json()
        # Should decline off-topic, not hallucinate an answer
        reply = r.json()["reply"].lower()
        assert any(w in reply for w in ["focused", "project", "task", "can't", "cant", "here"]), \
            f"Expected refusal, got: {reply}"

    def test_query_intent_returns_reply(self, anayna_token):
        r = CLIENT.post(f"{BASE}/ai/chat", json={"message": "What projects are blocked?"}, headers=auth(anayna_token))
        assert r.status_code == 200
        data = r.json()
        assert "reply" in data
        assert len(data["reply"]) > 10

    def test_chat_with_history(self, anayna_token):
        history = [
            {"role": "user", "content": "What projects are overdue?"},
            {"role": "assistant", "content": "There are 3 overdue projects."},
        ]
        r = CLIENT.post(f"{BASE}/ai/chat", json={
            "message": "Which one is the most urgent?",
            "history": history,
        }, headers=auth(anayna_token))
        assert r.status_code == 200
        assert "reply" in r.json()

    def test_unauthenticated_chat_rejected(self):
        r = CLIENT.post(f"{BASE}/ai/chat", json={"message": "hello"})
        assert r.status_code == 401


# ── 8. MCP Tools (skipped — protocol mismatch) ───────────────────────────────

@pytest.mark.skip(
    reason=(
        "MCP tool calls return -32602 (Invalid request parameters). "
        "Root cause: Railway is running mcp>=1.0.0 which resolved to 1.27.2 "
        "(protocol 2025-11-25) while Claude Code 2.1.163 sends protocol 2024-11-05. "
        "Fix deployed in requirements.txt (mcp==1.6.0) — pending Railway redeploy. "
        "Re-enable these tests once /health returns mcp_version: 1.6.0."
    )
)
class TestMCPTools:
    def test_list_my_tasks_via_mcp(self):
        pass

    def test_create_task_via_mcp(self):
        pass

    def test_complete_task_via_mcp(self):
        pass


# ── 9. AI Intake confirm — project/task routing (Option C) ───────────────────
#
# These tests exercise the confirm endpoint deterministically by seeding
# `pending` RequestIntake rows DIRECTLY in the DB (no live AI call), so subtask
# count / item_type / status are fixed. Seeded intakes and any projects they
# create are cleaned up in the fixture teardown so repeated runs stay isolated
# and "no spurious project" assertions do not go flaky.

def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


async def _seed_intake_async(item_type, subtasks, title):
    from app.db.session import AsyncSessionLocal
    from app.models.models import RequestIntake, IntakeStatus, PriorityLevel
    intake_id = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        db.add(RequestIntake(
            id=intake_id,
            raw_input="seeded for regression test",
            generated_title=title,
            generated_description="seeded description",
            project_type="test",
            suggested_item_type=item_type,   # may be None to simulate a legacy row
            suggested_tags=["regression"],
            suggested_subtasks=subtasks,
            suggested_next_steps=["first step"],
            suggested_priority=PriorityLevel.medium,
            suggested_owners=[],
            intake_status=IntakeStatus.pending,
        ))
        await db.commit()
    return str(intake_id)


async def _cleanup_async(intake_ids):
    from sqlalchemy import select, delete
    from app.db.session import AsyncSessionLocal
    from app.models.models import RequestIntake, Project
    async with AsyncSessionLocal() as db:
        for iid in intake_ids:
            res = await db.execute(select(RequestIntake).where(RequestIntake.id == uuid.UUID(iid)))
            intake = res.scalar_one_or_none()
            if intake and intake.project_id:
                # Deleting the project cascades to its tasks (ondelete=CASCADE).
                await db.execute(delete(Project).where(Project.id == intake.project_id))
            await db.execute(delete(RequestIntake).where(RequestIntake.id == uuid.UUID(iid)))
        await db.commit()


@pytest.fixture
def intake_factory():
    """Yields a factory for seeded pending intakes; cleans them up afterwards."""
    created = []

    def make(item_type="project", subtasks=None, title=None):
        if subtasks is None:
            subtasks = ["Subtask one", "Subtask two"]
        title = title or f"_reg_intake_{uuid.uuid4().hex[:8]}"
        iid = _run(_seed_intake_async(item_type, subtasks, title))
        created.append(iid)
        return iid, title

    yield make
    _run(_cleanup_async(created))


def confirm_intake(token, intake_id, body):
    return CLIENT.post(f"{BASE}/ai/intake/{intake_id}/confirm", json=body, headers=auth(token))


class TestIntakeConfirm:
    def test_project_route_creates_project_and_subtasks(self, anayna_token, intake_factory):
        iid, title = intake_factory(item_type="project", subtasks=["A", "B", "C"])
        r = confirm_intake(anayna_token, iid, {"confirmed_priority": "high", "item_type": "project"})
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["item_type"] == "project"
        assert data["project"]["title"] == title
        assert data["project"]["status"] == "intake"
        assert data["tasks_created"] == 3
        assert {t["title"] for t in data["tasks"]} == {"A", "B", "C"}
        assert all(t["project_id"] == data["project"]["id"] for t in data["tasks"])

    def test_project_route_empty_subtasks_creates_zero_tasks(self, anayna_token, intake_factory):
        iid, _ = intake_factory(item_type="project", subtasks=[])
        r = confirm_intake(anayna_token, iid, {"confirmed_priority": "low", "item_type": "project"})
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["item_type"] == "project"
        assert data["tasks_created"] == 0
        assert data["tasks"] == []

    def test_task_to_new_project(self, anayna_token, intake_factory):
        iid, _ = intake_factory(item_type="task", subtasks=["Do the thing"])
        r = confirm_intake(anayna_token, iid, {
            "confirmed_priority": "medium",
            "item_type": "task",
            "new_project_title": "_reg_new_parent",
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["item_type"] == "task"
        assert data["project"]["title"] == "_reg_new_parent"
        assert data["tasks_created"] == 1
        assert data["tasks"][0]["title"] == "Do the thing"

    def test_task_to_new_project_empty_subtasks_creates_single_task(self, anayna_token, intake_factory):
        iid, title = intake_factory(item_type="task", subtasks=[])
        r = confirm_intake(anayna_token, iid, {
            "confirmed_priority": "medium",
            "item_type": "task",
            "new_project_title": "_reg_new_parent2",
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["tasks_created"] == 1
        # single task falls back to the generated title
        assert data["tasks"][0]["title"] == title

    def test_task_to_existing_project(self, anayna_token, anayna_project, intake_factory):
        iid, _ = intake_factory(item_type="task", subtasks=["X", "Y"])
        r = confirm_intake(anayna_token, iid, {
            "confirmed_priority": "medium",
            "item_type": "task",
            "target_project_id": anayna_project["id"],
        })
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["item_type"] == "task"
        assert data["project"]["id"] == anayna_project["id"]   # no spurious new project
        assert data["tasks_created"] == 2
        assert all(t["project_id"] == anayna_project["id"] for t in data["tasks"])

    def test_user_override_wins_over_ai_classification(self, anayna_token, intake_factory):
        # AI said "project"; user overrides to "task" → routed as task.
        iid, _ = intake_factory(item_type="project", subtasks=["only one"])
        r = confirm_intake(anayna_token, iid, {
            "confirmed_priority": "medium",
            "item_type": "task",
            "new_project_title": "_reg_override_parent",
        })
        assert r.status_code == 201, r.text
        assert r.json()["item_type"] == "task"

    def test_legacy_null_classification_defaults_to_project(self, anayna_token, intake_factory):
        # Row created before the column existed (None) + no override → project.
        iid, _ = intake_factory(item_type=None, subtasks=["Z"])
        r = confirm_intake(anayna_token, iid, {"confirmed_priority": "medium"})
        assert r.status_code == 201, r.text
        assert r.json()["item_type"] == "project"

    def test_missing_target_project_returns_404(self, anayna_token, intake_factory):
        iid, _ = intake_factory(item_type="task", subtasks=["t"])
        r = confirm_intake(anayna_token, iid, {
            "confirmed_priority": "medium",
            "item_type": "task",
            "target_project_id": "00000000-0000-0000-0000-000000000000",
        })
        assert r.status_code == 404, r.text

    def test_unauthorized_target_project_returns_403(self, anayna_token, stephen_project, intake_factory):
        # Anayna cannot add tasks to Stephen's project.
        iid, _ = intake_factory(item_type="task", subtasks=["t"])
        r = confirm_intake(anayna_token, iid, {
            "confirmed_priority": "medium",
            "item_type": "task",
            "target_project_id": stephen_project["id"],
        })
        assert r.status_code == 403, r.text

    def test_already_confirmed_returns_409(self, anayna_token, intake_factory):
        iid, _ = intake_factory(item_type="project", subtasks=["A"])
        r1 = confirm_intake(anayna_token, iid, {"confirmed_priority": "medium", "item_type": "project"})
        assert r1.status_code == 201, r1.text
        r2 = confirm_intake(anayna_token, iid, {"confirmed_priority": "medium", "item_type": "project"})
        assert r2.status_code == 409, r2.text

    def test_confirmed_priority_required(self, anayna_token, intake_factory):
        iid, _ = intake_factory(item_type="project", subtasks=["A"])
        r = confirm_intake(anayna_token, iid, {"item_type": "project"})
        assert r.status_code == 422, r.text

    def test_unauthenticated_confirm_rejected(self, intake_factory):
        iid, _ = intake_factory(item_type="project", subtasks=["A"])
        r = CLIENT.post(f"{BASE}/ai/intake/{iid}/confirm", json={"confirmed_priority": "medium"})
        assert r.status_code == 401
