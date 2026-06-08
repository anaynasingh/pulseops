# AIGILE_PLAN/

The "how do we get from where we are to where we want to be" artefact.

Peer of `AIGILE_CHARTER.md` (vision), `AIGILE_STATUS.md` (now), `AIGILE_HISTORY.md` (past), `AIGILE_CORRECTIONS.md` (lessons).

## Layout

```
AIGILE_PLAN/
├── README.md                              this file
├── long-term/
│   ├── sequence.md                        the burst sequence (B1..Bn) mapped to CHARTER objectives
│   └── revisions.md                       append-only log of sequence reorderings, each with trigger
├── current/                               the active burst's working store (empty when Phase=Idle)
│   ├── plan.md                            mirror of the latest round's plan
│   ├── iteration.md                       round-by-round summary
│   ├── feedback.md                        HAV: chronological log of Orchestrator redirects during the burst (eagerly created at /ag-plan Step 1 with empty-state header)
│   ├── feedback-review.md                 HAV: Codex `task` review of feedback.md, written at /ag-probe retrospective Step 4 (eagerly created at Step 1 with placeholder, overwritten at probe)
│   └── round_<N>/                         one per planning round
│       ├── plan.md                        the plan as it stood at round N — the anchor for round N+1
│       ├── codex.md                       Codex critique verbatim
│       ├── gemini.md                      (when run; rare at plan time, common at probe)
│       ├── determination.md               per-finding reasoning: absorb / reject / defer + why
│       ├── change-request.md              authoritative whitelist of what round N+1 may change
│       └── preservation-check.md          diff of round_N+1 plan vs round_N plan, fails if changes
│                                           are outside change-request.md
└── closed/<date>-<burst-label>-<shortsha>/   one per shipped burst, migrated from current/ at /ag-ship
    └── (same shape as current/, frozen)
```

## Rules

1. **Plan iteration is file-anchored.** Each round's Plan-agent spawn reads `round_<N>/plan.md`, `round_<N>/codex.md`, `round_<N>/determination.md`, and `round_<N>/change-request.md` directly via the Read tool. The agent produces `round_<N+1>/plan.md` by editing from the anchor, not regenerating from prompt fragments.

2. **Convergence is a preservation property, not a count.** Round N+1's plan diff vs round N's plan is checked against round N's `change-request.md`. Any change outside the whitelist fails the gate. Finding-category trends are a dashboard signal, not a hard gate.

3. **Codex carries its own thread.** Plan-time Codex challenges on rounds 2+ use `codex-review task --resume` so Codex's review becomes "did the diff address my prior findings" rather than a fresh re-review of a moved artefact.

4. **Long-term sequence edits require an audit trail.** `/ag-ship` is the only place that edits `long-term/sequence.md`. Each edit appends a matching entry to `long-term/revisions.md` citing the trigger.

5. **`closed/` is append-only.** Once a burst ships, its `closed/<date>-<label>-<shortsha>/` directory is frozen. The receipts are the audit trail.

6. **`current/` is single-tenant.** One burst at a time. Empty when STATUS Phase is `Idle`. /clear-safe at every planning checkpoint because all state is on disk.

7. **HAV signal lives next to the plan.** `feedback.md` (Orchestrator-redirect capture) and `feedback-review.md` (Codex review of redirects at /ag-probe retrospective) are sibling per-burst artefacts under `current/`. Both are created eagerly by `/ag-plan` Step 1 (feedback.md with empty-state header; feedback-review.md with placeholder) and migrate to `closed/<sha>/` at /ag-ship alongside the round receipts. See `docs/hav-classification-rubric.md` for the four-category capture taxonomy, six review dimensions, "populated" definition (which gates the B7 ACC tile trigger), and empty-state behaviour clause.

## See also

- `AIGILE_RULES.md ### AI-gile Document Layout` — the canonical artefact set.
- `AIGILE_CORRECTIONS.md` [2026-05-15] — why this directory exists (Plan-agent drift defect).
- `/ag-plan` SKILL.md — the skill that populates `current/`.
- `/ag-probe` SKILL.md — the skill that uses the plan as the scope reference at probe time.
- `/ag-ship` SKILL.md — the skill that migrates `current/` to `closed/` at burst close.
