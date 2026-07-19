#!/usr/bin/env python3
"""
rasa.module.atlas — exporter.  atlas/sites/**/site-*.md  ->  atlas.kml + atlas.geojson

Usage:
    python3 export.py <atlas_root> <atlas_canon.md> [kml|geojson|both]

- HARD-STOP: refuses to derive a color for any in-use category absent from the
  seam (the one inference the module won't make). Add it to atlas-canon.md first.
- Colors are pure functions of the seam (KML aabbggrr, GeoJSON marker-color).
- Every site's `entry_id` + `extended` bag ride in the export, so a re-import
  re-joins to the same site — the round-trip is a fixed point.

Standard library only.
"""

import glob
import json
import os
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib          # noqa: E402
import render_key   # noqa: E402


def load_sites(atlas_root):
    sites = []
    for path in sorted(glob.glob(os.path.join(atlas_root, "sites", "*", "site-*.md"))):
        sites.append(lib.parse_site(path))
    return sites


def _cdata(text):
    # Split any CDATA terminator so it round-trips exactly — ElementTree
    # concatenates adjacent CDATA sections, so ']]>' -> ']]]]><![CDATA[>'.
    return "<![CDATA[" + (text or "").replace("]]>", "]]]]><![CDATA[>") + "]]>"


def _has_coords(s):
    try:
        float(s.get("lon"))
        float(s.get("lat"))
        return True
    except (TypeError, ValueError):
        return False


def _coord_str(s):
    lon, lat, alt = s.get("lon"), s.get("lat"), s.get("alt")
    if alt in (None, "", "null"):
        return f"{lon},{lat}"
    return f"{lon},{lat},{alt}"


def _extdata(s):
    """entry_id + category + one Data per source + the extended bag -> KML ExtendedData."""
    rows = [("entry_id", s["id"]), ("category", s.get("category", ""))]
    for src in (s.get("sources") or []):     # one row per source — a source may contain
        rows.append(("source", src))         #   spaces/commas, so never space-join them
    for k, v in (s.get("extended") or {}).items():
        rows.append((k, v))
    body = "".join(
        f'<Data name="{escape(k)}"><value>{escape("" if v is None else str(v))}</value></Data>'
        for k, v in rows
    )
    return f"<ExtendedData>{body}</ExtendedData>"


def _geometry_kml(s):
    """The KML geometry for a feature: its full LineString/Polygon when present,
    else a Point at the representative marker. entry_id/geometry round-trip it back."""
    gt = (s.get("geometry_type") or "point").lower()
    geom = s.get("geometry")
    if gt == "linestring" and geom:
        return f"<LineString><tessellate>1</tessellate><coordinates>{escape(geom)}</coordinates></LineString>"
    if gt == "polygon" and geom:
        return ("<Polygon><tessellate>1</tessellate><outerBoundaryIs><LinearRing>"
                f"<coordinates>{escape(geom)}</coordinates></LinearRing></outerBoundaryIs></Polygon>")
    return f"<Point><coordinates>{_coord_str(s)}</coordinates></Point>"


def _placemark(s):
    parts = ["<Placemark>"]
    parts.append(f"  <name>{escape(s.get('name') or '')}</name>")
    parts.append(f'  <styleUrl>#cat-{s["category"]}</styleUrl>')
    if s.get("description"):
        parts.append(f"  <description>{_cdata(s['description'])}</description>")
    parts.append(f"  {_extdata(s)}")
    parts.append(f"  {_geometry_kml(s)}")
    parts.append("</Placemark>")
    return "\n".join(parts)


def _folder_tree(sites):
    """Nest sites under their folder_path so import reconstructs the same path."""
    root = {"_sites": [], "_children": {}}
    for s in sites:
        node = root
        for name in (s.get("folder_path") or []):
            node = node["_children"].setdefault(name, {"_sites": [], "_children": {}})
        node["_sites"].append(s)
    return root


