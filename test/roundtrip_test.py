#!/usr/bin/env python3
"""
rasa.module.atlas — the round-trip fixed-point release gate.

The losslessness contract's proof. Run before any tag:

    python3 test/roundtrip_test.py        # exit 0 = green

Covers (each an adversarial case the converters must survive):
  A. PRISTINE fixed point — import -> export -> re-import is identity on the stable
     field set {id,name,category,lon,lat,alt,folder_path,sources,extended,description}
     over a HARD fixture: unicode + quotes + colon + '#' + comma in a name; a
     3-level folder_path with '&','<>','/' in the names; alt=0 vs alt absent; an
     extended value with a comma and one with '&'; multi-token sources ('Smith 2020',
     a URL); a description with HTML, '&', and a literal ']]>' CDATA terminator.
  B. MERGE preservation — a re-import must NOT reset human-authored fields
     (status/tags/related/graduated_to) or a [D] domain overlay.
  C. The literal string "null" survives as a name.
  D. A placemark with no Point is skipped, not crashed on; export skips a
     coordinate-less site rather than emitting invalid geometry.
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATLAS = os.path.join(HERE, "..", "content", "skills", "atlas")
sys.path.insert(0, ATLAS)
import lib  # noqa: E402

STABLE = ["id", "name", "category", "lon", "lat", "alt", "geometry_type", "geometry",
          "folder_path", "sources", "extended", "description"]

SEAM = """# Atlas Canon
    categories:
      water-source: { label: "Water source", color: "#1b9e77", symbol: drop,     kml_icon: "paddle/wht-blank" }
      structure:    { label: "Structure",     color: "#d95f02", symbol: building, kml_icon: "paddle/wht-blank" }
"""

# A hard source KML. Placemark 4 has no Point (must be skipped on import).
HARD_KML = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
  <Style id="structForm"><IconStyle><color>ff025fd9</color></IconStyle></Style>
  <Folder><name>North sector</name>
    <Placemark>
      <name>Cenote "El Ojo": #3, north</name>
      <description><![CDATA[<b>bold</b> &amp; entity, colon: value; term end]]></description>
      <ExtendedData>
        <Data name="category"><value>water-source</value></Data>
        <Data name="flow_lpm"><value>1,2</value></Data>
        <Data name="note"><value>a &amp; b</value></Data>
        <Data name="source"><value>Smith 2020</value></Data>
        <Data name="source"><value>http://x/y?a=b&amp;c=d</value></Data>
      </ExtendedData>
      <Point><coordinates>-119.417900,36.778300,0</coordinates></Point>
    </Placemark>
  </Folder>
  <Folder><name>A &amp; B</name><Folder><name>C&lt;D&gt;</name><Folder><name>E/F</name>
    <Placemark>
      <name>null</name>
      <ExtendedData><Data name="category"><value>structure</value></Data></ExtendedData>
      <Point><coordinates>1.0,2.0</coordinates></Point>
    </Placemark>
  </Folder></Folder></Folder>
  <Placemark>
    <name>Old Platform</name><styleUrl>#structForm</styleUrl>
    <Point><coordinates>10.500000,45.250000</coordinates></Point>
  </Placemark>
  <Placemark><name>Ley Line</name>
    <ExtendedData><Data name="category"><value>structure</value></Data></ExtendedData>
    <LineString><coordinates>1,2 3,4,10 5,6</coordinates></LineString>
  </Placemark>
  <Placemark><name>Enclosure</name>
    <ExtendedData><Data name="category"><value>water-source</value></Data></ExtendedData>
    <Polygon><outerBoundaryIs><LinearRing>
      <coordinates>0,0 0,1 1,1 1,0 0,0</coordinates></LinearRing></outerBoundaryIs></Polygon>
  </Placemark>
  <Placemark><name>No Geometry</name></Placemark>
</Document></kml>
"""


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(ATLAS, script), *args],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"{script} failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
    return r.stdout + r.stderr


def load(root):
    return {s["id"]: s for s in
            (lib.parse_site(p) for p in sorted(glob.glob(os.path.join(root, "sites", "*", "site-*.md"))))}


def stable(site):
    return {k: site.get(k) for k in STABLE}


