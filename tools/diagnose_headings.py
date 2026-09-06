"""List every candidate chapter opening with the evidence around it.

A real chapter body opens with an "ASC NNN <TITLE>" heading and reaches
PERSPECTIVE AND ISSUES shortly after. Cross-references and per-chapter contents
lists also start with "ASC NNN", so this prints the distance to the nearest
section banner for each candidate, which is what separates them.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "extraction" / "full_text.txt"
FIXES = {
    "\u00e2\u0080\u0094": "\u2014", "\u00e2\u0080\u0093": "\u2013",
    "\u00e2\u0080\u0099": "'", "\u00e2\u0080\u009c": '"',
    "\u00e2\u0080\u009d": '"', "\u00e2\u0080\u0098": "'",
    "\u00ef\u00ac\u0081": "fi", "\u00ef\u00ac\u0082": "fl",
    "\u00e2\u0080\u00a2": "-", "\u00c2\u00a0": " ",
}
text = TEXT.read_text(encoding="utf-8", errors="replace")
for b, g in FIXES.items():
    text = text.replace(b, g)
lines = text.split("\n")
n = len(lines)

BANNERS = ("PERSPECTIVE AND ISSUES", "DEFINITIONS OF TERMS",
           "CONCEPTS, RULES, AND EXAMPLES")
HEAD = re.compile(r"^\s*(?:\d{1,2}\s+)?ASC\s+(\d{3}[a-z]?s?)\s*(.*)$")

TOC_END = 500

def dist_to_banner(i: int, span: int = 500) -> int:
    for d in range(span):
        j = i + d
        if j >= n:
            break
        if lines[j].strip().upper().startswith(BANNERS):
            return d
    return -1

targets = {"605", "606", "320", "321", "323", "325", "326", "330", "215", "430"}
print(f"{'line':>7} {'asc':<6} {'d2banner':>8}  heading text")
print("-" * 92)
for i in range(TOC_END, n):
    m = HEAD.match(lines[i])
    if not m:
        continue
    asc = m.group(1)
    if asc not in targets:
        continue
    rest = m.group(2).strip()
    d = dist_to_banner(i)
    # Only show plausible openings: heading line is mostly a title, not prose.
    if len(rest) > 60:
        continue
    nxt = " | ".join(l.strip() for l in lines[i + 1:i + 4] if l.strip())[:56]
    print(f"{i:>7} {asc:<6} {d:>8}  {rest[:34]:<34} >> {nxt}")
