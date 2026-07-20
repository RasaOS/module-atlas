# CHANGELOG — `rasa.module.atlas`

Reverse-chronological. Each entry is a version bump.

---

## 0.4.0 — 2026-07-19

### Toggleable geometry layers — see markers only, with one checkbox

- A KML export now groups features into three top-level folders — **`Markers` / `Lines` /
  `Areas`** — so Google Earth's Places panel can switch each geometry layer on and off
  independently (uncheck Lines + Areas to see markers only). Folders ship `<open>0</open>`
  so a 1,000-feature Places tree stays tidy.
- **The round-trip is preserved.** Each layer folder carries an `atlas:layer` `<Data>` tag,
  and the importer treats a so-tagged folder as a VIEW wrapper — walking through it without
  adding its name to `folder_path`. Detection is by the machine tag, **not by folder name**,
  so a genuine source folder called "Lines" is still preserved verbatim. Without this, a
  re-import would inject "Markers" into every record and break the fixed point.
- Bucketing is defensive: any unrecognised `geometry_type` falls back to the `Markers`
  layer, so a site can never be silently dropped from the export.
- Gate extended: asserts all three layer folders are emitted and tagged, and that no layer
  name leaks into any re-imported `folder_path`. `bin/check-manifest` + round-trip gate GREEN.
- GeoJSON is unchanged — it has no folder concept; filter on the `geometry_type` property.

## 0.3.0 — 2026-07-19

### Live Google Earth view — a NetworkLink loader + a re-export-on-save watch loop

- **`atlas-live.kml`** — a KML export now also writes a companion Google Earth
  **NetworkLink** loader that re-reads `atlas.kml` every 2s. Open it once in Google
  Earth **Pro** and a `/atlas export` appears without re-importing; the camera view is
  preserved (`flyToView=0`). The loader's `href` is **relative** (`atlas.kml`) so it is
  portable and hardcodes no path; the machine-absolute path is written into its
  `<description>` as a fallback for GE builds that don't resolve the relative link. It is
  the one *generated* artifact allowed to name a local path, and only inside a deployment.
  Subject-neutral (the module ships zero subject content).
- **`/atlas watch [interval]`** (`content/skills/atlas/watch.py`) — a foreground,
  stdlib-only loop that re-runs the exporter whenever a site record or the color-key seam
  changes, so the live view updates hands-free. **No self-trigger:** exports land in the
  atlas root while the watch is on `sites/` + the seam. A failed export (e.g. an unknown
  category) is reported and does not stop the loop; fix the seam and the next save
  re-exports. Debounced so a burst of saves collapses to one export.
- **Watcher hardening** (adversarial-review pass): change detection is a **content
  digest**, not `(count, max-mtime)` — so a same-second second edit (this workspace's
  HFS/USB has 1-second mtime) and an mtime-preserving restore are both caught, while a
  pure `touch` is correctly ignored. The baseline is armed on the **pre-export** snapshot
  so an edit that lands *during* an export re-fires instead of being swallowed. The
  `interval` arg is validated (non-numeric / ≤0 → default with a warning, never a
  busy-loop or a raw traceback); Ctrl-C during the initial export exits cleanly; and
  output is line-buffered so status streams even when piped. The loader's empty-map hint
  now names the `Sites (auto-refresh)` node that actually carries the editable `<Link>`,
  and the absolute-path fallback is emitted via `pathlib.as_uri()` (a valid `file://` URI
  on POSIX and Windows).
- Gate extended: the round-trip fixture now asserts the loader is emitted, is well-formed
  XML, and points at the relative `atlas.kml`; and that `watch.signature()` flips on a
  record change (drives the auto-export). `bin/check-manifest` + `test/roundtrip_test.py`
  GREEN. Requires Google Earth Pro desktop — local network links are unsupported in
  Google Earth Web.

## 0.2.0 — 2026-07-19

### Feature geometry — the atlas is now a point/line/polygon catalog (not point-only)

- A site record gains two additive fields — **`geometry_type`** (`point` | `linestring`
  | `polygon`) and **`geometry`** (the full coordinate string) — so a LineString keeps
  every vertex (with a mid-vertex marker) and a Polygon keeps its outer ring (with a
  centroid marker), instead of being flattened to a single dot. Points are unchanged
  (`geometry_type: point`, no `geometry`).
- **The KML importer** now reads `LineString` and `Polygon` (not just `Point`);
  **the exporter** emits real `<LineString>`/`<Polygon>` KML and GeoJSON
  `LineString`/`Polygon` geometry; **the color key** now carries `LineStyle` +
  `PolyStyle` (same category colour) so lines and areas render coloured, and GeoJSON
  gains `stroke`/`fill`. CSV gains optional `geometry_type`/`geometry` columns.
- The round-trip fixed-point fixture now covers a LineString + a Polygon (geometry
  survives import → export → re-import); a truly geometry-less placemark is still
  skipped. `bin/check-manifest` + `test/roundtrip_test.py` GREEN.
- Motivated by ingesting the Proverbs global-sites KML (167 lines + 61 polygons that
  the v0.1 point-import had flattened). Additive, backward-compatible: existing point
  records read/round-trip unchanged.

