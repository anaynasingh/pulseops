# AIGILE_STATUS.md

The "where are we right now" index. Thin by design. Plan content lives in `AIGILE_PLAN/`; closed-burst history in `AIGILE_HISTORY.md`; lessons in `AIGILE_CORRECTIONS.md`.

## Current state

**Phase:** Building
**Active burst:** hourly-reminders
**Burst base:** b0dd158eba8a6155881fcc21b6dfd592e20a0469
**Plan reference:** AIGILE_PLAN/current/
**Next action:** Build: Stream A (notifications foundation), then Stream B (Railway Cron + reminder service) + Stream C (frontend bell) in parallel
**Last updated:** 2026-06-04

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

**Stream notifications-foundation builders:** claude
**Stream notifications-foundation handoff head:** None
**Stream notifications-foundation status:** IN PROGRESS

**Stream railway-cron builders:** claude
**Stream railway-cron handoff head:** None
**Stream railway-cron status:** WAITING ON A

**Stream frontend-bell builders:** claude
**Stream frontend-bell handoff head:** None
**Stream frontend-bell status:** WAITING ON A

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
