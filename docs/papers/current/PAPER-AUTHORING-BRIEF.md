# Paper Authoring Brief

This is the durable authoring anchor for this repo's paper suite. Every paper in `current/` must reflect the locked facts listed here. When a fact changes in the codebase, update this brief and the relevant paper in the same commit.

## The documents

| Seq | Paper | File | State |
|---|---|---|---|
| — | _(add papers here)_ | — | — |

## Authoring mechanics

### COVER block

Every paper begins with a COVER comment block that `md2html.py` renders as a cover page:

```
<!-- COVER
title: <title>
subtitle: <subtitle>
org: <organisation>
date: <month year>
confidential: <footer text>
footer: <running footer>
-->
```

### Markdown conventions

- `## Heading` — section heading (renders as a new page group)
- `![caption](figures/<name>.png)` — embedded figure (base64, no external dependency)
- `<!-- INTERACTIVE <name> -->` — inline interactive widget (live on screen, static in print)
- `<!-- COLLAPSE: <summary> --> … <!-- /COLLAPSE -->` — collapsible detail (open in print)

### Rendering

```
python3 docs/papers/tools/md2html.py docs/papers/current/<paper>.md docs/papers/current/<paper>.html
```

The output is a single self-contained HTML file. Open in a browser; print with `File > Print` for a clean A4 PDF.

## Locked decisions

Fill in per-repo: locked product decisions, taxonomy, named entities, and archival facts that every paper must reflect consistently. Numbers, definitions, and naming decisions belong here so they do not drift across papers.

| Decision | Value | Source |
|---|---|---|
| _(none yet)_ | — | — |

## Reconstruction note

If this brief is absent or incomplete, reconstruct it by reading `current/` papers and extracting the claims that appear in multiple papers or that could become inconsistent under independent editing. The brief exists to prevent exactly that inconsistency.
