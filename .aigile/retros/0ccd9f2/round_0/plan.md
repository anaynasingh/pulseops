# Retrospective: intake-default-assignee (round 0)

## 1. Corrections review
PENDING entries written this burst: None. Codex plan findings C1-C4 were caught at PLAN
time and absorbed into the test set before coding (coverage gaps in a draft list, not build
defects); build adversarial review returned APPROVE/0. No new CORRECTIONS rule from C1-C4.

ag-init drift loop bug IS CORRECTIONS-worthy (repo-specific bridge) + needs /ag-upstream for
the canonical fix. Root cause: migrate_corrections_header no-ops when the Builder marker is
present, so the parser-contract drift notice never clears and .aigile/last-init is never
written → preflight hard-blocks every burst. Workaround applied: hand-sync CORRECTIONS header
to canonical template.

## 2. Command friction
ag-plan preflight hard-block resolved correctly (header synced, drift cleared, last-init
written). No other /command friction.

## 3. Missing knowledge
None. model_fields_set omit-vs-null is Pydantic-v2 standard, documented inline.

## 4. Agent gaps
None. Plan agent (opus) produced a code-grounded plan with both ambiguities surfaced; Codex
caught the three real coverage gaps.

## 5. Discovered Capabilities
ADD — intake confirm auto-assigns ownership with a three-state override contract.

## 6. Decision pipeline
Deferred: ADD — frontend assignee/owner picker (AMBIGUITY 1, deferred).
Under Consideration: none.

## Recommended writes (Orchestrator-approved)
1. PENDING → AIGILE_CORRECTIONS.md (ag-init drift workaround) + /ag-upstream.
2. Capability → AIGILE_PLAN/CAPABILITIES.md.
3. Deferred → AIGILE_PLAN/DEFERRED.md.
