# CLAUDE.md

<!-- AIGILE:START - Do not edit this block. Managed by ag-init. -->

## AI-gile Rules

### Session start

On your first response in every session:

1. Check whether the SessionStart hook already fired and provided output
   in the system-reminder. If it did, act on that output directly — no
   manual run needed (avoids a duplicate).
2. If no hook output is present in the system-reminder, run
   `$HOME/.claude/aigile-canonical/scripts/ag-status --quiet` manually.
   The hook is unreliable in the desktop app and web
   UI after `/clear` (confirmed bug: anthropics/claude-code#34072); the
   manual run is the guaranteed fallback.

```bash
$HOME/.claude/aigile-canonical/scripts/ag-status --quiet
```

Interpret the output (whether from the hook or the manual run):

- If it contains `ACTION REQUIRED` with `ag-init --auto`: run it
  immediately before anything else. Do not ask.
- If it contains `AIGILE RESUME (in-flight): <burst-label> — active burst
  in progress. Run /ag-resume to continue.`: run `/ag-resume` before
  responding to the user's first message. The plan is already approved
  and on disk; skip the full /ag-plan pipeline.
- If it contains `AIGILE RESUME (delegated): <burst-label>`: run
  `/ag-delegate` before responding to the user's first message. A stream
  is currently delegated to an external builder; present status/accept/abandon
  options to the Orchestrator.
- If it contains `ACTION REQUIRED (post-/clear)` with `run /ag-plan`:
  run `/ag-plan` before responding to the user's first message.
- If it contains `AIGILE RESUME:` (no `in-flight` qualifier, no post-/clear),
  it is the forward pointer from a prior non-clear session. Present it to
  the Orchestrator and confirm before acting. Do NOT auto-execute.
- If it contains `[understand-anything] Knowledge graph is stale`, spawn the
  background fork agent exactly as described — see the rule below.
- If it contains override or health warnings, mention them once and continue.
- If empty: repo is healthy and idle. Proceed normally.

### Understand-anything auto-update rule

When any session-start system-reminder contains `[understand-anything] Knowledge graph
is stale`, spawn a background fork agent as your very first action (before responding
to the user). The hook will include an `Agent({...})` call — execute it exactly as
shown. Do not execute the update inline; it spawns multiple sub-agents and blocks the
session. Do not ask the user for confirmation.

If the hook message is the old form ("You MUST read the file … and execute its
instructions"), override it: spawn a background fork with the prompt "Read <path> and
execute all its instructions to incrementally update the knowledge graph." Find the
path with: `find ~/.claude/plugins/cache/understand-anything -name 'auto-update-prompt.md' | sort -rV | head -1`

This rule also applies after git commits — the PostToolUse hook fires with the same
pattern.

### Pre-flight init check

Before executing any ag- skill (ag-plan, ag-probe, ag-ship, ag-resume, ag-charter,
ag-delegate, ag-brief, ag-handoff, ag-stream), run the pre-flight gate:

```bash
LIB_DIR="$HOME/.claude/aigile-canonical/lib"
. "$LIB_DIR/ag-preflight.sh"
ag_preflight "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

Interpret the result:
- `PREFLIGHT_OK` — proceed normally.
- `PREFLIGHT_REMEDIATED: …` — `ag-init --auto` ran automatically; proceed.
- `PREFLIGHT_FAIL: …` (exit 26 = branch gate; exit 25 = mid-burst marker) — **HARD STOP.**
  Surface the message verbatim to the Orchestrator and wait for resolution.

ag-ship deletes `.aigile/last-init` at Step 12 after shipping, so every new burst cycle
starts with a forced ag-init. This ensures canonical skills and settings are always current.

### Plan first

Start every non-trivial task in Plan Mode. Iterate until the plan is
solid before building. A good plan prevents most correction Bursts.

### Build commits

During a burst build (STATUS Phase=Building), commit completed stream
work as it lands — do not wait to be asked. The harness default
"commit only when requested" is superseded by the burst workflow.
The burst base is the Codex adversarial review anchor; commits must
land on dev for the review to cover the actual diff.

### Stage ownership and gate discipline

You own forward progress through the AI-gile cycle. After every substantive
stage, tell the Orchestrator: (1) what completed and the evidence for it,
(2) the exact next mandatory action, (3) who owns that action, and (4) whether
Orchestrator confirmation is required. Do not leave a completed stage with a
blank or make the Orchestrator infer the next step. Start normal, safe,
in-scope next actions without waiting.

Mandatory gates are never optional because they are inconvenient or because a
tooling limitation is encountered. Do not call work ready to ship while a
required gate is unresolved. State the gate, its evidence or failure, and the
compliant route forward. If no compliant route exists, request an explicit,
recorded Orchestrator exception; do not silently defer it.

### Verify your work

Always self-verify. Run tests, check the UI, check the API. Flag
anything you cannot verify with `# AMBIGUITY:`. When a build Burst
completes, run /ag-probe immediately. Do not wait for the human to
ask. Deployment success is not a proxy for probe: a live app means
only the API check (Step 4) passed. Tests, Codex adversarial review,
and the formal steer checkpoint are all still required. STATUS Phase
moves Building → Steering via probe only — a working deploy is not
probe done.

### Test verification economy

Applies everywhere — inside `/ag-probe` or `/ag-challenge`, and equally in
ad-hoc fix-and-verify work outside a formal skill invocation (e.g. chasing
a CI failure directly on a PR during ship finalization). Wasting
Orchestrator wall-clock time on unnecessary verification is itself a
failure of AI-gile, not a merely suboptimal tactical choice.

Never invoke a bare full-suite test command. Run `/ag-test` (or
`scripts/ag-test-plan` directly) with an explicit scope and rationale —
it computes what actually needs to run and, for a large/full-suite plan,
shards the work across parallel Haiku subagents. See the skill for the
full protocol.

This rule previously lived as restated prose in `docs/probe-fix-phase-gate.md`
step 4.5 and inside `ag-probe`/`ag-challenge`'s own skill files, and was
violated three times across three different contexts precisely because
each fix only propagated the rule to the specific skill file in play,
never to a mechanism every path actually runs through. `ag-test-plan` /
`/ag-test` is that mechanism — see `AIGILE_CORRECTIONS_ARCHIVE.md` for the
incident history this absorbs.

### Codex invocation

Never invoke `/codex:<cmd>` via the Skill tool. Claude Code's
harness silently drops Skill-routed plugin results with
`[Tool result missing due to internal error]` and breaks safety
gates without warning.

Always invoke Codex through the Bash wrapper at absolute path:

```
$HOME/.claude/aigile-canonical/scripts/codex-review <subcmd> [args]
```

Subcommands mirror the slash forms (`adversarial-review`, `review`,
`rescue`, `task`, `status`, `result`, `cancel`, `setup`). The
wrapper checks Codex readiness before launching execution
subcommands and surfaces specific repair guidance on failure.
The `rescue` alias approximates `/codex:rescue` for the bash
environment - it auto-adds `--write` (matching the plugin's
write-by-default) and hard-fails with exit 7 when a resumable
rescue thread exists and no `--resume`/`--fresh` was passed
(it cannot replicate the plugin's interactive `AskUserQuestion`
prompt). Pass `--resume` or `--fresh` explicitly when invoking
`rescue` in a session that may have a prior rescue thread. Treat
the wrapper's exit code as authoritative:

- Exit 0: success; pass output to the Orchestrator.
- Exit non-zero: STOP. Surface stderr verbatim. Do not fabricate
  "review running" or a synthetic critique. The wrapper's stderr
  names the specific repair (install CLI, login, install plugin,
  install node, etc.).

If the wrapper itself is unreachable (rare - canonical install
broken), ask the Orchestrator to type `/codex:<cmd>` at the
prompt directly. User-typed slash commands go through the
command router, not the Skill tool, and work in that edge case.

### Canonical edits

Never edit files under `~/.claude/` or canonical skill paths directly
from within a client repo. Editing canonical files via symlinks bypasses
governance and creates uncommitted changes that are discovered by luck.
To propose a skill improvement discovered in this repo, use `/ag-upstream`.

This rule applies to client repos only. Canonical maintainers working
directly in `aigile-canonical` edit those files as their normal workflow.

### AI-gile Document Layout

Canonical methodology files live at repo root with the `AIGILE_`
prefix. These names are authoritative - if any user-owned prose elsewhere
in this file (or anywhere in the repo) references a different path, the
names below win:

- `AIGILE_CHARTER.md` - vision (where we want to get to)
- `AIGILE_DECISIONS.md` - decisions (record of challenged decisions)
- `AIGILE_PLAN/` - route (how we get there; directory artefact, peer of CHARTER)
- `AIGILE_STATUS.md` - now (where we are right now; thin index)
- `AIGILE_HISTORY.md` - past (closed burst log)
- `AIGILE_CORRECTIONS.md` - lessons (record of past mistakes and their fixes)

`AIGILE_PLAN/` carries the long-term burst sequence under `long-term/`,
the active burst's working store under `current/` (per-round plan,
adversarial critique, determination, change-request whitelist,
preservation diff), and the closed-burst archive under
`closed/<date>-<burst-label>-<shortsha>/`. `ag-init` creates the
CHARTER-extracted operational zones at the `AIGILE_PLAN/` root:
`CAPABILITIES.md` (discovered capabilities), `DEFERRED.md` (deferred
items with trigger conditions), and `CONSIDERATIONS.md` (items under
consideration with resolution needs). A future data-infrastructure
burst may relocate these under `long-term/` with lowercase-hyphenated
names to match `sequence.md`/`revisions.md`'s convention — treat that
as forward-looking, not current behaviour.
See `AIGILE_PLAN/README.md` for the full structure and the
file-anchored iteration rules.

`AIGILE_ORCHESTRATION.md` was **removed in v9.0.0** — its stream-decomposition
role moved into `AIGILE_PLAN/current/round_<N>/plan.md` and its operational
per-stream tracking moved into `AIGILE_STATUS.md ## Active streams`.
`ag-init` removes any legacy `AIGILE_ORCHESTRATION.md` or
`CLAUDE_AIGILE_ORCHESTRATION.md` from upgrading repos automatically.

Obsolete locations you may still see in older repos: `docs/ai_gile/STATUS.md`,
bare `STATUS.md`, `ORCHESTRATION.md`, `HISTORY.md`, `CHARTER.md`, and any
`## Corrections Log` section inside CLAUDE.md (migrated to
`AIGILE_CORRECTIONS.md`). Treat these as stale references - the
files above are the real ones.

### CHARTER is the north star

AIGILE_CHARTER.md defines the project Vision, Hard Specs, and
Objectives. Read it before planning. Hard Specs are non-negotiable.
If the CHARTER is blank, run /ag-adopt to seed it before doing any work.

For extracted CHARTER content that changes frequently or accumulates
history, read the peer artefacts instead: `AIGILE_PLAN/CAPABILITIES.md`
(Discovered Capabilities), `AIGILE_PLAN/DEFERRED.md` (Deferred items),
`AIGILE_PLAN/CONSIDERATIONS.md` (Under Consideration items), and
`AIGILE_DECISIONS.md` (Challenged Decisions log). If any of these
files does not yet exist, fall back to the corresponding section in
AIGILE_CHARTER.md — transitional behaviour until the data burst lands.

### Context economy

The burst cycle preserves state in files (STATUS, HISTORY, CORRECTIONS,
commits, CHARTER). Conversation context is disposable after a burst ships.

`/clear` hard conditions (all must be true - these are checkable):

**Standard (post-burst) /clear:**
- STATUS `**Phase:**` = `Idle`
- STATUS `**Active burst:**` = `None`
- Working tree is clean (`git status --short` is empty)

**Mid-burst /clear (after a completed Codex round):** safe ONLY when:
- Working tree is clean (no uncommitted build edits)
- STATUS `**Phase:**` = `Building`
- `AIGILE_PLAN/current/round_<N>/determination.md` has been written for
  the current round (round is fully resolved)

Hard-blocked phases — do NOT `/clear` mid-burst when Phase is
`Probing`, `Steering`, or `Delegated`. These phases may have in-flight Codex threads,
pending steer questions, or active delegation artefacts that cannot be resumed from
disk alone. If Phase is `Delegated`, run `/ag-delegate` to accept or abandon the
delegation before clearing.

If any hard condition fails, do not suggest `/clear`. Surface the
specific failing condition (e.g. "STATUS Phase is Building, not Idle").

Advisory checks (warn if these look wrong, but do not hard-block):

- STATUS `**Next action:**` should start with `Burst complete`
- No known background agents still running in this session
- `AIGILE_PLAN/current/` should be empty when STATUS Phase is `Idle` (the directory was migrated to `closed/` at /ag-ship; non-empty indicates an unfinished burst)

Empty `AIGILE_PLAN/current/` = no active burst working state = safe to clear.

Mid-burst clears are safe because plan artefacts are file-anchored in
`AIGILE_PLAN/current/`. After a mid-burst /clear, the next session
reads `ag-status --quiet`, sees `AIGILE RESUME (in-flight):`, and runs
`/ag-resume` to continue without re-running the full /ag-plan pipeline.

Do NOT `/clear` when:

- Uncommitted working tree
- Steer question asked but not answered
- STATUS Phase is `Probing`, `Steering`, or `Delegated`
- STATUS Phase is not Idle or Active Burst is not None (unless mid-burst
  conditions above are met)

`/compact` is a weaker alternative: preserves continuity, halves context.
Use when the burst is not done and mid-burst /clear conditions are not met.

After a completed Codex round (determination.md written, worktree clean):
if context > 25%, suggest `/clear` and `/ag-resume` to the Orchestrator.

After `/clear` in the standard post-burst case, the SessionStart hook
runs `ag-status --quiet` which emits `ACTION REQUIRED (post-/clear):
run /ag-plan`. The session start rule handles this automatically.

After `/clear` in the mid-burst case, `ag-status --quiet` emits
`AIGILE RESUME (in-flight): <burst-label>`. The session start rule
routes this to `/ag-resume`.

Claude Code does not expose token counts programmatically. To check
actual context usage, run `/cost` interactively. Suggest `/cost` at
natural checkpoints (steer, ship, retrospective) when the session
has been heavy.

### Context management

Context thresholds (treat context as scarce — weekly limits are tighter than 5-hour limits):

- **25%**: run `/cost` and report usage. If /clear conditions allow, suggest `/clear`.
- **30%**: strongly suggest `/clear` if conditions allow; `/compact` otherwise. Do not wait.
- **50%**: `/compact` mandatory if conditions do not allow `/clear`. Do not proceed without compacting.
- **70%**: hard cap. Do not let context exceed this.

After every Codex round with determination.md written and worktree clean: if context > 25%,
suggest `/clear` and `/ag-resume` (mid-burst path) before the next sub-phase.

### Corrections

When you make a mistake and the Orchestrator corrects you, immediately
write a `PENDING:` entry to `AIGILE_CORRECTIONS.md`:

```
PENDING: [YYYY-MM-DD] Short rule.
         Builder: <claude|codex|mixed|n/a>.
         Why: <what went wrong>.
         How to apply: <when this kicks in>.
```

One field per line, indented to align with the date bracket. Keeps
human scanning easy and lets dedupe/migration tooling key on
(first line, Builder) so identical rule text from different builders
remains distinct - per-builder data is the whole point of this field.

`Builder:` records which agent produced the work that earned the
correction. Values: `claude`, `codex`, `mixed` (multi-stream burst
with both), or `n/a` (process/orchestration correction not tied to
a builder, e.g. push-to-main rule). Set this at write-time, not at
retrospective - the live context knows who built what.

If a `PENDING:` entry surfaces at retrospective with no
`Builder:` line, the Orchestrator decides per entry whether it is
a grandfathered pre-v5.11.0 backlog entry (mark `Builder: legacy`,
promote) or a current write-time omission (HARD STOP - supply
Builder or discard). No automated date gate; the Orchestrator is
the authority. See `/ag-probe` Step 7 retrospective for the
full rule. Never infer Builder from the diff under review -
inference looks clean while being wrong.

Announce inline: _"PENDING correction written: [rule summary]"_

Do not defer this to the retrospective. Write it now, in the moment,
while the context is live.

`PENDING:` entries are provisional notes, not active policy. Do not
follow them as standing rules. Only promoted entries (prefix removed
at retrospective) should be applied in future sessions.

At probe retrospective, each `PENDING:` entry is reviewed:
promoted to permanent (prefix removed) if still valid, or discarded
if it was a false alarm. The Orchestrator confirms each, including
the `Builder:` value.

Never write corrections into `CLAUDE.md` itself.

### HAV redirect capture

When the Orchestrator redirects you at any point in the methodology cycle
(Plan, Build, Probe, or Ship), propose to log it. The
orchestrator-assistant should ask "log as redirect?" with a proposed
classification when the conversation contains a candidate redirect: a
moment where the Orchestrator changed the burst's direction, scope, or
specific implementation choice in a way that materially affected what
gets shipped.

The Orchestrator confirms or rejects the proposal. On confirm, append a
structured entry to `AIGILE_PLAN/current/feedback.md` (initialized at
the start of `/ag-plan` Step 1 — always present before any redirect is
requested). See `docs/hav-classification-rubric.md` for the
canonical four-category capture taxonomy, the six dimensions Codex scores
at `/ag-probe` retrospective Step 4, the disk schema (machine-stable
headers, ASCII pipe separators), the "populated" definition that gates
the B7 ACC tile trigger, and the empty-state behaviour clause.

This is the v0 cadence. The detection threshold for "log as redirect?"
prompts will be tuned by pilot bursts. Flagging too often is friction;
flagging too rarely loses signal. Per CHARTER need (f), the tuning is
OUT OF SCOPE for the v9.1.0 substrate burst that introduces the
mechanism.

### Push to main

Never push to main without stating explicitly what you are about to do
and waiting for "confirmed" or "go ahead". Steer approval is not push
approval - they are separate confirmations.

### Branch hygiene (two-contract override model, CD-026)

Burst work never lands on `main` without an open PR. This is enforced
across multiple layers (defence in depth):

- `/ag-plan` Step 0 hard-stops planning if the working branch is
  `main`/`master`.
- Local `pre-commit` hook (canonical at `~/.claude/aigile-canonical/
hooks/pre-commit`, installed by `ag-setup` as `.husky/pre-commit`)
  refuses commits on `main`/`master`.
- Local `pre-push` hook refuses pushes whose REMOTE ref targets
  `main`/`master` (catches `HEAD:main`, deletions, multi-ref, non-
  `origin` remotes).
- `ag-status` warns loudly when branch is `main`/`master` AND STATUS
  Phase is not `Idle`.
- Server-side: GitHub branch protection on `main` (apply via
  `scripts/ag-protect-main`) requires PR review, dismisses stale
  reviews on push, forbids force push and deletions.

**Two-contract override model.** The local hooks and the GitHub
branch protection are **separate contracts**. You must obtain BOTH
overrides for a true direct-to-main push.

**Local override** (bypasses local hooks ONLY):

1. Preferred: command-scoped env var.
   ```
   AIGILE_ALLOW_MAIN=1 git commit -m "..."
   AIGILE_ALLOW_MAIN=1 git push origin main
   ```
2. Multi-step alternative: untracked `.aigile-allow-main` file at
   repo root, **burst-scoped** (two lines required):
   ```
   reason on line 1
   <burst-base-SHA> on line 2 (≥7 chars; copy from AIGILE_STATUS.md)
   ```
   Example:
   ```
   # Read the current burst base SHA
   grep '^\*\*Burst base' AIGILE_STATUS.md
   # → **Burst base:** d03fb312d5b5af8b7469efa2ccd8c3108c73f3af

   # Create the override file
   printf 'hotfix for incident X\nd03fb31\n' > .aigile-allow-main
   git commit -m "..."   # stderr: "Override used (burst d03fb31...): hotfix for incident X"
   rm .aigile-allow-main  # delete after hotfix lands
   ```
   The hook refuses the file if:
   - line 2 is missing or under 7 chars (no SHA)
   - line 2 does not prefix-match `**Burst base:**` in STATUS (stale)
   - STATUS `**Phase:**` is `Idle` (no active burst context)
   - The file is tracked or staged (sticky bypass — see antipatterns)

   `ag-status --quiet` surfaces "override file is present in this repo"
   so you can spot stale files between bursts.

**Server override** (bypasses GitHub branch protection):

- The canonical hotfix path is a PR with a `hotfix` label (or admin
  push if `enforce_admins=false` in the protection ruleset). The
  local override does NOT bypass GitHub's enforcement.
- See `docs/BRANCH-PROTECTION.md` for the full server contract.

**Antipatterns (refused or warned):**

- Never `export AIGILE_ALLOW_MAIN=1` in shell rc files. The override
  is meant to be command-scoped, not persistent.
- Never `git add .aigile-allow-main`. The hooks detect this as
  "sticky bypass" and refuse the commit/push entirely. The file is
  in `.gitignore` for a reason — leaving it tracked silently
  disables the guard for everyone on the repo.
- An empty `.aigile-allow-main` (no reason on first line) is
  refused.

### Docs sync with build

When a burst changes a number, capability, or behaviour that a
`docs/papers/current/` file describes, update the relevant paper in
the same commit. The papers are the living specification; they must
not drift from what the system does.

<!-- AIGILE:END -->


## Project

**Name:** PulseOps
**Repo:** github.com/anaynasingh/pulseops
**Purpose:** AI-powered team operations and workflow intelligence platform
**Owner:** Anayna Singh, P33

## Stack

**Language:** Python 3.11+ (backend) / TypeScript (frontend)
**Framework:** FastAPI (backend) / Next.js 14+ App Router (frontend)
**Database:** PostgreSQL with pgvector via Supabase
**Package manager:** pip (backend) / npm (frontend)
**Deploy:** TBD
**Test runner:** pytest (backend) / vitest (frontend)
**Formatter:** black (backend) / prettier (frontend)

## Key Commands

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Frontend
cd frontend
npm install --ignore-scripts
npm run dev

# API docs
open http://localhost:8001/docs
```

## Environment Variables

- `backend/.env` — copy from `.env.example`, fill in `DATABASE_URL`, `OPENROUTER_API_KEY`, `SECRET_KEY`
- `frontend/.env.local` — `NEXT_PUBLIC_API_URL=http://localhost:8001`

## AI Stack

- **LLM:** OpenRouter → GPT-4o (structured JSON outputs)
- **Embeddings:** HuggingFace `all-MiniLM-L6-v2` (384-dim, free tier)
- **Vector DB:** pgvector on Supabase (cosine similarity)

## AI-gile Operating Model

This repo operates under AI-gile.
Global rules in ~/.claude/CLAUDE.md. Repo-specific additions below only.

## Repo-Specific Rules

<!-- Rules genuinely specific to this repo only. -->
<!-- Do not duplicate rules in ~/.claude/CLAUDE.md -->

<!-- Corrections from real mistakes live in AIGILE_CORRECTIONS.md -->
<!-- not here. See that file for past errors and their fixes.           -->
