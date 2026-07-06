# AIGILE_STATUS.md

The "where are we right now" index. Thin by design. Plan content lives in `AIGILE_PLAN/`; closed-burst history in `AIGILE_HISTORY.md`; lessons in `AIGILE_CORRECTIONS.md`.

## Current state

**Phase:** Idle
**Active burst:** None
**Burst base:** None
**Next action:** Burst complete - /clear when ready, next session runs /ag-plan.
**Last updated:** 2026-07-06 (assignable-users-sso shipped to P33-AI master via PR #16, merge 528214e; prod deploy triggered)

<!-- Next action is the forward pointer for resume-on-/clear. Every phase  -->
<!-- transition updates it. A new session reads this field via             -->
<!-- `ag-status --quiet` and picks up exactly where we left off. Must  -->
<!-- be accurate before any /clear - stale pointers are worse than none.   -->
<!--                                                                       -->
<!-- Plan reference points at AIGILE_PLAN/current/ when a burst is active. -->
<!-- The plan content itself is NOT copied here - AIGILE_PLAN/ is the      -->
<!-- canonical home; STATUS is just the index.                             -->
<!--                                                                       -->
<!-- Burst base is the SHA of HEAD captured at /ag-plan approval - the     -->
<!-- parent of the burst's first commit. /ag-probe reads it and passes     -->
<!-- `--base <sha>` to `codex-review adversarial-review` so the review     -->
<!-- sees only burst-scope changes.                                        -->
<!--                                                                       -->
<!-- Codex steps: NEVER write `Invoke /codex:<cmd> ...` in Next action.    -->
<!-- The next assistant will Skill-route it and hit the harness bug.       -->
<!-- Write the Bash form `Run codex-review <subcmd> ... with brief at      -->
<!-- <path>`. For rescue pointers, include --resume or --fresh explicitly  -->
<!-- when an in-session rescue thread may already exist. See AIGILE_RULES  -->
<!-- ### Codex invocation for the full rule.                               -->

## Active streams

**Stream assignable-users-sso builders:** claude
**Stream assignable-users-sso handoff head:** None
**Stream assignable-users-sso status:** COMPLETE (steer: SHIP 2026-07-06)

## Gemini Reviews

<!-- Populated by /ag-ship when a dev->main PR is opened. -->
<!-- Two states: WAITING_REVIEW (not yet reviewed) and WAITING_RESPONSE (reviewed, findings pending). -->
<!-- Cleared when Orchestrator records a disposition (fix/defer/skip). -->
<!-- Format:
     **PR #N:** WAITING_REVIEW | opened <ISO> | retries: 0
     **PR #N:** WAITING_RESPONSE | reviewed <ISO> | reviewed_sha: <sha> | findings: HIGH: x, MEDIUM: y
     On disposition: remove entry; record outcome in HISTORY as **Gemini:** <outcome> -->

<!-- PR #16 shipped 2026-07-06: merged to P33-AI master (528214e). Gemini: R1 model_dump default-clobber fixed (f2c2939); R2 omit-vs-null ruled intentional (never-unassigned invariant), replied + resolved. -->


## Deferred Reviews

<!-- Populated by /ag-plan when you defer a code review item. -->
<!-- Cleared by /ag-probe steer checkpoint when addressed or explicitly dismissed. -->
<!-- Format: - PR #N: [comment summary] — deferred [date] -->

- Codex adversarial-review: review-mqunqa66-vawfmc (status: resolved — C1 race + C2 test-pollution fixed, 2026-06-26)
- Codex adversarial-review: review-mquo3tdl-a0821i (status: resolved — C1/C2 confirmed fixed; C3 progress_pct deferred to DEFERRED.md, 2026-06-26)
- Codex adversarial-review: thread 019f0358-27f9-7c70-a84b-947909a94919 (intake-default-assignee, base 33f8c43; status: resolved — verdict APPROVE, no material findings, 2026-06-26)
- Codex adversarial-review: guide-modal-center (base ec8a597, branch mode; status: resolved — R1 set-state-in-effect lint error FIXED via render-time guard; R2 process-artefact finding re untracked AIGILE_PLAN/current accepted as known AI-gile resume-in-worktree architecture, not a deliverable defect; steer=SHIP, 2026-06-26)
## Session Checkpoint

<!-- Written by /ag-compact before context compaction. -->
<!-- Read on resume to re-orient. -->
<!--                                                                       -->
<!-- Mostly superseded by AIGILE_PLAN/current/iteration.md within an       -->
<!-- active burst. Kept for compact-time session orientation hints that    -->
<!-- don't belong in plan iteration.                                       -->

## History

<!-- Append completed Bursts. Keep last 5 entries. Full archive in AIGILE_HISTORY.md. -->
<!-- Long-term burst sequence lives in AIGILE_PLAN/long-term/sequence.md. -->

- [2026-06-25] assistant-task-prompts — task-focused AI quick prompts + per-user task context in /ai/chat. PASS (probe: 2 Codex HIGH fixed; ship Gemini: week-window + style). Shipped prod 2812192 (PR #6).
- [2026-06-26] intake-functional — AI intake routes to project/task (user override + parent picker); confirm creates real Task rows, logs activity, busts kanban cache; fixed board-never-refreshes query-key bug. PASS (static+Codex; live deferred to prod deploy. Codex: C1 race + C2 test fixed, C3 progress_pct deferred; Gemini: 1 MEDIUM fixed). Shipped prod 63a8b48 (PR #8).
- [2026-06-26] intake-default-assignee — intake confirm defaults new project owner_id + created task assigned_to to the confirming user (model_fields_set omit-vs-null; explicit override/null preserved; Route 2 existing owner untouched). PASS (static + Codex APPROVE 0 findings; live 24-test suite + API deferred to deploy per steer).
- [2026-06-26] guide-modal-center — Claude setup "guide" modal now centers on viewport (createPortal to document.body, escaping the transformed sidebar containing block). PASS (build+tsc+eslint clean; Codex R1 lint error fixed, R2 process-artefact finding accepted as known-architecture). Steer=SHIP.
- [2026-07-06] assignable-users-sso — GET /users/ now returns all logged-in users (or_(ms_oid, password_hash)), not just 3 password-seeded accounts; SSO users were excluded by password_hash-only filter. PASS (SQL compile + root-cause; ag-challenge PASS_CLEAN). Steer=SHIP, Codex skipped (2-line validated fix, noisy base range).
