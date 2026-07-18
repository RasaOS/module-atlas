---
name: atlas
description: Manage a geospatial site catalog — add, import (KML/KMZ/CSV), and export (color-styled KML + GeoJSON) located records with a project-owned category color key. Reads .claude/atlas-rules.md (the discipline) + .claude/atlas-canon.md (the color key). Triggered by "/atlas", "add a site", "import KML", "import placemarks", "export the map", "export KML", "export GeoJSON", "catalog this place", "color key", "site catalog".
---

# /atlas — the geospatial site catalog driver

Manage `atlas/sites/<id-block>/site-NNNNNN.md` — a light, color-keyed catalog of
places that scales to thousands. **Read `.claude/atlas-rules.md` first** (the
node, the id scheme, the losslessness contract, the color key). The category→color
taxonomy is the project-owned `.claude/atlas-canon.md` seam.

The conversions are **deterministic Python** in this folder — call them; never
do KML `aabbggrr` math or lossless row conversion in prose. All operations
**stage** files; the human commits.

## Behavior contract

- Every site is one file with an immutable `site-NNNNNN` id (fixed 6 digits,
  never recycled). `category` is a field, never a folder; sharding is on the id.
- `lon` before `lat`, always. One canonical copy of each fact; color is derived
  from `category` + the seam at export, never stored.
- Import **stages** unknown categories and reports them — it never halts a bulk
  load. Export **hard-stops** on any in-use category absent from the seam.
- The round-trip `import → export → re-import` is a fixed point on
  `{id, name, category, lon, lat, alt, folder_path, sources, extended, description}`.
- Never invent a category or a color. Never auto-merge a near-duplicate. Never
  delete a site — retire it (`status: retired: "<reason>"`).

## Process

Run the helpers from `.claude/skills/atlas/` (paths relative to the project root;
`<root>` is the atlas root, default `atlas/`; `<canon>` is `.claude/atlas-canon.md`):

- **`/atlas new "<name>" <lon> <lat> <category>`** — scaffold one site from
  `.claude/atlas-template/site.md`: assign `highest+1` id, fill placeholders,
  write to `atlas/sites/<block>/site-NNNNNN.md`. If the category is not yet in the
  seam, **stage-and-warn** (write the site, tell the user to add it before export)
  — the only hard-stop is at export, never at input.
- **`/atlas import <file...>`** — `python3 .claude/skills/atlas/import.py <root> <canon> <file...>`.
  KML/KMZ/CSV in; reports staged categories + near-duplicates. Review the report,
  add staged categories to the seam, then stage the new site files.
- **`/atlas export [kml|geojson|both]`** — `python3 .claude/skills/atlas/export.py <root> <canon> [both]`.
  Writes `atlas/atlas.kml` + `atlas/atlas.geojson`. Hard-stops on an unknown
  category — surface the list, stop, ask the user to add them to the seam.
- **`/atlas key`** — `python3 .claude/skills/atlas/render_key.py <canon>` to show
  the KML styles + the INDEX legend the color key renders to.
- **`/atlas index`** — regenerate the `atlas/INDEX.md` dashboard: counts by
  category (the legend, via `render_key.legend_md`) + the health block
  (color-disagreements from `provenance.original_color_rgb` vs the palette,
  staged-unknown categories, provisional/past-cadence if the domain adds the clock).
- **`/atlas list [category|near|bbox]`** — read-only roster/filters. Full spatial
  queries (`near`/`bbox`/`region`) land in v0.2.0.

## What NOT to do

- Don't hand-compute KML colors or hand-edit 1300 rows — call the converters.
- Don't add a category to a site without adding it to the seam (export will refuse).
- Don't store a marker color on a site (it is derived); don't drop an unmapped
  column (it goes to `extended`); don't invent `alt: 0` for a missing altitude.
- Don't auto-commit; don't auto-merge duplicates; don't recycle an id.
- Don't build the verification clock / rivalry / sightline registry / survey axis
  here — those are the consuming domain's overlays.

## Done when

- New/imported sites are valid files under `atlas/sites/<block>/`, staged not
  committed; staged categories reported; near-duplicates surfaced.
- `atlas/atlas.kml` + `atlas/atlas.geojson` regenerate cleanly (no unknown
  category), and a `import → export → re-import` is a fixed point.
- The human reviews and commits.
