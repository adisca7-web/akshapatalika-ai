"""Probe the extracted text to find reliable chapter and section boundaries."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "extraction" / "full_text.txt"
raw = TEXT.read_text(encoding="utf-8", errors="replace")

# The extractor read a cp1252 file as UTF-8 in places; repair the common cases.
FIXES = {
    "\u00e2\u0080\u0094": "\u2014",  # em dash
    "\u00e2\u0080\u0093": "\u2013",  # en dash
    "\u00e2\u0080\u0099": "'",
    "\u00e2\u0080\u009c": '"',
    "\u00e2\u0080\u009d": '"',
    "\u00e2\u0080\u0098": "'",
    "\u00ef\u00ac\u0081": "fi",
    "\u00e2\u0080\u00a2": "-",
}
text = raw
for bad, good in FIXES.items():
    text = text.replace(bad, good)

print(f"chars: {len(text):,}")
print(f"mojibake remaining: {text.count(chr(0xe2) + chr(0x80))}")

lines = text.split("\n")
print(f"lines: {len(lines):,}\n")

# -- candidate chapter headings: "NN ASC NNN TITLE" ----------------------
pat = re.compile(r"^\s*(\d{1,2})\s+ASC\s+(\d{3}[a-z]?s?)\s+(.{3,80})$")
hits = []
for i, ln in enumerate(lines):
    m = pat.match(ln.rstrip())
    if m:
        hits.append((i, int(m.group(1)), m.group(2), m.group(3).strip()))

print(f"'NN ASC NNN TITLE' matches: {len(hits)}")
seen = Counter(h[1] for h in hits)
print(f"distinct chapter numbers: {len(seen)}  range {min(seen) if seen else '-'}..{max(seen) if seen else '-'}")

# Show first and last occurrence of a few chapter numbers to separate ToC from body
for num in (1, 2, 30, 57, 64):
    occ = [h for h in hits if h[1] == num]
    if occ:
        print(f"\nch{num}: {len(occ)} occurrence(s)")
        for o in occ[:6]:
            print(f"   line {o[0]:>7}  ASC {o[2]:<5} {o[3][:56]}")

# -- section markers -----------------------------------------------------
print("\n=== section markers ===")
for marker in ("PERSPECTIVE AND ISSUES", "DEFINITIONS OF TERMS",
               "CONCEPTS, RULES, AND EXAMPLES", "Technical Alert",
               "Scope", "ASC 9"):
    c = sum(1 for ln in lines if ln.strip().startswith(marker))
    print(f"  lines starting with {marker!r}: {c}")

# -- industry headings inside the 900s chapter ---------------------------
print("\n=== industry headings (TITLE (ASC NNN)) ===")
ind = re.compile(r"^\s*([A-Z][A-Z\u2014\u2013 ,'&/-]{4,70})\s*\(ASC\s+(9\d{2}(?:,\s*ASC\s+9\d{2})*)\)\s*$")
found = []
for i, ln in enumerate(lines):
    m = ind.match(ln.rstrip())
    if m:
        found.append((i, m.group(1).strip(), m.group(2)))
print(f"matches: {len(found)}")
for i, title, asc in found:
    print(f"   line {i:>7}  ASC {asc:<24} {title[:52]}")
