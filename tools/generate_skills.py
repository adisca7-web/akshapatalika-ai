"""Generate the GaapAccounting agent skill pack from the segmented book.

Each Wiley chapter opens with a hierarchical contents outline and then repeats
those headings over the body. That structure is the skill hierarchy: the chapter
is a skill, its top-level outline entries are subskills, and the "Example:"
entries are the worked references. Recovering it mechanically means the pack
mirrors the book's own organisation rather than an organisation I invented.

Emits, per book-to-skill's SKILL.md spec:
    chapters/chNN-<slug>.md     64 topic skills
    industries/ascNNN-<slug>.md 20 industry subskill packs
    _index.json                 machine-readable catalog

The authored layers (SKILL.md, cheatsheet, patterns, glossary) are written
separately; this script produces the deterministic scaffolding that they index.

No raw book prose is copied. What is emitted is structure -- headings, ASC
citation keys, ASU identifiers, and example titles -- which is reference
apparatus, not the text itself.
"""

from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEG = ROOT / "extraction" / "segments"
OUT = ROOT / "skills" / "gaap-accounting"

CITATION = re.compile(r"\bASC\s+(\d{3})-(\d{2})(?:-(\d{2}))?(?:-(\d{1,3}[A-Za-z]?))?")
ASU = re.compile(r"\bASU\s+(\d{4}-\d{2})\b")
SUBTOPIC = re.compile(r"\bASC\s+(\d{3}-\d{2})\s*,\s*([A-Z][^,.\n]{3,70})")


def is_outline_line(s: str) -> bool:
    """Outline entries are short, title-ish, and unpunctuated."""
    t = s.strip()
    if not (2 < len(t) <= 78):
        return False
    if t.endswith((".", ";", ":", ",")):
        return False
    if re.match(r"^[\d.]+$", t):
        return False
    # Must start with a letter or a digit-step label ("Step 1:").
    return bool(re.match(r"^[A-Z0-9]", t))


def find_outline(lines: list) -> tuple:
    """Return (outline_entries, body_start_index).

    The outline runs until prose begins. Prose is detected as a run of lines
    that are long or sentence-terminated -- outline entries are neither.
    """
    entries = []
    body_start = 0
    run = 0
    for i, raw in enumerate(lines[:1400]):
        s = raw.strip()
        if not s:
            continue
        prose = len(s) > 88 or (s.endswith(".") and len(s) > 55)
        if prose:
            run += 1
            if run >= 3:
                body_start = i - 2
                break
        else:
            run = 0
            if is_outline_line(raw):
                entries.append((len(raw) - len(raw.lstrip()), s, i))
    if not body_start:
        body_start = entries[-1][2] + 1 if entries else 0
    return entries, body_start


def pick_sections(entries: list, body: str) -> tuple:
    """Split outline entries into major sections and their subsections.

    Indentation is unreliable across page breaks, so an entry is promoted to a
    major section when it is at the shallowest common indent AND recurs in the
    body (a real heading is printed again above its text).
    """
    if not entries:
        return [], []
    indents = sorted({e[0] for e in entries})
    shallow = set(indents[:2]) if len(indents) > 1 else set(indents[:1])

    body_upper = body.upper()

    majors, subs = [], []
    seen = set()
    for indent, title, _ in entries:
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        recurs = body_upper.count(title.upper()) >= 1
        if indent in shallow and recurs and not title.lower().startswith("example"):
            majors.append(title)
        else:
            subs.append(title)
    return majors, subs


def body_headings(lines: list) -> list:
    """Recover section headings directly from the body.

    The industry sections sit inside chapter 64 and have no contents block of
    their own, so there is no outline to read. Their headings are recoverable
    typographically instead: a short, unpunctuated, capitalised line sitting
    alone between blank lines is a heading; a line of running prose is not.
    """
    heads: "OrderedDict[str, int]" = OrderedDict()
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not (2 < len(s) <= 72):
            continue
        if s.endswith((".", ",", ";", ":", "?")):
            continue
        if not re.match(r"^[A-Z]", s):
            continue
        if re.search(r"\d{3}-\d{2}", s):  # a citation, not a heading
            continue
        prev_blank = i == 0 or not lines[i - 1].strip()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not prev_blank:
            continue
        if not nxt:  # heading followed by blank then text is still a heading
            nxt = lines[i + 2].strip() if i + 2 < len(lines) else ""
        if not nxt:
            continue
        # Headings are followed by prose, not by another short fragment.
        if len(nxt) < 30:
            continue
        words = s.split()
        if not (1 <= len(words) <= 10):
            continue
        capitalised = sum(1 for w in words if w[:1].isupper())
        if capitalised / len(words) < 0.6:
            continue
        heads[s] = heads.get(s, 0) + 1
    return list(heads)


