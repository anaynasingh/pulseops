# AIGILE_STATUS.md

The "where are we right now" index. Thin by design. Plan content lives in `AIGILE_PLAN/`; closed-burst history in `AIGILE_HISTORY.md`; lessons in `AIGILE_CORRECTIONS.md`.

## Current state

**Phase:** Idle
**Active burst:** None
**Burst base:** None
**Plan reference:** None
**Next action:** PR #41 (dev -> P33 master, transcript-intake-bell + live-hardening fixes) awaiting Gemini review; merge after disposition, then verify prod deploy.
**Last updated:** 2026-07-23 (dev-only ship; burst archived to closed/2026-07-23-transcript-intake-bell-52c42f2; manifest finalised)

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

<!-- No active streams. Last burst's stream blocks archived in closed/2026-07-23-transcript-intake-bell-52c42f2/ and the burst manifest. -->


## Gemini Reviews

<!-- Populated by /ag-ship when a dev->main PR is opened. -->
<!-- Two states: WAITING_REVIEW (not yet reviewed) and WAITING_RESPONSE (reviewed, findings pending). -->
<!-- Cleared when Orchestrator records a disposition (fix/defer/skip). -->
<!-- Format:
     **PR #N:** WAITING_REVIEW | opened <ISO> | retries: 0
     **PR #N:** WAITING_RESPONSE | reviewed <ISO> | reviewed_sha: <sha> | findings: HIGH: x, MEDIUM: y
     On disposition: remove entry; record outcome in HISTORY as **Gemini:** <outcome> -->

**PR #41:** WAITING_REVIEW | opened 2026-07-24T08:55:00Z | retries: 0

<!-- PR #16 shipped 2026-07-06: merged to P33-AI master (528214e). Gemini: R1 model_dump default-clobber fixed (f2c2939); R2 omit-vs-null ruled intentional (never-unassigned invariant), replied + resolved. -->


## Deferred Reviews

<!-- Populated by /ag-plan when you defer a code review item. -->
<!-- Cleared by /ag-probe steer checkpoint when addressed or explicitly dismissed. -->
<!-- Format: - PR #N: [comment summary] — deferred [date] -->

- Codex adversarial-review: review-mqunqa66-vawfmc (status: resolved — C1 race + C2 test-pollution fixed, 2026-06-26)
- Codex adversarial-review: review-mquo3tdl-a0821i (status: resolved — C1/C2 confirmed fixed; C3 progress_pct deferred to DEFERRED.md, 2026-06-26)
- Codex adversarial-review: thread 019f0358-27f9-7c70-a84b-947909a94919 (intake-default-assignee, base 33f8c43; status: resolved — verdict APPROVE, no material findings, 2026-06-26)
- Codex adversarial-review: guide-modal-center (base ec8a597, branch mode; status: resolved — R1 set-state-in-effect lint error FIXED via render-time guard; R2 process-artefact finding re untracked AIGILE_PLAN/current accepted as known AI-gile resume-in-worktree architecture, not a deliverable defect; steer=SHIP, 2026-06-26)
- Peer adversarial review: transcript-intake-bell (base 52c42f2; reviewer: peer via ag-review; verdict: 3 findings, no Critical; status: resolved 2026-07-23 — 2 findings fixed and committed, TLS verify=False finding deferred to Orchestrator as repo-wide posture; details in AIGILE_PLAN/closed/2026-07-23-transcript-intake-bell-52c42f2/review.md)
- Codex adversarial-review: mcp-longlived-apikey (base b936411; status: SKIPPED — review hung twice at context-gathering (review-mr96bcna-u8k6ut, review-mr99fvw0-mdu6t7), never produced a verdict; both cancelled. Per Orchestrator steer, verification rests on the COMPLETED adversarial passes: Codex plan-challenge round 0 (6 findings absorbed + build-verified) + ag-challenge --build opus/Prosecution PASS_CLEAN (line-by-line diff review, 0 findings). 2026-07-06)
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

- [2026-06-26] guide-modal-center — Claude setup "guide" modal now centers on viewport (createPortal to document.body, escaping the transformed sidebar containing block). PASS (build+tsc+eslint clean; Codex R1 lint error fixed, R2 process-artefact finding accepted as known-architecture). Steer=SHIP.
- [2026-07-06] assignable-users-sso — GET /users/ now returns all logged-in users (or_(ms_oid, password_hash)), not just 3 password-seeded accounts; SSO users were excluded by password_hash-only filter. PASS (SQL compile + root-cause; ag-challenge PASS_CLEAN). Steer=SHIP, Codex skipped (2-line validated fix, noisy base range).
- [2026-07-06] mcp-longlived-apikey — get_current_user accepts permanent User.api_key as bearer (non-JWT tokens); local pulseops MCP server uses PULSEOPS_API_KEY instead of email/password→JWT (connect once, no re-auth; also unblocks SSO users who had no password). PASS (static+3 adversarial passes; live TestApiKeyAuth deferred to deploy). Steer=SHIP; Codex code-review skipped (hung x2), covered by plan-challenge + build-challenge PASS_CLEAN.
- [2026-07-22] claude-bridge-live — bridge service hardened + deployed to Railway from prep/claude-bridge-harden (env binding, m365 MCP wiring, Dockerfile, runbook). Closed by Orchestrator steer, probe waived (recorded exception): bridge verified working live by Orchestrator. Archived to closed/2026-07-08-claude-bridge-live-bb3c8d2/.
- [2026-07-23] transcript-intake-bell — Graph transcript poll (per-user delegated tokens) -> GPT-4o action-item extraction -> per-user proposed-tasks bell with explicit-lists confirm + pre-add dedup; un-dormed internal router; RLS-safe shared progress recalc. PASS (pytest 37/37 new + vitest 7/7; ag-challenge PASS_CLEAN; peer review 2 fixed/1 deferred). Steer=SHIP (4 rulings in DEFERRED.md). Shipped DEV ONLY per round_ship redirect; prod promotion pending dev-server verification.
