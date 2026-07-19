#!/usr/bin/env python3
"""
rasa.module.atlas — color-key renderer.

Turns the project-owned category->color seam (.claude/atlas-canon.md) into the
KML <Style>/<StyleMap> blocks and the INDEX legend. Pure function of the seam:
change a color once, every marker and the legend follow.

Usage:
    python3 render_key.py <atlas_canon.md>          # prints the KML styles + legend
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lib  # noqa: E402


def kml_styles(cats):
    """One shared <Style>/<StyleMap> per category (referenced by styleUrl)."""
    parts = []
    for key in sorted(cats):
        meta = cats[key]
        col = lib.rgb_to_kml(meta["color"])                 # ff + bb + gg + rr (opaque)
        fill = "80" + col[2:]                               # ~50% alpha for polygon fill
        href = f"http://maps.google.com/mapfiles/kml/{meta.get('kml_icon', 'paddle/wht-blank')}.png"
        # One style serves all three geometries of the category: points (IconStyle),
        # lines/connections (LineStyle), and areas (PolyStyle) — same colour.
        parts.append(
            f'<Style id="cat-{key}-normal">\n'
            f'  <IconStyle><color>{col}</color><scale>1.1</scale>'
            f'<Icon><href>{href}</href></Icon></IconStyle>\n'
            f'  <LabelStyle><color>{col}</color></LabelStyle>\n'
            f'  <LineStyle><color>{col}</color><width>2</width></LineStyle>\n'
            f'  <PolyStyle><color>{fill}</color></PolyStyle>\n'
            f'</Style>\n'
            f'<Style id="cat-{key}-highlight">\n'
            f'  <IconStyle><color>{col}</color><scale>1.4</scale>'
            f'<Icon><href>{href}</href></Icon></IconStyle>\n'
            f'  <LineStyle><color>{col}</color><width>3</width></LineStyle>\n'
            f'  <PolyStyle><color>{fill}</color></PolyStyle>\n'
            f'</Style>\n'
            f'<StyleMap id="cat-{key}">\n'
            f'  <Pair><key>normal</key><styleUrl>#cat-{key}-normal</styleUrl></Pair>\n'
            f'  <Pair><key>highlight</key><styleUrl>#cat-{key}-highlight</styleUrl></Pair>\n'
            f'</StyleMap>'
        )
    return "\n".join(parts)


def legend_md(cats, counts=None):
    """A markdown legend for the INDEX dashboard."""
    lines = ["| Category | Key | Color | Count |", "|---|---|---|---|"]
    for key in sorted(cats):
        c = cats[key]["color"]
        n = (counts or {}).get(key, "")
        lines.append(f"| {cats[key].get('label', key)} | `{key}` | `{c}` | {n} |")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cats = lib.load_categories(sys.argv[1])
    if not cats:
        print(f"  (no categories found in {sys.argv[1]} — fill the `categories:` block)")
        sys.exit(0)
    print("<!-- KML styles -->")
    print(kml_styles(cats))
    print("\n<!-- INDEX legend -->")
    print(legend_md(cats))