def _emit_tree(node, indent=1):
    out = []
    for s in node["_sites"]:
        out.append(_placemark(s))
    for name in node["_children"]:  # dict preserves insertion (import) order
        child = node["_children"][name]
        out.append(f"<Folder>\n<name>{escape(name)}</name>")
        out.append(_emit_tree(child, indent + 1))
        out.append("</Folder>")
    return "\n".join(out)


def build_kml(sites, cats):
    styles = render_key.kml_styles(cats)
    body = _emit_tree(_folder_tree(sites))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
        '<Document>\n'
        f'{styles}\n'
        f'{body}\n'
        '</Document>\n'
        '</kml>\n'
    )


def _geom_pairs(geom):
    """'lon,lat,alt lon,lat ...' -> [[lon,lat(,alt)], ...] as floats (RFC 7946 order)."""
    out = []
    for tok in (geom or "").split():
        p = tok.split(",")
        if len(p) >= 2:
            v = [float(p[0]), float(p[1])]
            if len(p) > 2 and p[2].strip():
                v.append(float(p[2]))
            out.append(v)
    return out


def _geometry_geojson(s):
    gt = (s.get("geometry_type") or "point").lower()
    geom = s.get("geometry")
    if gt == "linestring" and geom:
        return {"type": "LineString", "coordinates": _geom_pairs(geom)}
    if gt == "polygon" and geom:
        return {"type": "Polygon", "coordinates": [_geom_pairs(geom)]}
    coords = [float(s["lon"]), float(s["lat"])]
    if s.get("alt") not in (None, "", "null"):
        coords.append(float(s["alt"]))
    return {"type": "Point", "coordinates": coords}


def build_geojson(sites, cats):
    features = []
    for s in sites:
        color = cats[s["category"]]["color"]
        gt = (s.get("geometry_type") or "point").lower()
        props = {
            "name": s.get("name") or "",
            "category": s.get("category", ""),
            "marker-color": color, "stroke": color, "fill": color,
            "marker-symbol": cats[s["category"]].get("symbol", ""),
            "entry_id": s["id"], "geometry_type": gt,
        }
        if s.get("sources"):
            props["sources"] = s["sources"]
        for k, v in (s.get("extended") or {}).items():
            props.setdefault(k, v)
        if s.get("description"):
            props["description"] = s["description"]
        features.append({
            "type": "Feature",
            "geometry": _geometry_geojson(s),
            "properties": props,
        })
    return json.dumps({"type": "FeatureCollection", "features": features},
                      indent=2, ensure_ascii=False) + "\n"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    atlas_root, canon = argv[0], argv[1]
    which = argv[2] if len(argv) > 2 else "both"
    cats = lib.load_categories(canon)
    sites = load_sites(atlas_root)

    # A site with non-numeric coordinates cannot be a map marker — skip + report
    # rather than emit invalid KML (None,None) or crash GeoJSON on float(None).
    no_coord = [s["id"] for s in sites if not _has_coords(s)]
    sites = [s for s in sites if _has_coords(s)]
    if no_coord:
        print(f"  ⚠ {len(no_coord)} site(s) skipped — no numeric coordinates: "
              f"{', '.join(no_coord)}", file=sys.stderr)

    in_use = {s.get("category", "") for s in sites}
    missing = sorted(c for c in in_use if c and c not in cats)
    if missing:
        print("✗ export refused — these in-use categories are not in the color key "
              f"({canon}):", file=sys.stderr)
        for c in missing:
            print(f"      {c}", file=sys.stderr)
        print("  Add them to the `categories:` block first (the one inference the "
              "module won't make).", file=sys.stderr)
        return 1

    wrote = []
    if which in ("kml", "both"):
        p = os.path.join(atlas_root, "atlas.kml")
        with open(p, "w", encoding="utf-8") as f:
            f.write(build_kml(sites, cats))
        wrote.append(p)
    if which in ("geojson", "both"):
        p = os.path.join(atlas_root, "atlas.geojson")
        with open(p, "w", encoding="utf-8") as f:
            f.write(build_geojson(sites, cats))
        wrote.append(p)

    print(f"✓ exported {len(sites)} site(s):")
    for p in wrote:
        print(f"      {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
