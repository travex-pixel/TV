#!/usr/bin/env python3
"""Which CleanYourTV example profiles match this TV's firmware? Read-only, offline.

Usage: python3 tools/match-profile.py discovery/<timestamp>

Reads getprop.txt from a tv-discover run and scores every cleanyourtv/examples/*/debloat.txt
header by the identifiers it mentions (device, product, board, build id, SDK). A match on the
device/product codename counts far more than a match on the generic "Smart TV Pro" model name.
It prints candidates only; nothing is applied.
"""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit(__doc__)
run = Path(sys.argv[1])
props = {}
for line in (run / "getprop.txt").read_text(errors="replace").splitlines():
    m = re.match(r"\[(.+?)\]: \[(.*)\]", line)
    if m:
        props[m.group(1)] = m.group(2)

def p(k):
    return props.get(k, "").strip()

weights = [
    (p("ro.product.device"), 5), (p("ro.product.name"), 5), (p("ro.build.version.incremental"), 4),
    (p("ro.software.version_id"), 4), (p("ro.board.platform"), 3), (p("ro.hardware"), 2),
    (p("ro.build.display.id"), 2), (p("ro.product.model"), 1),
]
sdk = p("ro.build.version.sdk"); rel = p("ro.build.version.release")
print(f"TV: model={p('ro.product.model')} device={p('ro.product.device')} product={p('ro.product.name')} "
      f"android={rel} sdk={sdk} build={p('ro.build.display.id')} incremental={p('ro.build.version.incremental')}")
root = Path(__file__).resolve().parent.parent / "cleanyourtv" / "examples"
scored = []
for lst in sorted(root.glob("*/debloat.txt")):
    header = "\n".join(l for l in lst.read_text(errors="replace").splitlines() if l.startswith("#"))
    score, hits = 0, []
    for value, w in weights:
        if len(value) >= 3 and re.search(re.escape(value), header, re.IGNORECASE):
            score += w; hits.append(value)
    if rel and re.search(rf"Android (TV )?{re.escape(rel)}\b|Google TV {re.escape(rel)}\b", header):
        score += 1; hits.append(f"Android {rel}")
    if score:
        scored.append((score, lst.parent.name, hits))
scored.sort(reverse=True)
if not scored:
    print("No example profile mentions this firmware. A list will have to be built from the package inventory.")
for score, name, hits in scored[:8]:
    print(f"  {score:2d}  examples/{name:34s} matched: {', '.join(hits)}")
print("\nA score of 10+ (device or product codename plus build) means the same board and firmware family.\n"
      "Scores from only 'Smart TV Pro' or the Android version alone prove nothing; TCL reuses those names.")