## 0.1.1 — 2026-07-19

### Doc reconciliation — the `aln-NNNN` sightline registry moves to `rasa.module.sightlines`

- The cross-site sightline registry that v0.1.0's "what the consuming domain adds"
  section reserved as `aln-NNNN` on the domain side is now **`aln-NNNNNN`, owned by
  the new `rasa.module.sightlines`** (Model A: a fit-epoch/window is an engine output,
  so record and compute cannot straddle an ownership boundary). `atlas-rules.md`,
  `BUILD_PLAN.md`, and the `rasa.json` design note are repointed; the domain now
  overlays only its `[D]` re-computation cadence over that module. **No behavioural or
  installed-surface change** — atlas never implemented the registry.

## 0.1.0 — 2026-07-18

Initial ship — a **portable geospatial catalog** (greenfield, author-requested;
the first of a latent catalog family). Unlike `module.theory` (which deferred its
driver), this ships the `/atlas` driver + working converters at v0.1.0, because
the color-keyed KML round-trip *is* the ask.

### The capability

- **Catalog places** — one light markdown file per site,
  `atlas/sites/<id-block>/site-NNNNNN.md`, sharded on the id (never by category).
  `site-NNNNNN` id (immutable, fixed 6 digits, never recycled); canonical
  `lon/lat/alt` stored once (lon first); `category` field = the color-key join; a
  verbatim `provenance` block + an `extended` overflow bag for lossless import.

### Design decisions locked (four-design / two-judge review)

- **File-per-site, sharded on the id.** Directory-per-category rejected
  (reclassification would break every link); a single data-file rejected (a cell
  can't hold prose links / `@path` / a provenance excerpt).
- **`site-NNNNNN` id** — a located record is *cited by id like a source*, not
  *linked by slug like a topic*; zero-padded to a **fixed 6 digits** (1M headroom)
  so growth never renames a file or an `@path`.
- **Losslessness** = canonical facts once + derived styling + verbatim provenance
  + an `extended` overflow bag; proven by an `import → export → re-import`
  fixed-point fixture (the release gate).
- **Deterministic Python converters** ship under `content/skills/atlas/` (blessed
  to ship runnable code inside `content/skills/`; covered by the directory-mirror
  ancestor rule — no new manifest slots).
- **Unknown categories are STAGED on import** (a bulk load never halts) — the
  hard-stop fires at export/legend.
- **INDEX is a dashboard** (counts + legend + health), never a 10k-row table — the
  generated `atlas.kml`/`atlas.geojson` are the real rollup.
- **Coupling to siblings is SOFT** (`requires.elements[]` empty): graduate → topic,
  theory-evidence, cite `src`/`lib`, describe with a term.
- **The four longitudinal/cross-site disciplines** (verification clock default-OFF,
  contested geography, the `aln-NNNN` sightline registry, the dated survey axis)
  are ADDED BY the consuming domain (`rasa.domain.proverbs`), never here.
- **A general `module.catalog` base stays LATENT** — extracted only when a second
  consumer (a minerals property-catalog) proves the pattern.

### Ships

- **Spine** — `content/atlas-rules.md` → `.claude/atlas-rules.md` (file-replace):
  the node, the id scheme, the losslessness contract, the color key + round-trip,
  the INDEX-as-dashboard convention, the soft cross-family seams, the one hard-stop.
  Distinct filename — never collides with `research-rules.md`/`theory-rules.md`.
- **Template** — `content/atlas-template/site.md` → `.claude/atlas-template/`
  (directory-mirror): the single-file per-site skeleton (a justified divergence
  from the folder-node templates).
- **Skills + converters** — `content/skills/` → `.claude/skills/` (directory-mirror):
  the `/atlas` driver + the deterministic `import.py`/`export.py`/`render_key.py`/
  `lib.py` (stdlib only), plus the inherited house skills `/sync`, `/promote`,
  `/whoami`.
- **Seam (color key)** — `seed/atlas-canon.md.template` → `.claude/atlas-canon.md`
  (skip-if-exists): the category→color taxonomy; export hard-stops on an in-use
  category absent here.
- **Index** — `seed/atlas/INDEX.md.template` → `atlas/INDEX.md` (skip-if-exists):
  the dashboard (counts + legend + health); seeding creates the `atlas/` root.
- **Author docs** — `content/README.md` + `content/BUILD_PLAN.md` (opt-in).
- Canon-required files: Apache-2.0 LICENSE, `bin/init`, `bin/check-manifest`,
  SHA-stamped lockfile template, `.gitignore`.

### Notes

- Forked from the `rasa.module.theory` / `rasa.module.research` house pattern.
- Converters are standard-library only (KML/KMZ/CSV native; XLSX best-effort via
  openpyxl, else export to CSV).
- Soft cross-references to `rasa.module.research` (graduate-to-topic),
  `rasa.module.theory` (alignment evidence), and `rasa.module.jobs` (re-verify
  sweep). None hardened into `requires.elements[]`.
- `bin/check-manifest` GREEN; `bin/init` smoke-tested; round-trip fixed-point
  fixture green. Built locally; not yet pushed. Target repo: `RasaOS/module-atlas`.
