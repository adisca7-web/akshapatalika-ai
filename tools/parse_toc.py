"""Parse the extracted Wiley GAAP text into a structured chapter/topic index.

Reads the extractor's full_text.txt and locates ASC topic chapters plus their
page offsets, so the skill generator can address one chapter at a time instead
of holding 813K tokens in context.

Emits structure only -- topic numbers, titles, offsets. No book prose.
"""

from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "extraction" / "full_text.txt"
OUT = ROOT / "extraction" / "toc.json"

# "ASC 606 Revenue from Contracts with Customers" style headings.
ASC_HEADING = re.compile(
    r"^\s*(?:\d+\s+)?ASC\s+(\d{3})\s+([A-Z][^\n]{2,90}?)\s*$",
    re.MULTILINE,
)
# Part dividers in the Wiley structure.
PART = re.compile(
    r"^\s*(I{1,3}V?|IV)\.\s+([A-Z][^\n]{5,90})\s*$",
    re.MULTILINE,
)


def normalise(title: str) -> str:
    t = re.sub(r"\s+", " ", title).strip()
    t = re.sub(r"[.\s]*\d+\s*$", "", t)  # trailing page numbers from ToC lines
    return t.strip(" .")


def main() -> int:
    text = TEXT.read_text(encoding="utf-8", errors="replace")
    print(f"loaded {len(text):,} chars")

    # -- topic occurrences ------------------------------------------------
    hits: OrderedDict[str, dict] = OrderedDict()
    for m in ASC_HEADING.finditer(text):
        topic, title = m.group(1), normalise(m.group(2))
        if len(title) < 4:
            continue
        rec = hits.setdefault(topic, {
            "topic": topic, "titles": {}, "offsets": [],
        })
        rec["titles"][title] = rec["titles"].get(title, 0) + 1
        rec["offsets"].append(m.start())

    # The body heading is the last substantial occurrence; ToC lines cluster
    # near the front of the file.
    topics = []
    for topic, rec in hits.items():
        title = max(rec["titles"].items(), key=lambda kv: (kv[1], -len(kv[0])))[0]
        offsets = sorted(rec["offsets"])
        body = offsets[-1] if len(offsets) > 1 else offsets[0]
        topics.append({
            "topic": topic,
            "title": title,
            "mentions": len(offsets),
            "toc_offset": offsets[0],
            "body_offset": body,
            "all_titles": sorted(rec["titles"], key=lambda t: -rec["titles"][t])[:3],
        })

    topics.sort(key=lambda t: t["topic"])

    # -- span estimation --------------------------------------------------
    by_offset = sorted(topics, key=lambda t: t["body_offset"])
    for i, t in enumerate(by_offset):
        end = by_offset[i + 1]["body_offset"] if i + 1 < len(by_offset) else len(text)
        t["span_chars"] = max(0, end - t["body_offset"])
        t["end_offset"] = end

    parts = [
        {"numeral": m.group(1), "title": normalise(m.group(2)), "offset": m.start()}
        for m in PART.finditer(text)
    ]

    def band(topic: str) -> str:
        n = int(topic)
        if n < 200:
            return "General Principles"
        if n < 300:
            return "Presentation"
        if n < 400:
            return "Assets"
        if n < 500:
            return "Liabilities"
        if n < 600:
            return "Equity"
        if n < 700:
            return "Revenue"
        if n < 800:
            return "Expenses"
        if n < 900:
            return "Broad Transactions"
        return "Industry"

    for t in topics:
        t["band"] = band(t["topic"])

    result = {
        "source": "Wiley GAAP 2020 (local copy)",
        "total_chars": len(text),
        "parts": parts[:12],
        "topic_count": len(topics),
        "topics": topics,
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"\nfound {len(topics)} ASC topics")
    bands: OrderedDict[str, list] = OrderedDict()
    for t in topics:
        bands.setdefault(t["band"], []).append(t)
    for b, ts in bands.items():
        print(f"\n== {b} ({len(ts)}) ==")
        for t in ts:
            print(f"  ASC {t['topic']:<4} {t['title'][:62]:<62} "
                  f"{t['span_chars']//1000:>5}k")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
