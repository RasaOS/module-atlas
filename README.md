# Rasa · Module · Atlas

**Canonical name:** `rasa.module.atlas`
**Repo / folder:** `module-atlas`
**Kind:** `module` (canon Spec §6)
**Contract:** Element Contract v1.3.0
**Version:** 0.1.0 (spine + seam + template + the `/atlas` driver + deterministic converters)
**Status:** Built locally; not yet pushed. Target: `RasaOS/module-atlas`.

## What this is

A portable **geospatial catalog**, mountable into any domain or orchestrator.
Where [`rasa.module.research`](../module-research/) tracks investigations and
[`rasa.module.theory`](../module-theory/) tracks patterns, this tracks **places** —
a light, greppable, color-keyed catalog of located records that scales to
thousands ("the largest personal library of sites").

## The site node

One site is **one markdown file**, sharded on the id (never by category):

```
atlas/
  INDEX.md                         # dashboard + color legend + health (NOT a per-site table)
  atlas.kml · atlas.geojson        # the real at-a-glance rollup (generated, color-styled)
  sites/
    000000-000999/
      site-000042.md               # frontmatter (id, name, lon/lat/alt, category, provenance, extended) + body
```

- **`site-NNNNNN`** id — immutable, fixed 6 digits, never recycled. A site is a
  *located record cited by id* (like a source), not a *named node linked by slug*
  (like a topic). `lon` before `lat`, always.
- **`category`** is a field, never a folder — reclassifying is a one-line edit,
  not a file move that breaks links.
- **Losslessness** — canonical facts stored once + a verbatim `provenance` block +
  an `extended` overflow bag (every unmapped KML `<Data>`/column) mean
  `import → export → re-import` is a **fixed point**.

## The color key

The category→color taxonomy lives in the project-owned `.claude/atlas-canon.md`
seam, authored once as `#RRGGBB`. The converters render it by pure function to KML
`<IconStyle>` (`aabbggrr`) + GeoJSON `marker-color` + the INDEX legend — change a
color once, every marker follows. The module's **one hard-stop**: export refuses
to derive a color for an in-use category absent from the seam (inventing a
category is the one inference it won't make).

## KML / spreadsheet round-trip

Deterministic **Python** (`content/skills/atlas/{import,export,render_key,lib}.py`,
stdlib only), orchestrated by `/atlas` — not LLM prose, because `aabbggrr` math
and 1300-row conversion must not drift. Import stages unknown categories (never
halts a bulk load); export hard-stops on them. The **release gate is a round-trip
fixed-point fixture** (`import → export → re-import` == identity).

## The `/atlas` skill

| Op | Does |
|---|---|
| `new` | scaffold one site (assign id, fill the template) |
| `import <file>` | KML/KMZ/CSV → site files; stage unknown categories + surface near-duplicates |
| `export [kml\|geojson\|both]` | color-styled KML + GeoJSON; hard-stop on unknown category |
| `index` | regenerate the dashboard (counts + legend + health) |
| `key` / `list` | show the color key; roster/filters (full geo-queries in v0.2.0) |

Plus the inherited house skills `/sync`, `/promote`, `/whoami`.

## Cross-family seams (all soft, `requires.elements[]` empty)

A site **graduates** to a `module.research` topic; its alignment is **evidence**
for a `module.theory` prediction (the archaeoastronomy case); it **cites** library
sources and is **described** with lexicon terms. Drop any sibling and the atlas
stays a valid standalone catalog.

## What a consuming domain adds

`rasa.domain.proverbs` layers four disciplines additively: a verification clock
(`last_verified:`, default OFF), contested/held-open geography, a **cross-site
sightline registry** (`aln-NNNN` — the home for archaeoastronomical alignments),
and a dated survey axis. None are built into the module.

## Install

`bin/init [target-dir]` reads `rasa.json` and applies each `element.files[]` /
`seed.files[]` entry by policy. Installs the spine + template + skills (incl. the
converters) into `.claude/`, seeds the color-key seam + dashboard + lockfile.

## See also

- `content/atlas-rules.md` — the installed spine (the discipline).
- `content/BUILD_PLAN.md` — the full spec + design record.
- `../module-research/` — a site graduates to a topic (soft).
- `../module-theory/` — a site's alignment is theory evidence (soft).
- `../domain-proverbs/` — the reference consuming domain (the four overlays).