def citations_of(block: str, limit: int = 260) -> list:
    found = OrderedDict()
    for m in CITATION.finditer(block):
        parts = [m.group(1), m.group(2)]
        if m.group(3):
            parts.append(m.group(3))
        if m.group(4):
            parts.append(m.group(4))
        found["-".join(parts)] = None
    return list(found)[:limit]


def subtopics_of(block: str) -> list:
    out = OrderedDict()
    for m in SUBTOPIC.finditer(block):
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        if 3 < len(title) < 70:
            out[m.group(1)] = title
    return [{"subtopic": k, "title": v} for k, v in out.items()][:24]


def examples_of(entries: list, block: str) -> list:
    """Worked examples the chapter contains, by title."""
    out = OrderedDict()
    for _, title, _ in entries:
        if title.lower().startswith("example"):
            t = re.sub(r"^Example\s*[:\u2014-]\s*", "", title).strip()
            if t:
                out[t] = None
    for m in re.finditer(r"^\s*Example[:\u2014-]\s*(.{4,70})$", block, re.MULTILINE):
        t = m.group(1).strip().rstrip(".")
        if t and not t.endswith(","):
            out.setdefault(t, None)
    return list(out)[:40]


def asus_of(block: str) -> list:
    return sorted({m.group(1) for m in ASU.finditer(block)})


def md_escape(s: str) -> str:
    return s.replace("|", "\\|")


def render(kind: str, meta: dict, data: dict) -> str:
    """Render one chapter or industry skill file."""
    L = []
    asc_label = meta.get("asc_label")
    L.append(f"# ASC {asc_label} \u2014 {meta['title']}")
    L.append("")
    L.append(f"> {meta['provenance']}")
    L.append("")

    if data["majors"]:
        L.append("## Subskills")
        L.append("")
        L.append("The sections this topic decomposes into. Ask for one by name.")
        L.append("")
        for s in data["majors"]:
            L.append(f"- **{md_escape(s)}**")
        L.append("")

    if data["subtopics"]:
        L.append("## Codification subtopics")
        L.append("")
        L.append("| Subtopic | Title |")
        L.append("|---|---|")
        for st in data["subtopics"]:
            L.append(f"| ASC {st['subtopic']} | {md_escape(st['title'])} |")
        L.append("")

    if data["subs"]:
        L.append("## Detail index")
        L.append("")
        L.append("<details><summary>"
                 f"{len(data['subs'])} detailed headings</summary>")
        L.append("")
        for s in data["subs"]:
            L.append(f"- {md_escape(s)}")
        L.append("")
        L.append("</details>")
        L.append("")

    if data["examples"]:
        L.append("## Worked examples in the source")
        L.append("")
        L.append("Illustrations the chapter works through end to end. "
                 "Cite these when a question needs a concrete pattern.")
        L.append("")
        for e in data["examples"]:
            L.append(f"- {md_escape(e)}")
        L.append("")

    if data["asus"]:
        L.append("## Standards updates referenced")
        L.append("")
        L.append(", ".join(f"ASU {a}" for a in data["asus"]))
        L.append("")

    if data["citations"]:
        L.append("## ASC references cited")
        L.append("")
        L.append(f"{len(data['citations'])} paragraph-level references appear in "
                 "this topic. Use these as the authority column of a workpaper.")
        L.append("")
        L.append("<details><summary>Show references</summary>")
        L.append("")
        # Group by subtopic for readability.
        groups: "OrderedDict[str, list]" = OrderedDict()
        for c in data["citations"]:
            parts = c.split("-")
            groups.setdefault("-".join(parts[:2]), []).append(c)
        for g, items in groups.items():
            L.append(f"- **ASC {g}** \u2014 " + ", ".join(items))
        L.append("")
        L.append("</details>")
        L.append("")

    L.append("## Source")
    L.append("")
    L.append(f"- Segment: `{meta['segment']}`")
    L.append(f"- Extent: {meta['words']:,} words")
    L.append("")
    return "\n".join(L)


