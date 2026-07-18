# `rasa.module.atlas` — Specification & Design Record

**Status:** v0.1.0 = the spine + seam + template + the `/atlas` driver + the
deterministic converters + the round-trip fixed-point fixture. This is the
author-time design record behind the installed spine (`content/atlas-rules.md`).

---

## Why this module exists

Requested directly by the workspace author (2026-07-18): keep track of all the
historical and interesting spots around the world (1300 in a spreadsheet + KML
Google Earth files today, growing to "the largest personal library of sites"),
with a **color-coded category key** so markers are colored by topic. It is the
first of a planned catalog family (minerals, and structurally a document library
and a lexicon later reuse the pattern).

Greenfield / author-requested (like `module.research`), so the extract-after-proof
gate does not apply. And unlike `module.theory` (which deferred its driver to
prove the spine), atlas **ships its `/atlas` driver at v0.1.0** — the color-keyed
round-trip is the ask, 1300 sites are waiting, and a spine with no importer is
inert. The converters are deterministic, so shipping them now is safe.

## The boundary — a site is not a research topic

Settled by a four-design / two-judge review:

> A **site** is a *located record* — one of potentially thousands, that you point
> at on a map. A **research topic** is a *sustained investigation* — few, heavy, a
> whole folder.

**Discriminator:** *point at it on a map, one of many → site (here); a
question-driven investigation → a `module.research` topic.* A site **graduates**
to a topic when it earns sustained study (a disputed dating, a contested
alignment) — a pointer, not a move.

## Node granularity — file-per-site, sharded on the id

The load-bearing bet. One markdown file per site,
`atlas/sites/<id-block>/site-NNNNNN.md`; `category` is a field, never a folder;
sharding is classification-free (blocks of 1000, on the id).

Alternatives rejected:
- **Directory-per-category** — reclassifying a "mound" to a "platform" would be a
  physical move that breaks every `@path` and rewrites history.
- **One big CSV/NDJSON** — a cell cannot hold prose `[[links]]`, an `@path`, or a
  `## Provenance excerpt`, so every cross-family seam has nowhere to live. That is
  a gazetteer; this is a catalog whose entries cite, feed, and graduate.

File-per-site survives scale because frontmatter is the greppable/queryable layer,
the body holds what a row can't, a bare site degrades to frontmatter-only
(near-row weight), and one edit is one small file (clean git-diff/blame).

## The `site-NNNNNN` id scheme

A located record is *cited by id like a source* (`src-NNNN`), not *linked by slug
like a topic* (`RT-`/`TH-`) — so the prefix is `site-`, not a slug. **Zero-padded
to a fixed 6 digits** (1M headroom), fixed once: widening would rename every file
and every `@path`. Corpus-unique, `highest+1`, never recycled.

This yields the corpus-consistent split: `[[slug]]` names investigable nodes
(topics, theories, lexicon terms); `site-NNNNNN` / `@path` cites located records.

## Losslessness — the fixed-point contract

`import → export → re-import` is a fixed point on
`{id, name, category, lon, lat, alt, folder_path, sources, extended, description}`
(not on `provenance`, which records where a given import came from). Achieved by a
four-part split: canonical facts stored once, derived styling, a verbatim
`provenance` block, and an `extended` overflow bag (no column dropped). On export
the `entry_id` + `extended` ride in KML `ExtendedData` / GeoJSON `properties`, so
a re-import re-joins rather than duplicates. **The fixture that proves this is the
release gate** — see `test/roundtrip_test.py`, which fuzzes a hard fixture
(unicode/quoted/comma names, multi-level folders with `&`/`<>`, `alt` present vs
absent, multi-token sources, a `]]>` in a description, a `"null"` name) and
asserts both the pristine fixed point and merge-preservation of authored fields.

## The color key

The category→color taxonomy is the project-owned `.claude/atlas-canon.md` seam,
authored once as `#RRGGBB`. Both encodings are pure functions of that one value
(`rgb_to_kml` → `aabbggrr`; GeoJSON `marker-color` verbatim). The module's **one
hard-stop**: export/legend refuse to derive a color for an in-use category absent
from the seam — inventing a category is the one inference the module won't make.
Palette discipline for 15–40 categories: explicit table (never hash-of-name),
never recycle a key, hue=family + lightness=member past ~8–12 hues.

## Deterministic converters (the fleet-precedent decision)

Lossless conversion of 1300 rows and `aabbggrr` arithmetic must be **code, not LLM
prose** (the review's top risk). So `content/skills/atlas/` ships runnable Python
(`lib`/`import`/`export`/`render_key`, standard-library only). The author blessed
shipping executable code inside `content/skills/` for the fleet; it is covered by
the existing `directory-mirror` ancestor rule (no new manifest slots, no new
install policy). XLSX is best-effort (export to CSV is the reliable path).

## Cross-family seams (soft)

All reuse `@path`/`[[slug]]`/`tags`/`related` verbatim; `requires.elements[]` stays
empty. A site graduates to a research topic (`graduated_to:`); its alignment is
evidence for a theory prediction (the measurement stays on the site, the theory
records only the bearing — theory's iron rule); it cites `src`/`lib` ids; it is
described with lexicon terms; it links geology. Drop any sibling → the catalog
stays valid, the seam just falls silent.

## What the consuming domain adds (not here)

`rasa.domain.proverbs` layers four disciplines additively: a verification clock
(`last_verified:`, default OFF — stone circles don't move), contested/held-open
geography, a cross-site sightline registry (`aln-NNNN`, owned by no site — the
home for archaeoastronomical alignment), and a dated survey/observation axis.

## Skills

- **v0.1.0** — `/atlas` (`new`, `import`, `export`, `index`, `key`, `list`) + the
  inherited house skills (`/sync`, `/promote`, `/whoami`).
- **v0.2.0 (behind the gate)** — the O(n) spatial queries (`near`/`bbox`/`region`),
  `graduate` polish, and `module.catalog` extraction **only when a second consumer
  (minerals) proves the pattern** (this family's first legitimate
  `requires.elements[]`).

## Version plan

- **v0.1.0 (this)** — full working module: spine + seam + template + `/atlas` +
  converters + the round-trip fixture. `bin/check-manifest` GREEN; `bin/init`
  smoke-tested. Local commit + tag; push is the author's.
- **v0.2.0** — spatial queries, `/atlas index` health polish, seam hardening after
  the first real 1300-site ingest.
- **v1.0.0** — node shape + id scheme + seam + round-trip contract locked after two
  real verticals run the pipeline unchanged.

## Suite roadmap (recorded, not committed)

The catalog family stays latent. `module.catalog` (the general typed-entity base)
extracts on the **second consumer** (a minerals property-catalog), whose two
divergences from atlas — a slug-native lexicon id and library's *inverted* citation
role (it mints `lib-NNNN` rather than citing it) — are invisible from atlas alone
and would bake a wrong base if guessed now. `module.library` and `module.lexicon`
follow the same extract-after-proof discipline.

## First consumer (natural)

- **`rasa.domain.proverbs`** — the reference consumer; requires this module,
  layers the four disciplines, and ingests the author's 1300+ sites into a
  dedicated `proverbs-corpus` deployment.
