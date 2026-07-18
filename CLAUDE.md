# CLAUDE.md — `rasa.module.atlas`

> **Who you are (SA-025).** `rasa.module.atlas` — the RasaOS module for a light, color-keyed geospatial catalog of places. Substrate: **RasaOS**; role: **module**. On install `bin/init` renders this into `.claude/rasa-identity.md`; `/whoami` composes the full identity with the project's deployment layer.

Per-repo working contract for Claude sessions opened inside this folder.
Extends `~/.claude/CLAUDE.md` and the workspace `rasa.tenant.rasaos` tenant
contract; does not override them. (Referenced by identity, not filesystem path.)

## What you are when you're in this folder

You are working on **`rasa.module.atlas`** — a `module`-kind Element: a portable
geospatial catalog that holds thousands of light, color-keyed located records.
Sibling to `rasa.module.research` (deep investigations; a site graduates to a
topic) and `rasa.module.theory` (patterns; a site's alignment is theory evidence).

You are working on **the module — the method + machinery — not a site corpus.**
If you find yourself cataloguing an actual place (a real pyramid, a real spring),
stop — that belongs in a deployment's `atlas/`, never in this Element. The one
exception is an obviously-placeholder example in a doc.

## The load-bearing ideas

**1. A site is a light located record, not a research topic.** Discriminator: *a
place you point at on a map, one of many → site; a sustained investigation →
`module.research` topic.* A site is one file; a topic is a folder. Don't inflate
a site into a topic or flatten a topic into a site.

**2. File-per-site, sharded on the id, category is a field.** `site-NNNNNN`
(immutable, fixed 6 digits, never recycled), `atlas/sites/<id-block>/`. Never a
directory-per-category (reclassification would break every link); never a single
mega data-file (a cell can't hold prose links / `@path` / a provenance excerpt).

**3. Losslessness is the point.** Canonical facts stored once + a verbatim
`provenance` block + an `extended` overflow bag → `import → export → re-import` is
a fixed point (on `{id,name,category,lon,lat,alt,folder_path,sources,extended,description}`,
NOT provenance). The round-trip fixture is the release gate. Never drop a column;
never store a derived color.

**4. The color key is the seam, with one hard-stop.** The category→color taxonomy
is project-owned `.claude/atlas-canon.md`. Export/legend hard-stop on an in-use
category absent from it. Inventing a category (and a color) is the one inference
the module won't make.

**5. Conversions are deterministic Python, not prose.** `content/skills/atlas/`
ships runnable `import.py`/`export.py`/`render_key.py`/`lib.py` (stdlib only) —
blessed to ship code inside `content/skills/` (covered by the directory-mirror
ancestor rule). `aabbggrr` math and 1300-row conversion must be code. Keep them
stdlib-only; XLSX best-effort (CSV is the reliable path).

**6. The four overlays are the domain's, not ours.** The verification clock,
contested geography, the cross-site sightline registry (`aln-NNNN` — where
archaeoastronomical alignments live), and the dated survey axis are added by a
consuming domain (`rasa.domain.proverbs`). Don't build them here.

## Current status — v0.1.0 (ships the `/atlas` driver)

Ships the spine (`content/atlas-rules.md`), the color-key seam
(`seed/atlas-canon.md.template`), the single-file site template
(`content/atlas-template/site.md`), the seeded dashboard
(`seed/atlas/INDEX.md.template`), the `/atlas` driver + the deterministic
converters, and the inherited house skills. Unlike `module.theory` (which deferred
its driver), atlas ships `/atlas` at v0.1.0 — the color-keyed round-trip *is* the
ask. Spatial queries (`near`/`bbox`/`region`) wait for v0.2.0. `bin/check-manifest`
GREEN; round-trip fixed-point fixture green.

## Source of truth

- **Canon** (`rasa.tenant.rasaos` workspace `canon/`) — authoritative. Spec §6
  defines the `module` kind; ELEMENT_CONTRACT.md §7 the install policies.
- **`content/atlas-rules.md`** — the installed spine (the discipline).
- **`content/BUILD_PLAN.md`** — the spec + the round-trip contract + the version
  and latent-catalog-family plan.
- **`rasa.json`** — the formal declaration + install manifest.

## Don'ts

- **You are NOT the template, and NOT `module.research`/`module.theory`.** If this
  contract ever describes another Element, that's template-CLAUDE.md drift — flag it.
- **Don't do KML color math or row conversion in prose** — call the converters.
- **Don't invent a category or a color** (export hard-stops); **don't drop a
  column** (→ `extended`); **don't store a derived color**; **don't invent
  `alt: 0`** for a missing altitude (use `null`).
- **Don't build the verification clock / rivalry / sightline registry / survey
  axis here** — those are the consuming domain's overlays.
- **Don't add a heavy folder-per-site or a second link system.** Reuse
  `@path`/`[[slug]]`/`tags`; research's `/xref` traverses site bodies on co-mount.
- **Don't bump `contract_version`.** Stays `1.3.0` — the last LOCKED + published
  contract; authored to v1.4.0 rules, declaring 1.3.0 like the whole fleet.
  Migration is a coordinated `bin/lock-sequence`, never a per-element bump.
- **Don't `bin/init` this Element into itself.** `content/` is the source.
- **Don't push from the Cowork sandbox.** Local commit + tag only; the author
  pushes from their machine (workspace rule).

## How a version bump works

- **Patch** — wording/converter bug fix. **Minor (→0.2.0)** — spatial queries,
  `graduate` polish, seam hardening after a first consumer, a new optional field.
  **Major (→1.0.0)** — node shape + id scheme + seam + round-trip contract locked
  after two real verticals run the pipeline unchanged.

Each bump: edit `VERSION` + `rasa.json#version`, write a CHANGELOG entry, run
`bin/check-manifest` **and the round-trip fixed-point fixture**, commit + tag
`v<version>`. Update the workspace `elements/REGISTRY.md` + `elements/CHANGELOG.md`
(track #2) + a line in `canon/AUDIT.md`.
