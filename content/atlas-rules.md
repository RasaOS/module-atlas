# Atlas Rules

The portable geospatial-catalog discipline that `rasa.module.atlas` installs at
`.claude/atlas-rules.md`. It covers the one thing the module exists to do —
**catalog places**: a light, greppable, color-keyed record per located site,
scaling to thousands — plus the id scheme, the losslessness contract, the
category→color key, the KML/GeoJSON round-trip, and the boundary against the
research substrate it sits beside. **Read this file when adding a site, importing
a KML/spreadsheet, exporting the map, choosing a category, or graduating a site
to a research topic.**

This file is **Element-owned** — it refreshes on upgrade. It deliberately does
**not** decide the one thing that varies per project:

- **The category→color taxonomy** (which categories exist, and what color each
  one is).

That lives in the project-owned **`.claude/atlas-canon.md`** (the atlas analogue
of `research-canon.md`'s `promotion_target` and `theory-canon.md`'s
`standing_criteria`). This file references the seam; it hardcodes none of it.
**Export and the legend hard-stop** if an in-use category is absent from the
seam. Inventing a category — and therefore a color — is the one inference this
module refuses to make on its own authority.

---

## The model in one screen

A **site** is a *located record*: a place with coordinates, a category, and a
provenance. It is **not** a research topic (a sustained investigation) — it is
one of potentially thousands of light entries, closer to a source record than to
a topic. The module gives each site **one small file**, keeps them **sharded by
id**, renders them to a **color-coded map**, and couples them — softly — to the
research topics, theories, and sources they touch.

```
   THE SITE NODE (light, thousands)          THE COLOR KEY + ROUND-TRIP
   ────────────────────────────────          ──────────────────────────
   atlas/sites/<id-block>/                    .claude/atlas-canon.md
     site-000042.md   (one file per site)       category → #RRGGBB  (authored once)
       frontmatter: id, name, lon/lat/alt,           │
         category, provenance, extended…             ├─► KML   <IconStyle><color> aabbggrr
   atlas/INDEX.md   (dashboard + legend)              └─► GeoJSON properties.marker-color
   atlas/atlas.kml · atlas/atlas.geojson  ← the real at-a-glance rollup (generated)

   import (KML/KMZ + spreadsheet) → sites → export (color-styled KML + GeoJSON)
   must be a FIXED POINT: import → export → re-import == identity   (the release gate)
```

---

## What a site is — and is not a research topic

**The discriminator:** *is it a located record, one of many, that you point at on
a map? → site (here). Is it a sustained, question-driven investigation? → a
`rasa.module.research` topic.*

- A **research topic** owns a whole folder (README + log + findings + sources +
  open-questions) for one deep line of inquiry. Few, heavy.
- A **site** is one light file: where a place is, what it is, on whose authority.
  Many, light.

A site **graduates** to a research topic when it earns sustained study (a
disputed dating, a contested alignment). Graduation is a pointer, not a move —
see the cross-family seams. Do not open a research folder for every site; do not
flatten a real investigation into a catalog row.

## The site node

One site is **one markdown file**: `atlas/sites/<id-block>/site-NNNNNN.md`.
Frontmatter is the uniform, greppable, converter-owned layer; the body holds what
a spreadsheet row structurally cannot (prose, `[[links]]`, a provenance excerpt).

### Sharding — classification-free, on the id

Sites are bucketed into **id-blocks of 1000** — `atlas/sites/000000-000999/`,
`atlas/sites/001000-001999/`, … — purely by id, **never by category**. This keeps
any one directory small at 10⁴+ entries without ever forcing a classification
decision into the filesystem. **Category is a frontmatter field, never a
folder**: reclassifying a "mound" to a "platform" is a one-line edit, not a file
move that would break every `@path` and rewrite history.

### The `site-NNNNNN` id scheme

- **`site-` prefix** — a site is a *located record cited by id* (like a source
  `src-NNNN`), not a *named node linked by slug* (like a topic `RT-` or a theory
  `TH-`). References point at the **id / `@path`**, never at the mutable name.
- **Zero-padded to a fixed 6 digits** (1,000,000 headroom), **fixed once**.
  Widening the width later would rename every file and every `@path` — so the
  width never changes. (If a corpus could plausibly exceed 1M sites, choose the
  width at first install and hold it forever.)
- **Corpus-unique, `highest + 1`, never recycled.** A retired site keeps its id;
  ids are not reused.

This yields the corpus-consistent split: **`[[slug]]`** names investigable nodes
(topics, theories, lexicon terms, named minerals); **`site-NNNNNN` / `@path`**
cites located records. The human name lives in the correctable `name:` field.

