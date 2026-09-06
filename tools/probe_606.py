"""Show the raw context around every plausible ASC 605 / 606 / 430 chapter opening."""

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

for target in ("605", "606", "430"):
    print("=" * 88)
    print(f"ASC {target}")
    print("=" * 88)
    pat = re.compile(rf"^\s*(?:\d{{1,2}}\s+)?ASC\s+{target}\s*(.*)$")
    shown = 0
    for i in range(500, len(lines)):
        m = pat.match(lines[i])
        if not m:
            continue
        rest = m.group(1).strip()
        if len(rest) > 45 or rest.startswith((",", "-", ".")):
            continue
        letters = [c for c in rest if c.isalpha()]
        if letters and sum(1 for c in letters if c.isupper()) / len(letters) < 0.9:
            continue
        print(f"\n--- line {i} ---")
        for j in range(i, min(i + 12, len(lines))):
            mark = ">>" if j == i else "  "
            print(f"{mark} {j:>6} | {lines[j][:96]}")
        shown += 1
        if shown >= 6:
            break
    if shown == 0:
        print("  (no caps-title candidate found)")
