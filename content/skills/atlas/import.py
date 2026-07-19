#!/usr/bin/env python3
"""
rasa.module.atlas — importer.  KML / KMZ / CSV / XLSX  ->  atlas/sites/<block>/site-NNNNNN.md

Usage:
    python3 import.py <atlas_root> <atlas_canon.md> <input_file> [<input_file> ...]

- Reuses `entry_id` from ExtendedData/columns when present (the re-join that makes
  the round-trip a fixed point); otherwise assigns highest+1.
- RE-IMPORT MERGES: if a site file already exists (same id), only the
  source-authoritative fields are overwritten; authored fields (status, tags,
  related, graduated_to, coord_precision) and any [D] domain overlay are preserved
  — a re-import never un-retires / un-graduates / un-tags a real site.
- Category from ExtendedData/column `category` if present, else resolved from the
  placemark's observed color against the seam, else STAGED (never halts a bulk
  load). Staged categories + near-duplicates are reported, not auto-resolved.
- A placemark with no coordinates/geometry is skipped and reported (atlas is a feature
  catalog). One bad input file is reported and skipped, not fatal.
- Writes one file per placemark/row. Stages files; the human commits.

Standard library only for KML/KMZ/CSV. XLSX is read best-effort via openpyxl if
installed; otherwise export the sheet to CSV first.
"""

import csv
import os
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402

_ID_RE = re.compile(r"^site-\d+$")


def _local(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _find(el, name):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _findall(el, name):
    return [c for c in el if _local(c.tag) == name]


def _text(el, name):
    c = _find(el, name)
    return (c.text or "").strip() if c is not None else ""


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.strip().lower()).strip("-") or "uncategorized"


def _safe_round(v):
    try:
        return round(float(v), 4)
    except (TypeError, ValueError):
        return None


# ---- KML ------------------------------------------------------------------

def _style_colors(doc):
    """Map style id -> observed IconStyle color (aabbggrr), incl. StyleMap 'normal'."""
    colors, maps = {}, {}

    def walk(el):
        for c in el:
            t = _local(c.tag)
            if t == "Style" and c.get("id"):
                icon = _find(c, "IconStyle")
                if icon is not None:
                    col = _find(icon, "color")
                    if col is not None and col.text:
                        colors["#" + c.get("id")] = col.text.strip().lower()
            elif t == "StyleMap" and c.get("id"):
                for pair in _findall(c, "Pair"):
                    if _text(pair, "key") == "normal":
                        maps["#" + c.get("id")] = _text(pair, "styleUrl")
            walk(c)

    walk(doc)
    for sid, target in maps.items():
        if target in colors:
            colors[sid] = colors[target]
    return colors


def read_kml(path):
    if path.lower().endswith(".kmz"):
        with zipfile.ZipFile(path) as z:
            name = next((n for n in z.namelist() if n.lower().endswith(".kml")), None)
            if not name:
                raise ValueError(f"no .kml inside {path}")
            data = z.read(name)
        root = ET.fromstring(data)
    else:
        root = ET.parse(path).getroot()

    doc = _find(root, "Document") or root
    style_colors = _style_colors(doc)
    out = []

    def walk(el, folders):
        for c in el:
            t = _local(c.tag)
            if t == "Folder":
                nm = _text(c, "name")
                walk(c, folders + ([nm] if nm else []))
            elif t == "Document":
                walk(c, folders)
            elif t == "Placemark":
                out.append(_placemark(c, folders, style_colors))

    walk(doc, [])
    return out


def _parse_coords(text):
    """'lon,lat,alt lon,lat ...' -> [(lon,lat,alt|None), ...] (strings, order preserved)."""
    out = []
    for tok in (text or "").split():
        p = tok.split(",")
        if len(p) >= 2 and p[0].strip() and p[1].strip():
            out.append((p[0].strip(), p[1].strip(),
                        p[2].strip() if len(p) > 2 and p[2].strip() else None))
    return out


def _find_deep(el, name):
    for d in el.iter():
        if _local(d.tag) == name:
            return d
    return None


def _geom_str(coords):
    return " ".join(",".join(x for x in v if x is not None) for v in coords)