### Frontmatter contract

```yaml
---
id: site-000042            # [M] IMMUTABLE — assigned once (highest+1), never recycled; filename == id
name: "Spring 12"          # [M] correctable human label; "" is legal (an unnamed feature)
category: water-source     # [M] the ONE classifier + the color-key join (a field, never a folder)
lon: -119.417900           # [M] the representative MARKER point — full precision, LON FIRST
lat:  36.778300            # [M]   (a point: the point; a line: its mid-vertex; a polygon: its centroid)
alt:  0                    # [M] metres; null if the source has none (never invent 0)
geometry_type: point       # [M] point | linestring | polygon  (v0.2 — a feature catalog, not point-only)
geometry:                  # [M] the FULL shape for a line/polygon: "lon,lat lon,lat …"; empty for a point
coord_precision: exact     # [M] exact | approximate | rough | unknown — intrinsic to a located record
status: active             # [M] active | provisional | retired: "<reason>"   (nothing is deleted)
tags: [perennial]          # [M] reused substrate layer — flat matching / discovery
related: [north-complex]   # [M] reused substrate layer — flat, UNTYPED slugs (the [[..]] mirror)
sources: [src-0114]        # [M] GLOBAL source ids, cited directly (no per-site local shelf — see below)
folder_path: ["North sector"]   # [M] the KML <Folder> hierarchy, preserved so it round-trips
graduated_to:              # [M] [[topic-slug]] once the site becomes a research topic; absent until then
provenance:                # [M] VERBATIM — the round-trip fidelity guarantee
  source_file: north-sector.kmz
  source_type: kmz         # kml | kmz | csv | xlsx | manual
  source_ref: "Placemark#Spring 12"      # or "catalog.xlsx!Sheet1!R42"
  imported_at: 2026-07-18T14:02:00Z
  original_style_url: "#waterStyle"       # as-seen, verbatim
  original_color_kml: "ff779e1b"          # observed KML color — kept so a source color that
  original_color_rgb: "#1b9e77"           #   DISAGREES with the palette is never silently lost
extended:                  # [M] OVERFLOW BAG — every unmapped <Data>/column, verbatim (no column dropped)
  flow_rate_lpm: "12"
# cadence: none            # [D] verification clock — added by a consuming domain; DEFAULT OFF
# last_verified: 2026-07-18 # [D]
---

# Spring 12 · site-000042

## Description
<!-- What is at this place, on whose authority. Corrected if a source is wrong. -->

## Provenance excerpt
<!-- Verbatim source text backing each cited claim (no claim without provenance). -->

## Geology
<!-- Soft mineral seam; present only if relevant: related: [[travertine]]. -->
```

Only fields marked **[M]** are the module's; **[D]** fields are added by a
consuming domain and are inert without it. A site cites the **global** source id
directly and keeps **no per-site local `[S1]` shelf** — a deliberate divergence
from a research topic, because a site is *not* a self-contained investigation.

## Losslessness — the round-trip fidelity guarantee

The import→export→re-import cycle must be a **fixed point** on the stable field
set — `id`, `name`, `category`, `lon`, `lat`, `alt`, `folder_path`, `sources`,
`extended`, `description` — but **not** on `provenance` (whose `imported_at` and
`source_file` legitimately change when you re-import the exported `atlas.kml`).
That is achieved by a four-part split, and
nothing outside it may carry load-bearing data:

1. **Canonical facts, stored once** — `lon/lat/alt`, `name`, `category`. The one
   true copy; styling is *derived* from them, never stored redundantly.
2. **Derived styling** — the marker color is computed from `category` + the seam
   at export; it is never a stored field that could drift.
3. **Verbatim provenance** — the `provenance` block preserves the source file,
   ref, and *observed* color/style exactly as seen, so a source color that
   disagrees with the palette is recorded, not lost.
4. **The `extended` overflow bag** — every KML `<Data>` element and every
   spreadsheet column the schema does not map lands here verbatim. **No column is
   ever dropped.**

On export, the site's `id` (as `entry_id`) and the whole `extended` bag ride in
the KML `ExtendedData` / GeoJSON `properties`, so a **re-import re-joins to the
same site** instead of creating a duplicate.

**Re-import merges; it does not overwrite.** When a site already exists, only the
stable (source-authoritative) fields above are rewritten — everything an author
added and the source does not carry (`status`, `tags`, `related`,
`graduated_to`, `coord_precision`, and any `[D]` domain overlay such as
`cadence:`/`last_verified:`) is **preserved**. So re-importing an updated KML
never un-retires, un-graduates, or un-tags a real site, and the fixed point holds
on enriched sites, not just pristine ones. That is what makes "lossless" provable
rather than aspirational — and the proof is a committed round-trip fixed-point
fixture (`test/roundtrip_test.py`, the release gate).

