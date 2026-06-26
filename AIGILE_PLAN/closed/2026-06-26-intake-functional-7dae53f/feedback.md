# Orchestrator redirects: intake-functional

## 2026-06-26T08:45:19Z | round_0 | strategic

Stage: round_0 (planning / scope definition).
Trigger: I presented a scoping question on how flexible the intake confirm action should be — A: new project + its tasks (minimal relabel + wire), B: add a target selector (new/existing/standalone), C: AI classifies project-vs-task and routes automatically with user override + parent-project picker. The Orchestrator selected Option C.
Effect: Set the burst to the full classification + override + routing scope rather than the minimal Option A fix. Materially expanded what shipped: new suggested_item_type column + migration 002 + startup auto-migration, the 8-case confirm_intake router, and the frontend type selector + parent-project picker — versus what would have been a relabel + subtask-creation + invalidation fix only.
AI prior: I presented the three options without a strong recommendation; Option C was the largest-scope choice.