def _extract_geometry(pm):
    """-> (geometry_type, geometry_str|None, rep_lon, rep_lat, rep_alt). A LineString
    keeps its full vertex list in geometry_str with a mid-vertex marker; a Polygon
    keeps its outer ring with a centroid marker; a Point is just a marker."""
    pt = _find(pm, "Point")
    if pt is not None:
        c = _parse_coords(_text(pt, "coordinates"))
        if c:
            return "point", None, c[0][0], c[0][1], c[0][2]
    ls = _find(pm, "LineString")
    if ls is not None:
        c = _parse_coords(_text(ls, "coordinates"))
        if len(c) >= 2:
            mid = c[len(c) // 2]                       # deterministic representative marker
            return "linestring", _geom_str(c), mid[0], mid[1], mid[2]
    poly = _find(pm, "Polygon")
    if poly is not None:
        ring = _find_deep(poly, "LinearRing")
        c = _parse_coords(_text(ring, "coordinates")) if ring is not None else []
        if len(c) >= 3:
            lons = [float(v[0]) for v in c]
            lats = [float(v[1]) for v in c]
            return "polygon", _geom_str(c), \
                "%.6f" % (sum(lons) / len(lons)), "%.6f" % (sum(lats) / len(lats)), None
    return "point", None, None, None, None


def _placemark(pm, folders, style_colors):
    ext, source_list, category, entry_id, coord_precision = {}, [], "", None, ""
    ed = _find(pm, "ExtendedData")
    if ed is not None:
        for d in _findall(ed, "Data"):
            k = d.get("name")
            v = _text(d, "value")
            if not k:
                continue
            if k == "source":                      # export writes one Data per source
                source_list.append(v)
            elif k == "sources":                   # a legacy single field
                source_list.extend(s.strip() for s in re.split(r"[;\n]", v) if s.strip())
            elif k == "category":
                category = v
            elif k == "entry_id":
                entry_id = v
            elif k == "coord_precision":
                coord_precision = v
            else:
                ext[k] = v
    gtype, geom, lon, lat, alt = _extract_geometry(pm)
    style_url = _text(pm, "styleUrl")
    return {
        "name": _text(pm, "name"), "description": _text(pm, "description"),
        "style_url": style_url, "lon": lon, "lat": lat, "alt": alt,
        "geometry_type": gtype, "geometry": geom,
        "folder_path": folders, "ext": ext, "source_list": source_list,
        "category": category, "entry_id": entry_id, "coord_precision": coord_precision,
        "observed_kml_color": style_colors.get(style_url, ""),
    }


# ---- tabular (CSV / XLSX) -------------------------------------------------

_TAB_MAPPED = {"name", "lon", "lat", "alt", "category", "description",
               "sources", "source", "coord_precision", "entry_id",
               "geometry_type", "geometry"}


def _row_to_rec(row):
    row = {(k or "").strip(): ("" if v is None else str(v).strip()) for k, v in row.items()}
    ext = {k: v for k, v in row.items() if k.lower() not in _TAB_MAPPED and v != ""}
    src = row.get("sources") or row.get("source") or ""
    source_list = [s.strip() for s in re.split(r"[;\n]", src) if s.strip()]
    return {
        "name": row.get("name", ""), "description": row.get("description", ""),
        "style_url": "", "lon": row.get("lon") or None, "lat": row.get("lat") or None,
        "alt": row.get("alt") or None, "folder_path": [], "observed_kml_color": "",
        "ext": ext, "source_list": source_list, "category": row.get("category", ""),
        "entry_id": row.get("entry_id") or None,
        "coord_precision": row.get("coord_precision", ""),
        "geometry_type": row.get("geometry_type") or "point",
        "geometry": row.get("geometry") or None,
    }


def read_csv(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return [_row_to_rec(row) for row in csv.DictReader(f)]


def read_xlsx(path):
    try:
        import openpyxl
    except ImportError:
        print(f"  ! openpyxl not installed — export {path} to CSV first "
              f"(or `pip install openpyxl`); skipped")
        return None
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb.active.iter_rows(values_only=True))
    if not rows:
        return []
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        out.append(_row_to_rec({header[i]: r[i] for i in range(min(len(header), len(r)))}))
    return out


# ---- build site records ---------------------------------------------------

def build_site(rec, source_file, source_type, next_id, cats, atlas_root):
    entry_id = rec.get("entry_id")
    if entry_id and _ID_RE.match(entry_id):
        sid, assigned = entry_id, False
    else:
        sid, assigned = lib.make_id(next_id), True

    obs_rgb = ""
    if rec["observed_kml_color"]:
        try:
            obs_rgb = lib.kml_to_rgb(rec["observed_kml_color"])
        except ValueError:
            obs_rgb = ""

    category, staged = rec.get("category", ""), False
    if not category:
        if obs_rgb:
            for k, meta in cats.items():
                if meta["color"].lower() == obs_rgb.lower():
                    category = k
                    break
        if not category:
            category = slugify(rec["style_url"].lstrip("#")) if rec["style_url"] else "uncategorized"
            staged = True
    elif category not in cats:
        staged = True

    prov = {
        "source_file": os.path.basename(source_file),
        "source_type": source_type,
        "source_ref": f"Placemark#{rec['name']}" if rec["name"] else "Placemark",
        "imported_at": datetime.now(timezone.utc).replace(microsecond=0)
                       .isoformat().replace("+00:00", "Z"),
    }
    if rec["style_url"]:
        prov["original_style_url"] = rec["style_url"]
    if rec["observed_kml_color"]:
        prov["original_color_kml"] = rec["observed_kml_color"]
    if obs_rgb:
        prov["original_color_rgb"] = obs_rgb

    fm = {
        "id": sid,
        "name": rec["name"] or "",
        "category": category,
        "lon": rec["lon"], "lat": rec["lat"],
        "alt": rec["alt"] if rec["alt"] not in (None, "") else None,
        "geometry_type": rec.get("geometry_type") or "point",
        "geometry": rec.get("geometry") or None,
        "coord_precision": rec.get("coord_precision") or "unknown",
        "status": "active",
        "tags": [], "related": [], "sources": list(rec.get("source_list") or []),
        "folder_path": rec["folder_path"],
        "graduated_to": "",
        "provenance": prov,
        "extended": rec["ext"],
        "description": rec["description"],
    }

    # MERGE: preserve every authored field on an existing site (anything the
    # source does not carry — status, tags, related, graduated_to,
    # coord_precision, and any [D] domain overlay). Only SOURCE_FIELDS are
    # overwritten from the import, so a re-import is a fixed point on enriched
    # sites too and never resets authored state.
    dst = os.path.join(atlas_root, lib.site_relpath(lib.id_num(sid)))
    if os.path.exists(dst):
        try:
            old = lib.parse_site(dst)
            for k, v in old.items():
                if k not in lib.SOURCE_FIELDS:
                    fm[k] = v
        except (ValueError, OSError):
            pass

    return fm, assigned, staged, category


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    atlas_root, canon = argv[0], argv[1]
    inputs = argv[2:]
    cats = lib.load_categories(canon)
    next_id = lib.highest_id(atlas_root) + 1

    written, staged_cats, dups, no_coord = [], {}, [], []
    seen = {}

    for inp in inputs:
        low = inp.lower()
        try:
            if low.endswith((".kml", ".kmz")):
                recs, stype = read_kml(inp), ("kmz" if low.endswith(".kmz") else "kml")
            elif low.endswith(".csv"):
                recs, stype = read_csv(inp), "csv"
            elif low.endswith((".xlsx", ".xlsm")):
                recs = read_xlsx(inp)
                if recs is None:
                    continue
                stype = "xlsx"
            else:
                print(f"  ! skipping unsupported input: {inp} (KML/KMZ/CSV/XLSX)")
                continue
        except Exception as e:                       # noqa: BLE001 — one bad file must not kill the batch
            print(f"  ! failed to read {inp}: {e} — skipped")
            continue

        for rec in recs:
            if rec.get("lon") in (None, "") or rec.get("lat") in (None, ""):
                no_coord.append((os.path.basename(inp), rec.get("name") or "(unnamed)"))
                continue
            fm, assigned, staged, category = build_site(rec, inp, stype, next_id, cats, atlas_root)
            if assigned:
                next_id += 1
            if staged:
                staged_cats[category] = staged_cats.get(category, 0) + 1
            key = (fm["name"].lower(), _safe_round(fm["lon"]), _safe_round(fm["lat"]))
            if key in seen and fm["name"]:
                dups.append((fm["id"], seen[key], fm["name"]))
            else:
                seen[key] = fm["id"]
            rel = lib.site_relpath(lib.id_num(fm["id"]))
            dst = os.path.join(atlas_root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "w", encoding="utf-8") as f:
                f.write(lib.render_site(fm))
            written.append(rel)

    print(f"✓ imported {len(written)} site(s) into {atlas_root}/sites/ (staged, not committed)")
    if staged_cats:
        print("\n  ⚠ categories to add to .claude/atlas-canon.md before /atlas export:")
        for c, n in sorted(staged_cats.items()):
            print(f"      {c}  ({n} site(s))")
    if no_coord:
        print("\n  ⚠ skipped (no coordinates / geometry):")
        for src, nm in no_coord:
            print(f"      {nm}  [{src}]")
    if dups:
        print("\n  ⚠ possible near-duplicates (same name + location) — resolve by hand, never auto-merged:")
        for new, old, nm in dups:
            print(f"      {new} ~ {old}  ({nm})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