## The color key

The category→color taxonomy is the seam's job (`.claude/atlas-canon.md`), authored
**once as `#RRGGBB`**. Both encodings are **pure functions of that one value**, so
a color change is a one-line edit that propagates to every marker in every format:

```
KML   <IconStyle><color>          = aabbggrr(cat.color)   # alpha + blue + green + red, REVERSED
GeoJSON properties["marker-color"] = cat.color             # web order, verbatim
INDEX legend swatch                = cat.color
```

`aabbggrr("#1b9e77")` → `ff779e1b`. One shared `<Style>`/`<StyleMap>` is emitted
per category and every placemark of that category references it by `styleUrl`
(single definition, not repeated per marker).

**Palette discipline** (for ~15–40 categories): assign colors by an explicit
table, **never a hash of the name** (hashing re-jitters every color on a rename).
**Never recycle a category key** (same rule as ids). Past ~8–12 distinct hues, add
a second channel — **hue = family, lightness = member** (`hazard-fire` /
`hazard-flood` / `hazard-slide` as deepening reds) and `symbol` as a third —
rather than more near-identical hues. Start from a proven categorical palette
(ColorBrewer Dark2 / Okabe–Ito) and freeze the order.

**The one hard-stop:** export and the legend **refuse to derive a color for an
in-use category that is absent from the seam.** Add it to `atlas-canon.md` first.

## KML / spreadsheet round-trip

The conversions are **deterministic Python** shipped under
`.claude/skills/atlas/` (`import.py`, `export.py`, `render_key.py`, `lib.py`),
orchestrated by `/atlas` — **not** LLM prose. `aabbggrr` arithmetic and
lossless conversion of thousands of rows must be code, or they silently drift.

**Import** (`/atlas import <file>`):
- KMZ → unzip, take the first `doc.kml`. KML → walk `Document → Folder* →
  Placemark`: `<name>`, `<description>`, `<coordinates>` (**lon,lat,alt — lon
  first**), `styleUrl`, `ExtendedData/Data*`, enclosing folder names →
  `folder_path`. Spreadsheet → map `name/lon/lat/alt/category/description/sources`
  columns; **every leftover column → `extended`**.
- Category ← an explicit `category` field if present, else resolve
  `styleUrl`/observed `<color>` to the nearest seam category. **Record the
  observed color in `provenance.original_color_*` regardless.**
- **Unknown category → STAGE, do not halt.** Write the site with its observed
  category preserved and add it to a "categories to add" report. A bulk 1300-row
  load never stalls; the hard-stop is at export, not mid-import.
- Assign `site-NNNNNN` (`highest + 1`); **surface near-duplicates** (name +
  proximity) for a human decision — never auto-merge. Write one file per
  placemark/row from the template; **stage, never auto-commit.**

**Export** (`/atlas export [kml|geojson]`):
- **KML** — `render_key` emits one `<Style>`/`<StyleMap>` per category;
  placemarks are regrouped into their `folder_path` tree, each with
  `<styleUrl>#cat-<category>`, coords `lon,lat,alt`, and `ExtendedData` carrying
  `entry_id` + category + `extended` (so re-import re-joins).
- **GeoJSON** (RFC 7946, WGS84, no `crs` member) — a `FeatureCollection`; each
  geometry `[lon,lat,alt]`; `properties` carries `name`, `category`,
  `marker-color` (from the palette), `entry_id`, and the `extended` bag
  (simplestyle-spec, honored by GitHub/Mapbox).
- **Hard-stop** on any in-use category absent from the seam.

## The INDEX — a dashboard, not a table

`atlas/INDEX.md` is **not** a per-site table (a 10k-row markdown table is
unreadable and undiffable). It leads with **counts + the color legend + a health
block** (color-disagreements, staged-unknown categories, provisional-past-cadence
if the domain adds the clock). The generated `atlas/atlas.geojson` and
`atlas/atlas.kml` are the real at-a-glance rollup — you browse places on a map,
not in a table. If a grep roster is wanted, keep it a **separate**, generated,
id-sorted file so opening and diffing stay sane.

## Geo-queries (v0.2.0)

`near <lon,lat> <km>`, `bbox`, `region <polygon>`, `category <cat>` are O(n)
plain-file scans with a bounding-box pre-filter (haversine for `near`;
antimeridian-aware bbox; ray-cast for polygons) — fine to ~10⁵ points. If a corpus
outgrows that, the escape hatch is a geohash/S2 or SQLite R-tree index over the
clean numeric `lon`/`lat` the node already stores — an index, not a model rewrite.
Shipped in v0.2.0; the round-trip is the v0.1.0 deliverable.