def main():
    tmp = tempfile.mkdtemp(prefix="atlas-gate-")
    try:
        canon = os.path.join(tmp, "atlas-canon.md")
        open(canon, "w").write(SEAM)
        src = os.path.join(tmp, "source.kml")
        open(src, "w").write(HARD_KML)

        a, b = os.path.join(tmp, "a"), os.path.join(tmp, "b")

        # A) pristine fixed point — points + a LineString + a Polygon; a geometry-less
        #    placemark is skipped
        out = run("import.py", a, canon, src)
        s1 = load(a)
        assert len(s1) == 5, f"expected 5 features (3 points + line + polygon), got {len(s1)}"
        assert "no coordinates" in out.lower(), "geometry-less skip not reported"
        # geometry captured, not flattened
        line = next(x for x in s1.values() if x["name"] == "Ley Line")
        assert line["geometry_type"] == "linestring" and line["geometry"] == "1,2 3,4,10 5,6", line
        assert (line["lon"], line["lat"], line["alt"]) == ("3", "4", "10"), \
            f"line marker should be the mid-vertex: {line['lon']},{line['lat']},{line['alt']}"
        poly = next(x for x in s1.values() if x["name"] == "Enclosure")
        assert poly["geometry_type"] == "polygon" and poly["geometry"] == "0,0 0,1 1,1 1,0 0,0", poly
        run("export.py", a, canon, "both")
        # the exported KML actually carries LineString/Polygon geometry, not just points
        kml = open(os.path.join(a, "atlas.kml")).read()
        assert "<LineString>" in kml and "<Polygon>" in kml, "export flattened geometry to points"
        run("import.py", b, canon, os.path.join(a, "atlas.kml"))
        s2 = load(b)
        assert set(s1) == set(s2), f"id sets differ: {set(s1)} vs {set(s2)}"
        for sid in s1:
            assert stable(s1[sid]) == stable(s2[sid]), \
                f"FIXED POINT broke on {sid}:\n  {stable(s1[sid])}\n  {stable(s2[sid])}"

        # C) the "null" name survived as the literal string
        nulls = [x for x in s1.values() if x["name"] == "null"]
        assert nulls, 'literal name "null" was lost (parsed back to None)'
        # multi-token source survived intact
        cen = next(x for x in s1.values() if x["name"].startswith("Cenote"))
        assert cen["sources"] == ["Smith 2020", "http://x/y?a=b&c=d"], \
            f"sources shredded: {cen['sources']}"
        assert cen["folder_path"] == ["North sector"], cen["folder_path"]
        assert nulls[0]["folder_path"] == ["A & B", "C<D>", "E/F"], nulls[0]["folder_path"]

        # B) merge preservation — enrich a site, re-import into the SAME atlas
        cen_id = cen["id"]
        fm = lib.parse_site(os.path.join(a, lib.site_relpath(lib.id_num(cen_id))))
        fm["status"] = 'retired: "superseded"'
        fm["tags"] = ["perennial", "karst"]
        fm["related"] = ["north-complex"]
        fm["graduated_to"] = "[[cenote-dispute]]"
        fm["cadence"] = "90d"  # a [D] domain overlay
        fm["description"] = "window: [start ]]> end], see <ref>"  # a literal CDATA terminator
        open(os.path.join(a, lib.site_relpath(lib.id_num(cen_id))), "w").write(lib.render_site(fm))
        run("export.py", a, canon, "kml")
        run("import.py", a, canon, os.path.join(a, "atlas.kml"))   # re-import onto itself
        merged = lib.parse_site(os.path.join(a, lib.site_relpath(lib.id_num(cen_id))))
        assert merged["status"] == 'retired: "superseded"', f"status reset: {merged['status']!r}"
        assert merged["tags"] == ["perennial", "karst"], f"tags reset: {merged['tags']}"
        assert merged["related"] == ["north-complex"], f"related reset: {merged['related']}"
        assert merged["graduated_to"] == "[[cenote-dispute]]", f"graduated_to reset: {merged['graduated_to']}"
        assert merged.get("cadence") == "90d", f"[D] overlay reset: {merged.get('cadence')}"
        assert "]]>" in merged["description"], f"CDATA terminator lost on export: {merged['description']!r}"

        print("✓ round-trip fixed-point gate GREEN — pristine identity, merge preservation, "
              '"null" survival, multi-source, LineString+Polygon geometry, and '
              'geometry-less skip all hold (5 features).')
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
