# Paper Suite

This folder holds the strategic product papers and the references that define them. It is structured so the **authoritative source is always obvious** and superseded versions are never lost.

## Layout

```
docs/papers/
├── README.md                          ← you are here
├── current/                           ← AUTHORITATIVE. The live source of truth.
│   ├── PAPER-AUTHORING-BRIEF.md       the durable authoring anchor
│   └── reference/                     facts the papers cite (source of truth)
├── archive/                           ← superseded & original versions, dated. Never edited.
└── tools/
    └── md2html.py                     markdown → page-turning book HTML (symlink to canonical)
```

The deliverable format is **HTML** — a self-contained, page-turning book that also prints to PDF. Word/DOCX is not produced.

## The rules

1. **`current/` is the only authoritative location.** When you need to know what the product *is* — for a build decision, a new paper, a client deck — read from `current/`. Nothing in `archive/` is current by definition.

2. **The `.md` is the source of truth; the HTML is generated.** Author and edit the markdown. The single rendering is HTML (`md2html.py`): one self-contained file (no external libraries) that presents the paper as a **page-turning book** on screen — discrete A4 pages turned with arrow keys / on-screen buttons, a running confidentiality footer and page numbers — prints to a clean A4 PDF (`File > Print`). **No Word/DOCX.** Never hand-edit the HTML as the master. From the repo root:
   ```
   python3 docs/papers/tools/md2html.py docs/papers/current/<paper>.md docs/papers/current/<paper>.html
   ```

3. **Docs stay synchronised with the build.** When the codebase discovers a new capability, changes a number, or adds a requirement, the relevant `current/` file (paper or reference) is updated **in the same change**. The papers are the living specification of the product; they must not drift from what the system does. The locked facts every paper must reflect are listed in `current/PAPER-AUTHORING-BRIEF.md`.

4. **Archiving a version.** When a paper reaches a milestone and is about to be materially revised, snapshot the outgoing version into `archive/` with a `YYYY-MM-DD-` prefix before editing `current/`. Git history is the fine-grained record; `archive/` holds the human-meaningful milestones (a published v1, a version sent to a client, a superseded original).

5. **Polish happens elsewhere.** This pipeline produces a clean, correct, branded draft. Final design polish is done downstream from the `current/` HTML/CSS — a web-oriented design workflow refines the HTML and produces the polished hosted page and PDF. Keep effort here on *content correctness*, not visual design.

## Figures and interactives

Figures should be **generated from the codebase's own formulas**, never hand-drawn, so their numbers cannot drift from the product. Generators live in `tools/figures/` (one `.py` per figure, plus `figstyle.py` for shared brand constants and `build_all.py` to rebuild every figure). Outputs go to `current/figures/` as both **PNG** (base64-embedded in the HTML) and **SVG** (handed to Design). Embed a static figure with markdown image syntax on its own line:

```
![caption](figures/<name>.png)
```

Interactive figures are **inlined** with a directive on its own line:

```
<!-- INTERACTIVE <name> -->
```

The widget is live on screen inside the page flow. Widgets are defined in `md2html.py`. **Every interactive carries a paper equivalent — itself, frozen at default values.** In print the renderer hides the sliders and keeps the chart/diagram, so the PDF shows a faithful, canonical static snapshot. Any new widget gets this automatically, provided its default state is a sensible static reading.

Detail that should be in the PDF but clutters the screen read can be wrapped in `<!-- COLLAPSE: summary --> … <!-- /COLLAPSE -->` — collapsed on screen, forced open in print.

### Consistency and legitimate reuse

- **One generator per figure.** A figure has exactly one generator. If two papers need the same figure, both embed the *same* output file; neither re-creates it.
- **Shared style.** All generators import `figstyle.py`. Brand colours, fonts, and helpers change in one place.
- **Rebuild before each paper ships.** Run `python3 docs/papers/tools/figures/build_all.py` so every embedded figure reflects the current formulas, then regenerate the affected HTML.

### Figure / interactive registry

Update this table when a figure is added or reused. It is the source of truth for which figure appears in which paper.

| Figure / Interactive | Generator / Definition | Source | Used in |
|---|---|---|---|
| _(none yet)_ | — | — | — |
