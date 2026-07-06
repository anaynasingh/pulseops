# Iteration log: assignable-users-sso

## Round 0 (reconciled 2026-07-06)

**Origin:** Fix built and committed ad hoc (381af90) in a prior session before STATUS
was advanced. No /ag-plan pipeline was run; reconciled into probe on 2026-07-06.

**Build:** `backend/app/api/v1/users.py` — replace `User.password_hash.isnot(None)`
with `or_(User.ms_oid.isnot(None), User.password_hash.isnot(None))` so SSO users
(ms_oid set, password_hash NULL) become assignable. Active + @prospect33.com guards kept.

**Verify (2026-07-06):** PASS.
- SQL compilation: `WHERE is_active = true AND (ms_oid IS NOT NULL OR password_hash IS NOT NULL) AND email LIKE '%prospect33.com%' ORDER BY name` — correct.
- Root cause confirmed: auth.py:99 creates SSO users with ms_oid, no password_hash.
- Placeholder exclusion confirmed: user_service.py:20 uses @pulseops.internal (fails domain guard).
- Integration suite not runnable (no live backend/DB/.env in this environment).
- Frontend: 0 files changed. Ambiguities: none. Scope: users.py only.

**ag-challenge (Opus, prosecution, round 1):** PASS_CLEAN. No defects introduced.
- Low (out of scope, pre-existing): `LIKE "%prospect33.com%"` is unanchored substring match.
- Info: placeholder exclusion enforced by two partially-redundant guards.

**Codex adversarial review:** SKIPPED by steer decision. Rationale: 2-line validated fix
already passed one adversarial pass (PASS_CLEAN); base..HEAD range is ~85% noise
(merged origin/master feature already reviewed via master PR #1, plus ag-init v10.6.0
governance upgrade). Codex review gate also disabled.

**Steer decision (2026-07-06):** SHIP — skip Codex, proceed to retrospective + /ag-ship.

## Ship round (2026-07-06) — Gemini finding on PR #16

PR #16 scope expanded to "ship all four" (SSO fix + auto-assign feature + ag-init v10.6.0 + retro docs)
per Orchestrator decision. Gemini re-review at head 76e6714 raised one MEDIUM finding in the
auto-assign feature code (not the SSO fix):

**MEDIUM — tasks.py:106 (create_task):** `data = payload.model_dump()` passes `duration_minutes=None`
for omitted field, overriding the SQLAlchemy column default (60) → NULL in DB. Fix: `model_dump(exclude_unset=True)`
plus `"assigned_to" not in data or data["assigned_to"] is None` guard (preserves never-unassigned for both
omit and explicit-null). Applied per Gemini's exact suggestion. Confirmed omit-vs-null contract (CLAUDE.md).

**Class-fix scan:** sibling `projects.py:164` uses same `model_dump()`→constructor pattern but is NOT
affected — Project columns with defaults (progress_pct/health_score/kanban_order) are absent from
ProjectCreate; tags/stakeholders schema-default to [] matching column defaults. No change needed there.

Authorised scope: tasks.py:106-110 only. Single-file, unambiguous per Gemini suggestion — light preservation gate.