def analyse(block: str) -> dict:
    """Build the structural payload for one chapter or industry section."""
    lines = block.split("\n")
    entries, body_start = find_outline(lines)
    body = "\n".join(lines[body_start:])
    majors, subs = pick_sections(entries, body)

    # Sections with no contents block of their own (every industry) fall back
    # to typographic heading recovery over the body.
    if len(majors) < 3:
        recovered = body_headings(lines)
        known = {m.lower() for m in majors} | {s.lower() for s in subs}
        for h in recovered:
            if h.lower() not in known:
                majors.append(h)
                known.add(h.lower())

    # Wiley's three structural banners repeat in every chapter, so they carry no
    # information about what a topic actually covers. Drop them from the
    # subskill list rather than presenting them as capabilities.
    BANNERS = {"perspective and issues", "definitions of terms",
               "concepts, rules, and examples", "concepts and rules",
               "overview", "scope", "scope and scope exceptions",
               "technical alert", "subtopics", "subtopic"}
    majors = [m for m in majors if m.strip().lower() not in BANNERS]
    subs = [s for s in subs if s.strip().lower() not in BANNERS]

    return {
        "majors": majors[:40],
        "subs": subs[:120],
        "subtopics": subtopics_of(block),
        "examples": examples_of(entries, block),
        "asus": asus_of(block),
        "citations": citations_of(block),
    }


def main() -> int:
    index = json.loads((SEG / "index.json").read_text(encoding="utf-8"))
    (OUT / "chapters").mkdir(parents=True, exist_ok=True)
    (OUT / "industries").mkdir(parents=True, exist_ok=True)

    catalog = {"chapters": [], "industries": []}

    for ch in index["chapters"]:
        block = (SEG / ch["file"]).read_text(encoding="utf-8")
        data = analyse(block)
        majors = data["majors"]
        meta = {
            "asc_label": ch["asc"],
            "title": ch["title"].title().replace("Asc", "ASC"),
            "words": ch["words"],
            "segment": ch["file"],
            "provenance": (
                f"Chapter {ch['chapter']} of *Wiley GAAP 2020: Interpretation and "
                "Application of Generally Accepted Accounting Principles*. "
                "Structure extracted locally; no source text reproduced."
            ),
        }
        name = f"ch{ch['chapter']:02d}-{ch['slug']}.md"
        (OUT / "chapters" / name).write_text(render("chapter", meta, data),
                                            encoding="utf-8")
        catalog["chapters"].append({
            "chapter": ch["chapter"], "asc": ch["asc"], "title": meta["title"],
            "file": f"chapters/{name}", "subskills": majors,
            "examples": len(data["examples"]), "citations": len(data["citations"]),
            "words": ch["words"],
        })

    for ind in index["industries"]:
        block = (SEG / ind["file"]).read_text(encoding="utf-8")
        data = analyse(block)
        majors = data["majors"]
        meta = {
            "asc_label": ", ".join(ind["asc"]),
            "title": ind["title"],
            "words": ind["words"],
            "segment": ind["file"],
            "provenance": (
                "Specialized industry GAAP, chapter 64 of *Wiley GAAP 2020*. "
                "Structure extracted locally; no source text reproduced."
            ),
        }
        # Industry files are hand-authored from the source rather than
        # scaffolded, so never clobber one that already exists. The generator
        # only fills gaps and keeps the catalog pointing at the real file.
        existing = sorted((OUT / "industries").glob(f"asc{ind['primary']}-*.md"))
        if existing:
            name = existing[0].name
        else:
            name = f"asc{ind['primary']}-{ind['slug']}.md"
            (OUT / "industries" / name).write_text(render("industry", meta, data),
                                                   encoding="utf-8")
        catalog["industries"].append({
            "asc": ind["asc"], "primary": ind["primary"], "title": ind["title"],
            "file": f"industries/{name}", "subskills": majors,
            "examples": len(data["examples"]), "citations": len(data["citations"]),
            "words": ind["words"],
        })

    (OUT / "_index.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    print(f"chapters written : {len(catalog['chapters'])}")
    print(f"industries written: {len(catalog['industries'])}")
    print("\n=== industry subskill counts ===")
    for i in catalog["industries"]:
        print(f"  ASC {i['primary']:<5} {i['title'][:40]:<40} "
              f"{len(i['subskills']):>3} subskills  {i['examples']:>3} ex  "
              f"{i['citations']:>4} cit")
    print("\n=== chapters with most subskills ===")
    for c in sorted(catalog["chapters"], key=lambda x: -len(x["subskills"]))[:14]:
        print(f"  ch{c['chapter']:02d} ASC {c['asc']:<5} {c['title'][:36]:<36} "
              f"{len(c['subskills']):>3} subskills  {c['examples']:>3} ex")
    tot = sum(len(c["subskills"]) for c in catalog["chapters"]) + \
          sum(len(i["subskills"]) for i in catalog["industries"])
    print(f"\ntotal subskills: {tot}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
