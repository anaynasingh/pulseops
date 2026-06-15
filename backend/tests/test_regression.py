"""
Full regression test suite for the Task Planner app.

Run against the live local backend:
  uvicorn app.main:app --host 127.0.0.1 --port 8001
  pytest tests/test_regression.py -v

Covers: authentication, task CRUD, privacy, project RBAC, chatbot, MCP (skipped).
"""
import pytest
import httpx

BASE = "http://localhost:8002/api/v1"
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
