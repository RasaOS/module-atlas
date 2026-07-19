#!/usr/bin/env python3
"""
rasa.module.atlas — shared converter library.

Deterministic helpers for the site node, the color key, and the KML/GeoJSON
round-trip. Standard library only (xml.etree, zipfile, csv, json, re, math) so
the converters run anywhere Python 3 does, with no install step. XLSX is
supported best-effort via openpyxl if present; otherwise export the sheet to CSV.

The round-trip identity is defined on the STABLE fields
  { id, name, category, lon, lat, alt, folder_path, sources, extended, description }
NOT on `provenance` — provenance records where a given import came from, which
legitimately changes when you re-import the exported atlas.kml. See atlas-rules.md.
"""

import math
import os
import re

# ---- id scheme -------------------------------------------------------------

ID_PREFIX = "site-"
ID_WIDTH = 6           # fixed once — 1,000,000 headroom; widening would rename every file
SHARD = 1000           # id-block size for atlas/sites/<lo>-<hi>/


def id_num(site_id):
    """'site-000042' -> 42"""
    return int(str(site_id).split("-", 1)[1])


def make_id(n):
    """42 -> 'site-000042'"""
    return f"{ID_PREFIX}{int(n):0{ID_WIDTH}d}"


def id_block(n):
    """42 -> '000000-000999' (classification-free shard, on the id)."""
    lo = (int(n) // SHARD) * SHARD
    hi = lo + SHARD - 1
    return f"{lo:0{ID_WIDTH}d}-{hi:0{ID_WIDTH}d}"


def site_relpath(n):
    """42 -> 'sites/000000-000999/site-000042.md' (relative to the atlas root)."""
    return os.path.join("sites", id_block(n), make_id(n) + ".md")


def highest_id(atlas_root):
    """Scan existing site files; return the highest id number, or -1 if none."""
    hi = -1
    sites_dir = os.path.join(atlas_root, "sites")
    if not os.path.isdir(sites_dir):
        return hi
    for block in sorted(os.listdir(sites_dir)):
        bdir = os.path.join(sites_dir, block)
        if not os.path.isdir(bdir):
            continue
        for fn in os.listdir(bdir):
            m = re.match(r"^(site-\d+)\.md$", fn)
            if m:
                hi = max(hi, id_num(m.group(1)))
    return hi


# ---- color key -------------------------------------------------------------

def rgb_to_kml(hex_rgb, alpha="ff"):
    """'#1b9e77' -> 'ff779e1b'  (KML is aabbggrr — alpha + blue + green + red, REVERSED)."""
    h = hex_rgb.strip().lstrip("#").lower()
    if not re.fullmatch(r"[0-9a-f]{6}", h):
        raise ValueError(f"not a #RRGGBB color: {hex_rgb!r}")
    rr, gg, bb = h[0:2], h[2:4], h[4:6]
    return f"{alpha.lower()}{bb}{gg}{rr}"


def kml_to_rgb(aabbggrr):
    """'ff779e1b' (or 'ff779e1b') -> '#1b9e77'. Accepts 6 (bbggrr) or 8 (aabbggrr) hex."""
    s = str(aabbggrr).strip().lstrip("#").lower()
    if re.fullmatch(r"[0-9a-f]{8}", s):
        _, bb, gg, rr = s[0:2], s[2:4], s[4:6], s[6:8]
    elif re.fullmatch(r"[0-9a-f]{6}", s):
        bb, gg, rr = s[0:2], s[2:4], s[4:6]
    else:
        raise ValueError(f"not a KML color: {aabbggrr!r}")
    return f"#{rr}{gg}{bb}"


def load_categories(atlas_canon_path):
    """
    Parse the project-owned color key from .claude/atlas-canon.md.
    Recognizes lines of the form (inside the `categories:` block):
        <key>: { label: "...", color: "#RRGGBB", symbol: ..., kml_icon: "..." }
    Returns { key: {color, label, symbol, kml_icon} }. Commented (#-led) lines
    are ignored, so the shipped placeholder-free template contributes nothing.
    """
    cats = {}
    if not os.path.isfile(atlas_canon_path):
        return cats
    line_re = re.compile(
        r"^\s*([A-Za-z0-9][A-Za-z0-9_-]*)\s*:\s*\{(.*)\}\s*$"
    )
    field_re = re.compile(r'([A-Za-z_]+)\s*:\s*"([^"]*)"|([A-Za-z_]+)\s*:\s*([^,}\s]+)')
    with open(atlas_canon_path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.lstrip().startswith("#"):
                continue
            m = line_re.match(line)
            if not m:
                continue
            key, body = m.group(1), m.group(2)
            fields = {}
            for fm in field_re.finditer(body):
                k = fm.group(1) or fm.group(3)
                v = fm.group(2) if fm.group(2) is not None else fm.group(4)
                fields[k] = v
            if "color" not in fields:
                continue
            cats[key] = {
                "color": fields["color"],
                "label": fields.get("label", key),
                "symbol": fields.get("symbol", ""),
                "kml_icon": fields.get("kml_icon", "paddle/wht-blank"),
            }
    return cats


# ---- YAML frontmatter (a deterministic parser/emitter for the site schema) --
#
# Not a general YAML implementation — a tight, round-trip-exact emitter/parser
# for the controlled site frontmatter: flat scalars, flow lists ([a, b]), and
# two one-level nested maps (provenance, extended). Emitter and parser are
# inverses, which is what the fixed-point gate relies on.

# Frontmatter key order (module-owned fields; [D] domain fields appended by the
# consuming domain are preserved verbatim on read but never emitted by the tool).
FM_ORDER = [
    "id", "name", "category", "lon", "lat", "alt", "geometry_type", "geometry",
    "coord_precision", "status", "tags", "related", "sources", "folder_path",
    "graduated_to", "provenance", "extended",
]
NESTED = ("provenance", "extended")
LISTS = ("tags", "related", "sources", "folder_path")

# Fields a re-import is authoritative for (it carries them in the source / the
# exported atlas.kml). Every OTHER field on an existing site — status, tags,
# related, graduated_to, coord_precision, and any [D] domain overlay
# (cadence, last_verified) — is authored and MUST be preserved on re-import
# (see import.build_site merge), so re-importing never un-retires / un-graduates
# / un-tags a real site.
SOURCE_FIELDS = {"id", "name", "category", "lon", "lat", "alt", "geometry_type",
                 "geometry", "folder_path", "extended", "provenance", "sources",
                 "description"}

_SAFE = re.compile(r"^[A-Za-z0-9_./:+-]+$")


def _emit_scalar(v):
    if v is None:
        return "null"
    s = str(v)
    # Force-quote the empty string and the reserved token "null" so a value that
    # is literally "null" survives (bare null parses back to None).
    if s == "" or s == "null" or not _SAFE.match(s):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _parse_scalar(s):
    s = s.strip()
    if s == "" :
        return ""
    if s == "null":
        return None
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        return s[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return s


def _emit_list(items):
    return "[" + ", ".join(_emit_scalar(x) for x in items) + "]"


def _parse_list(s):
    s = s.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1].strip()
    if not s:
        return []
    # split on commas not inside quotes
    out, cur, q = [], "", False
    for ch in s:
        if ch == '"':
            q = not q
            cur += ch
        elif ch == "," and not q:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur)
    return [_parse_scalar(x) for x in out]


def emit_frontmatter(d):
    """dict -> YAML frontmatter text (no fences). Deterministic key order."""
    lines = []
    for k in FM_ORDER:
        if k not in d:
            continue
        v = d[k]
        if k in NESTED:
            sub = v or {}
            lines.append(f"{k}:")
            for sk in sub:
                lines.append(f"  {sk}: {_emit_scalar(sub[sk])}")
        elif k in LISTS:
            lines.append(f"{k}: {_emit_list(v or [])}")
        else:
            lines.append(f"{k}: {_emit_scalar(v)}")
    # preserve any [D] domain-added keys verbatim (e.g. cadence, last_verified)
    for k in d:
        if k in FM_ORDER:
            continue
        v = d[k]
        if isinstance(v, dict):
            lines.append(f"{k}:")
            for sk in v:
                lines.append(f"  {sk}: {_emit_scalar(v[sk])}")
        elif isinstance(v, list):
            lines.append(f"{k}: {_emit_list(v)}")
        else:
            lines.append(f"{k}: {_emit_scalar(v)}")
    return "\n".join(lines)


def parse_frontmatter(text):
    """YAML frontmatter text -> dict. Inverse of emit_frontmatter for the schema."""
    d = {}
    cur_nested = None
    for raw in text.splitlines():
        if not raw.strip():
            continue
        if raw.startswith("  ") and cur_nested is not None:
            k, _, v = raw.strip().partition(":")
            d[cur_nested][k.strip()] = _parse_scalar(v)
            continue
        cur_nested = None
        k, _, v = raw.partition(":")
        k, v = k.strip(), v.strip()
        if k in NESTED and v == "":
            d[k] = {}
            cur_nested = k
        elif k in LISTS:
            d[k] = _parse_list(v)
        else:
            d[k] = _parse_scalar(v)
    return d


# ---- site file (frontmatter + body) ----------------------------------------

def _section(body, heading):
    """Return the text under a '## heading' up to the next '## ', stripped."""
    m = re.search(r"^##\s+" + re.escape(heading) + r"\s*$(.*?)(?=^##\s|\Z)",
                  body, re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def parse_site(path):
    """Read a site .md -> dict of frontmatter + 'description' (body ## Description)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not m:
        raise ValueError(f"no frontmatter in {path}")
    fm = parse_frontmatter(m.group(1))
    body = m.group(2)
    fm["description"] = _section(body, "Description")
    return fm


def render_site(fm):
    """dict (frontmatter + optional 'description') -> full site .md text."""
    d = {k: v for k, v in fm.items() if k != "description"}
    name = fm.get("name") or ""
    title = f"{name} · {fm.get('id','')}".strip(" ·")
    desc = fm.get("description", "") or ""
    body = (
        f"# {title}\n\n"
        f"## Description\n{desc}\n\n"
        f"## Provenance excerpt\n<!-- Verbatim source text backing each cited claim. -->\n\n"
        f"## Geology\n<!-- Soft mineral seam; present only if relevant. -->\n"
    )
    return f"---\n{emit_frontmatter(d)}\n---\n\n{body}"


# ---- geo -------------------------------------------------------------------

def haversine_km(lon1, lat1, lon2, lat2):
    r = 6371.0088
    p1, p2 = math.radians(float(lat1)), math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlmb = math.radians(float(lon2) - float(lon1))
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))