## Cross-family seams (soft, present-if-mounted)

All reuse the substrate's three link layers **verbatim** (`@path`, `[[slug]]`,
`tags:`/`related:`). Atlas adds **no new link syntax** and ships **no `/xref`** —
`rasa.module.research`'s `/xref` traverses site bodies when mounted.
`requires.elements[]` stays **empty**; every seam degrades gracefully.

| Seam | Direction | How |
|---|---|---|
| **Graduate → research topic** | a site earns sustained study | `graduated_to: [[topic-slug]]`; the topic cites back `@atlas/sites/<block>/site-NNNNNN.md` |
| **Theory evidence** | a site's alignment supports/challenges a `P#` | the theory's `predictions.md` cites `@atlas/sites/<block>/site-NNNNNN.md`; the *measurement* stays on the site, the theory records only the bearing |
| **Cite a source** | a site rests on a document | `sources: [src-0114]` (or a future `lib-NNNN`); atlas coins no source id of its own |
| **Describe with a term** | a site is a "menhir", a "tell" | `tags: [term-slug]` + `[[term-slug]]` in prose (lexicon owns the term) |
| **Geology** | a site's stone/mineral | `## Geology` body / `related: [[mineral-slug]]` |

Drop any sibling and the atlas stays a **valid standalone catalog** — the seam
just falls silent (`graduated_to:` dangles, a `sources:` id resolves to nothing),
never breaking the record.

## What a consuming domain adds — NOT built here

A domain that requires this module layers longitudinal and cross-site discipline
**on top**, additively (the `rasa.domain.proverbs` overlay pattern, transposed
from time to place). These are the domain's, not the module's:

| Discipline | Added by the domain, over this module |
|---|---|
| A **verification clock** | `cadence:` + `last_verified:`, **default OFF** (a stone circle does not move; opt-in for live/threatened records) |
| **Contested / held-open geography** | when two surveys give different coordinates or two authorities give different datings, both are held open rather than the last editor silently picking one |
| A **cross-site sightline registry** | `aln-NNNNNN`: **owned by `rasa.module.sightlines`** (not the domain — its fit-epoch/window are engine outputs; the domain overlays only `[D]` re-computation cadence). An alignment relates N sites and is owned by none; a structure-to-star sightline and its computed epoch. |
| A **dated survey/observation axis** | dated observations bearing on N sites ("1965 survey recorded these 12", "2024 LIDAR revealed 3 features") |

If a deployment wants these, it mounts a domain that provides them. Do not build
them into the module.

## Conventions (mandatory)

- **Ids are identity.** `site-NNNNNN`, immutable, fixed width, never recycled.
  Renaming a place edits `name:`, never the id. References use the id / `@path`.
- **Lon before lat, always.** KML, GeoJSON, and the frontmatter all store
  `lon,lat[,alt]` in that order — the commonest geospatial bug is swapping them.
- **Category is a field, never a folder.** Sharding is on the id only.
- **One canonical copy of each fact.** Coordinates and category are stored once;
  color and styling are *derived* at export, never stored.
- **No column dropped.** Every unmapped source field lands in `extended`
  verbatim; the observed color/style lands in `provenance`.
- **Never invent a category or a color.** Export hard-stops on an unknown
  category; add it to the seam first.
- **Never delete a site — retire it.** `status: retired: "<reason>"`; the id is
  kept and never reused.
- **Coordinates carry a precision.** `coord_precision` is intrinsic; never invent
  `alt: 0` for a missing altitude (use `null`).
- **Stage, never auto-commit.** Import and export stage files; the human commits.
- **The round-trip is a fixed point.** import → export → re-import is identity;
  the fixture proves it before any tag.

## Soft cross-references to sibling modules (degrade gracefully)

Present-if-mounted; never hardened into `requires.elements[]`:

- **`rasa.module.research`** — a site graduates to a topic; research's `/xref`
  traverses site bodies.
- **`rasa.module.theory`** — a site's alignment is evidence for a theory
  prediction (the archaeoastronomy case).
- **`rasa.module.jobs`** — a scheduled "re-verify provisional/threatened sites"
  sweep is a natural `job.toml` (once a domain adds the `cadence:` clock).
- A future **`module.catalog`** (the extracted base) / **`module.library`** /
  **`module.lexicon`** are recorded as *future considerations only* — this module
  is self-contained and coins no id it does not own.
