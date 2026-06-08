# Overrides

Skills and agents for this repo come from the global AI-gile
canonical installation (~/.claude/ managed by ag-setup).

## To override a skill for this repo only

1. Create the override directory and copy the canonical SKILL.md:

   mkdir -p .claude/skills/ag-plan
   cp ~/.claude/skills/ag-plan/SKILL.md .claude/skills/ag-plan/SKILL.md

2. Edit the local copy
3. Commit it (team members get the override via git)

The local copy shadows the global version for this repo only.
Claude Code loads `.claude/skills/<name>/SKILL.md` in preference to
`~/.claude/skills/<name>/SKILL.md` when both exist.

## To promote an override back to canonical

Use `/ag-upstream` — it creates a branch in aigile-canonical and opens
a PR for review, so the improvement flows through governance rather than
a direct copy. Direct `cp` to `~/.claude/aigile-canonical/global/skills/`
bypasses governance; use the skill instead.

## To see what is available globally

    ls ~/.claude/skills/
    ls ~/.claude/agents/
