# AIGILE_STATUS.md

The "where are we right now" index. Thin by design. Plan content lives in `AIGILE_PLAN/`; closed-burst history in `AIGILE_HISTORY.md`; lessons in `AIGILE_CORRECTIONS.md`.

## Current state

**Phase:** Building
**Active burst:** intake-functional
**Burst base:** 7dae53f2de15f721913344c3df07b66bd295ddaf
**Plan reference:** AIGILE_PLAN/current/
**Next action:** Build: Stream A (backend — classification Literal + migration + 8-case confirm_intake router under require_writer + Task creation + activity + cache-bust + ConfirmIntakeResult + seeded tests on 8001) and Stream B (frontend — item-type toggle + project picker + dynamic button + query-key invalidation fix). Build notes: N1 default-for-missing item_type, N2 use "task_created" action, N3 test cleanup/isolation, N4 picker loading state.
**Last updated:** 2026-06-26

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

**Stream A (backend) builders:** claude
**Stream A (backend) handoff head:** b4b0afc
**Stream A (backend) status:** DONE — built, awaiting probe

**Stream B (frontend) builders:** claude
**Stream B (frontend) handoff head:** b4b0afc
**Stream B (frontend) status:** DONE — built, awaiting probe

## Gemini Reviews

<!-- Populated by /ag-ship when a dev->main PR is opened. -->
<!-- Two states: WAITING_REVIEW (not yet reviewed) and WAITING_RESPONSE (reviewed, findings pending). -->
<!-- Cleared when Orchestrator records a disposition (fix/defer/skip). -->
<!-- Format:
     **PR #N:** WAITING_REVIEW | opened <ISO> | retries: 0
     **PR #N:** WAITING_RESPONSE | reviewed <ISO> | reviewed_sha: <sha> | findings: HIGH: x, MEDIUM: y
     On disposition: remove entry; record outcome in HISTORY as **Gemini:** <outcome> -->

## Deferred Reviews

<!-- Populated by /ag-plan when you defer a code review item. -->
<!-- Cleared by /ag-probe steer checkpoint when addressed or explicitly dismissed. -->
<!-- Format: - PR #N: [comment summary] — deferred [date] -->

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

- [2026-06-25] dashboard-complete-gap — task-completion layout gap fix (AnimatePresence reflow + 300ms check beat). PASS. Shipped prod b67f6dd (PR #2).
- [2026-06-25] focus-reminder-toggle — sidebar toggle knob containment + "Test"→"Preview" + a11y. PASS. Shipped prod f617541 (PR #3).
- [2026-06-25] reminder-modal — "Focus Check" title + prefetch/skeleton (no empty flash). PASS. Shipped prod 7180bed (PR #4).
- [2026-06-25] remove-my-tasks — dropped redundant dashboard My Tasks list + deleted component. PASS. Shipped prod db4bacd (PR #5).
- [2026-06-25] assistant-task-prompts — task-focused AI quick prompts + per-user task context in /ai/chat. PASS (probe: 2 Codex HIGH fixed; ship Gemini: week-window + style). Shipped prod 2812192 (PR #6).
