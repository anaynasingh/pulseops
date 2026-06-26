# Long-term burst sequence

The route from where we are now to the CHARTER vision. Each burst cites the CHARTER objective(s) it advances.

Edited only at `/ag-ship` retrospective. Every edit requires a matching entry in `revisions.md` citing the trigger.

---

## Active engagement: [engagement name]

**Decided:** [YYYY-MM-DD]

**Scope:** [CHARTER objectives in scope, e.g. O1-O5]

**Stack:** [stack summary]

**Deployment:** [deployment target]

### Phase 0 — [phase name] (~N bursts)

- [ ] **B1** advances [Ox] — [description]
- [ ] **B2** advances [Ox] — [description]

### Phase 1 — [next phase] (~N bursts)

- [ ] **BN** advances [Ox] — [description]

<!-- Add phases and bursts as the engagement scope is decomposed. Mark
     bursts complete with [x] and the ship date at /ag-ship. -->

---

## Out-of-sequence bursts

Methodology fixes and other work not in the phased plan above. Each cites its trigger.

<!-- Each entry: [in progress | YYYY-MM-DD] burst-label — one-sentence
     description. Trigger: (closed burst | CORRECTIONS rule | CHARTER
     update). -->

- [2026-06-26] intake-functional — made the AI Intake confirm flow functional: classify project-vs-task + route to new/existing project, create real Task rows, log activity, fix board-refresh. Advances CHARTER O3. Trigger: user bug report (intake generated items but did nothing). Shipped prod 63a8b48 (PR #8).
- [x] [2026-06-26] intake-default-assignee — intake confirm defaults new project owner_id + created task assigned_to to the confirming user (model_fields_set omit-vs-null contract; explicit override/null preserved; Route 2 existing owner untouched). Advances CHARTER O1 (backend API completeness). Trigger: user request (auto-assign task/project to the adder unless otherwise specified). Shipped prod 98316eb (PR #9).

## Pending decisions (not blocking active sequence)

<!-- Items that should reach a decision before they become blockers. -->
