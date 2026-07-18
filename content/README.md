# `rasa.module.atlas` — content

What this module ships and where it installs. Author-time documentation (not
installed into consumer projects).

## The one-liner

The **atlas** module: a portable, light, color-keyed geospatial catalog — one
markdown file per place, scaling to thousands, with a project-owned category→color
key and a lossless KML/GeoJSON round-trip.

## What installs where

| Source | Installs to | Policy | What it is |
|---|---|---|---|
| `content/atlas-rules.md` | `.claude/atlas-rules.md` | file-replace | The spine — the file-per-site node, the `site-NNNNNN` id + id-block sharding, the losslessness contract, the color key + KML/GeoJSON round-trip, the INDEX-as-dashboard convention, the soft cross-family seams, and the one color-key hard-stop. Element-owned; distinct filename (no collision with `research-rules.md`/`theory-rules.md`). |
| `content/atlas-template/` | `.claude/atlas-template/` | directory-mirror | The single-file per-site skeleton (`site.md`) `/atlas new` instantiates. Element-owned. |
| `content/skills/` | `.claude/skills/` | directory-mirror | The `/atlas` driver + the deterministic converters (`import.py`/`export.py`/`render_key.py`/`lib.py`, stdlib only) + the inherited house skills (`/sync`, `/promote`, `/whoami`). Element-owned. |
| `seed/atlas-canon.md.template` | `.claude/atlas-canon.md` | skip-if-exists | **The seam** — the category→color taxonomy (`#RRGGBB` → KML `aabbggrr` + GeoJSON `marker-color`). Project-owned; export hard-stops on an in-use category absent here. |
| `seed/atlas/INDEX.md.template` | `atlas/INDEX.md` | skip-if-exists | The dashboard (counts + legend + health). Project-owned; also creates the `atlas/` root. |
| `seed/rasa.lock.json.template` | `.claude/rasa.lock.json` | init-only-with-sha | Connection-Contract lockfile, SHA-stamped at init. |
| `seed/rasa-deployment.md.template` | `.claude/rasa-deployment.md` | skip-if-exists | The deployment identity layer (SA-025); project-owned. |

## The capability (the reason it exists)

**Catalog places** — one light `site-NNNNNN.md` per place (frontmatter is the
greppable layer; the body holds what a row can't), a project-owned category→color
key rendered by pure function to KML + GeoJSON, and a lossless import/export
round-trip (`import → export → re-import` is a fixed point). Ships **zero subject
content**.

## The converters

`content/skills/atlas/` ships runnable Python (standard library only):

- `lib.py` — id scheme, `rgb_to_kml`/`kml_to_rgb`, the deterministic frontmatter
  emitter/parser, the site reader/writer, haversine.
- `import.py` — KML/KMZ/CSV → site files; re-joins by `entry_id`; stages unknown
  categories; surfaces near-duplicates.
- `export.py` — site files → color-styled KML + GeoJSON; hard-stops on an unknown
  category.
- `render_key.py` — the color key → KML `<Style>`/`<StyleMap>` + the INDEX legend.

## The shape

Toolkit module, `requires.parent_kind: [domain, tenant]`. Soft cross-refs to
`rasa.module.research` (graduate-to-topic), `rasa.module.theory` (alignment
evidence), and `rasa.module.jobs` (a re-verify sweep) — none in
`requires.elements[]`.

## See also

- [`BUILD_PLAN.md`](BUILD_PLAN.md) — the full spec + design record.
- `content/atlas-rules.md` — the installed spine.
- `../module-research/`, `../module-theory/` — the siblings a site links to.
- `../domain-proverbs/` — the reference consuming domain (the four overlays).
