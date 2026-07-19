#!/usr/bin/env python3
"""
rasa.module.atlas — live watch loop.

Watches the site records (atlas/sites/**/site-*.md) and the color-key seam, and re-runs
the exporter whenever their CONTENT changes, so a Google Earth NetworkLink
(atlas-live.kml) picks up your edits hands-free. Standard library only; Ctrl-C to stop.

    python3 watch.py <atlas_root> <atlas_canon.md> [interval_seconds]

Change detection is a content digest, not mtime — so it is correct on coarse-mtime
volumes (this workspace's HFS/USB carries 1-second mtime, on which two same-second edits
share an mtime) and to mtime-preserving restores, and it ignores a pure `touch`. No
self-trigger: the exporter writes atlas.kml / atlas.geojson / atlas-live.kml into the
atlas ROOT, while this watches sites/ + the seam. A failed export (e.g. an unknown
category) is reported and does not stop the loop; fix the seam and the next save
re-exports.
"""

import glob
import hashlib
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INTERVAL = 1.0
DEBOUNCE = 0.4          # let a burst of saves settle before exporting


def _watched(atlas_root, canon):
    paths = glob.glob(os.path.join(atlas_root, "sites", "*", "site-*.md"))
    if os.path.exists(canon):
        paths.append(canon)
    return paths


def signature(atlas_root, canon):
    """A CONTENT signature over the watched set — an md5 over each file's path + length
    + bytes. Detects any content change, add, or delete regardless of mtime granularity,
    so it is correct on coarse-mtime volumes and on mtime-preserving restores that a
    stat-only (count, max-mtime) signature would silently miss — and it ignores a pure
    `touch` (identical content ⇒ identical export). ~25ms for a 1200-file corpus, reads
    only (never a sync-triggering write); raise the poll interval for a very large one."""
    h = hashlib.md5()
    for p in sorted(_watched(atlas_root, canon)):
        try:
            with open(p, "rb") as f:
                data = f.read()
        except OSError:
            continue    # vanished mid-scan — its absence shifts the digest next tick
        h.update(p.encode("utf-8"))
        h.update(b"\0")
        h.update(str(len(data)).encode("ascii"))
        h.update(b"\0")
        h.update(data)
    return h.hexdigest()


def run_export(atlas_root, canon):
    """Run `export.py <root> <canon> both`. Returns (ok, message)."""
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "export.py"), atlas_root, canon, "both"],
        capture_output=True, text=True,
    )
    out = (r.stdout or "") + (r.stderr or "")
    return r.returncode == 0, out.strip()


def _headline(ok, msg):
    """One status line — strip any glyph the exporter already printed so ours isn't doubled."""
    head = (msg.splitlines()[0] if msg else "exported").lstrip("✓✗⚠ ").strip()
    return ("✓ " if ok else "✗ ") + head


def watch(atlas_root, canon, interval=DEFAULT_INTERVAL):
    try:
        sys.stdout.reconfigure(line_buffering=True)   # stream each line even when piped
    except (AttributeError, ValueError):
        pass
    n = len(_watched(atlas_root, canon))
    live = os.path.abspath(os.path.join(atlas_root, "atlas-live.kml"))
    print(f"atlas watch — {n} record(s), re-exporting on change (every {interval}s poll).")
    print(f"  open once in Google Earth Pro:  {live}")
    print("  Ctrl-C to stop.\n")

    try:
        # Prime once so the map is current; arm on the PRE-export snapshot so an edit
        # that lands DURING any export is seen by the next poll and re-fires (the
        # exporter never writes a watched file, so absent a during-export edit the
        # next signature equals this one and there is no spurious re-export).
        last = signature(atlas_root, canon)
        ok, msg = run_export(atlas_root, canon)
        print("  " + _headline(ok, msg))

        while True:
            time.sleep(interval)
            sig = signature(atlas_root, canon)
            if sig == last:
                continue
            time.sleep(DEBOUNCE)                    # let a save burst settle
            sig = signature(atlas_root, canon)      # settled pre-export snapshot
            last = sig                              # arm BEFORE exporting
            ok, msg = run_export(atlas_root, canon)
            stamp = time.strftime("%H:%M:%S")
            print(f"  [{stamp}] {_headline(ok, msg)}")
            if not ok:
                for line in msg.splitlines()[1:6]:
                    print(f"           {line}")
    except KeyboardInterrupt:
        print("\natlas watch — stopped.")
        return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    atlas_root, canon = argv[0], argv[1]
    interval = DEFAULT_INTERVAL
    if len(argv) > 2:
        try:
            interval = float(argv[2])
        except ValueError:
            interval = 0.0
        if interval <= 0:
            print(f"  (ignoring invalid interval {argv[2]!r}; using {DEFAULT_INTERVAL}s)")
            interval = DEFAULT_INTERVAL
    return watch(atlas_root, canon, interval)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
