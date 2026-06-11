"""
Guardrail tests — verifies security rules are enforced at the API level.
Run against the live local backend: pytest tests/test_guardrails.py -v
"""
import pytest
import httpx

BASE = "http://localhost:8001/api/v1"
# Supabase is in Sydney — allow 30s per request
CLIENT = httpx.Client(timeout=30.0)


def login(email, password):
    r = CLIENT.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.text}"
    return r.json()["access_token"]

def auth(token):
    return {"Authorization": f"Bearer {token}"}

def get_tasks(token):
    r = CLIENT.get(f"{BASE}/tasks/", headers=auth(token))
    assert r.status_code == 200
    return r.json()

def get_projects(token):
    r = CLIENT.get(f"{BASE}/projects/", headers=auth(token))
    assert r.status_code == 200
    return r.json()

def patch_task(token, task_id, data):
    return CLIENT.patch(f"{BASE}/tasks/{task_id}", json=data, headers=auth(token))

def delete_task(token, task_id):
    return CLIENT.delete(f"{BASE}/tasks/{task_id}", headers=auth(token))


@pytest.fixture(scope="module")
def anayna_token():
    return login("anayna.singh@prospect33.com", "PulseOps2026!")

@pytest.fixture(scope="module")
def stephen_token():
    return login("stephen.kamau@prospect33.com", "StephenP33!2026")

@pytest.fixture(scope="module")
def anayna_task(anayna_token):
    tasks = get_tasks(anayna_token)
    task = next((t for t in tasks if t.get("assignee") and "anayna" in (t["assignee"].get("email","")).lower()), None)
    assert task, "No task assigned to Anayna found — check DB"
    return task

@pytest.fixture(scope="module")
def stephen_task(anayna_token):
    tasks = get_tasks(anayna_token)
    task = next((t for t in tasks if t.get("assignee") and "stephen" in (t["assignee"].get("email","")).lower()), None)
    assert task, "No task assigned to Stephen found — check DB"
    return task


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

    def test_unauthenticated_patch_rejected(self):
        r = CLIENT.patch(f"{BASE}/tasks/00000000-0000-0000-0000-000000000000", json={"status": "done"})
        assert r.status_code == 401


# ── 2. Task Ownership Guardrails ──────────────────────────────────────────────

class TestOwnershipGuardrails:
    def test_can_edit_own_task(self, anayna_token, anayna_task):
        r = patch_task(anayna_token, anayna_task["id"], {"status": "in_progress"})
        assert r.status_code == 200, f"Should allow editing own task: {r.text}"
        patch_task(anayna_token, anayna_task["id"], {"status": anayna_task["status"]})

    def test_cannot_edit_others_task(self, anayna_token, stephen_task):
        r = patch_task(anayna_token, stephen_task["id"], {"status": "done"})
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    def test_cannot_delete_others_task(self, anayna_token, stephen_task):
        r = delete_task(anayna_token, stephen_task["id"])
        assert r.status_code == 403, f"Expected 403, got {r.status_code}"

    def test_owner_can_edit_own_task(self, stephen_token, stephen_task):
        r = patch_task(stephen_token, stephen_task["id"], {"status": "in_progress"})
        assert r.status_code == 200, f"Stephen should edit his own task: {r.text}"
        patch_task(stephen_token, stephen_task["id"], {"status": stephen_task["status"]})

    def test_403_has_helpful_message(self, anayna_token, stephen_task):
        r = patch_task(anayna_token, stephen_task["id"], {"status": "done"})
        assert r.status_code == 403
        assert "detail" in r.json()
        assert len(r.json()["detail"]) > 10


# ── 3. Privacy Guardrails ─────────────────────────────────────────────────────

class TestPrivacyGuardrails:
    def test_can_make_own_task_private(self, anayna_token, anayna_task):
        r = patch_task(anayna_token, anayna_task["id"], {"is_private": True})
        assert r.status_code == 200
        assert r.json()["is_private"] is True

    def test_private_task_hidden_from_others(self, anayna_token, stephen_token, anayna_task):
        patch_task(anayna_token, anayna_task["id"], {"is_private": True})
        stephen_tasks = get_tasks(stephen_token)
        assert anayna_task["id"] not in [t["id"] for t in stephen_tasks], \
            "Private task must not appear in another user's task list"

    def test_private_task_visible_to_owner(self, anayna_token, anayna_task):
        patch_task(anayna_token, anayna_task["id"], {"is_private": True})
        anayna_tasks = get_tasks(anayna_token)
        assert anayna_task["id"] in [t["id"] for t in anayna_tasks], \
            "Owner must still see their own private task"

    def test_can_make_task_public_again(self, anayna_token, anayna_task):
        r = patch_task(anayna_token, anayna_task["id"], {"is_private": False})
        assert r.status_code == 200
        assert r.json()["is_private"] is False

    def test_cannot_make_others_task_private(self, anayna_token, stephen_task):
        r = patch_task(anayna_token, stephen_task["id"], {"is_private": True})
        assert r.status_code == 403


# ── 4. Progress Auto-Calculation ──────────────────────────────────────────────

class TestProgressAutoCalc:
    def test_progress_updates_on_task_completion(self, anayna_token, anayna_task):
        projects_before = get_projects(anayna_token)
        proj = next((p for p in projects_before if p["id"] == anayna_task["project_id"]), None)
        assert proj, "Project not found"
        before = proj["progress_pct"]

        patch_task(anayna_token, anayna_task["id"], {"is_completed": True})

        projects_after = get_projects(anayna_token)
        proj_after = next((p for p in projects_after if p["id"] == anayna_task["project_id"]), None)
        assert proj_after["progress_pct"] >= before, "Progress should not decrease after completion"

        # Restore
        patch_task(anayna_token, anayna_task["id"], {"is_completed": False, "status": "todo"})
