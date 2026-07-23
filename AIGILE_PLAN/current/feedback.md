# Orchestrator redirects: transcript-intake-bell

## 2026-07-23T09:27:36Z | round_ship | strategic

**Trigger:** At the /ag-ship RELEASE FLOW STOP gate, Claude presented the prepared promotion of dev (b915381..d534c7a, transcript-intake-bell) to P33-AI master via a release branch + PR, which would trigger the Railway PRODUCTION deploy for all users.
**Redirect:** Orchestrator: "go ahead. also dont do it on main, do it on dev server" - confirming the ship but redirecting the release target from production (P33 master) to the dev environment only.
**Evidence:** The feature's live checks are still deploy-gated (live API suite, browser bell check, real Graph poll against actual M365 tenants were all deferred to deployment through probe); the dev server is the correct place to observe first real-tenant behaviour before exposing the poll and bell to all production users.
**Outcome reference:** Ship converted from RELEASE FLOW to dev-only delivery: local dev pushed to origin/dev and p33/dev (stale p33/dev reconciled by merge, no force push); no PR to master; burst closed with prod promotion recorded as the pending next /ag-ship action once dev-server verification satisfies the Orchestrator.
