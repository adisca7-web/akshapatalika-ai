"""Segment the extracted Wiley GAAP text into addressable chapters and industries.

Deterministic pass. Produces, under extraction/segments/:

  chapters/chNN.txt     one source slice per chapter (64)
  industries/ascNNN.txt one slice per specialized-industry topic (20)
  index.json            chapter/industry offsets, ASC citations, defined terms

Nothing here is summarised or interpreted -- it is pure structure recovery, so
the generation pass can address one chapter at a time instead of holding 813K
tokens of book in context.

The extracted slices stay local and are gitignored: they are raw copyrighted
text, and only the synthesised skill files are meant to persist.
"""

from __future__ import annotations

import json
import re
import sys
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = ROOT / "extraction" / "full_text.txt"
OUTDIR = ROOT / "extraction" / "segments"

# The PDF layer mixed cp1252 bytes into UTF-8; repair before matching.
FIXES = {
    "\u00e2\u0080\u0094": "\u2014", "\u00e2\u0080\u0093": "\u2013",
    "\u00e2\u0080\u0099": "'", "\u00e2\u0080\u009c": '"',
    "\u00e2\u0080\u009d": '"', "\u00e2\u0080\u0098": "'",
    "\u00ef\u00ac\u0081": "fi", "\u00ef\u00ac\u0082": "fl",
    "\u00e2\u0080\u00a2": "-", "\u00e2\u0080\u00a6": "...",
    "\u00c2\u00a0": " ",
}

TOC_CHAPTER = re.compile(r"^\s*(\d{1,2})\s+ASC\s+(\d{3}[a-z]?s?)\s+(.{3,80})$")
# Industry headings wrap unpredictably, so match on the parenthesised ASC ref
# and take the preceding capitalised run as the title.
INDUSTRY_REF = re.compile(r"\(ASC\s+(9\d{2}(?:\s*,\s*ASC\s+9\d{2})*)\)")
CITATION = re.compile(r"\bASC\s+(\d{3})-(\d{2})(?:-(\d{2}))?(?:-(\d{1,3}[A-Za-z]?))?")
SECTION_MARKERS = (
    "PERSPECTIVE AND ISSUES",
    "DEFINITIONS OF TERMS",
    "CONCEPTS, RULES, AND EXAMPLES",
)


def repair(text: str) -> str:
    for bad, good in FIXES.items():
        text = text.replace(bad, good)
    return text


def slugify(title: str) -> str:
    s = title.lower()
    s = s.replace("\u2014", "-").replace("\u2013", "-").replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return re.sub(r"-+", "-", s).strip("-")[:52]


def main() -> int:
    text = repair(TEXT.read_text(encoding="utf-8", errors="replace"))
    lines = text.split("\n")
    n = len(lines)
    print(f"lines: {n:,}  chars: {len(text):,}")

    # ---------------------------------------------------------------
    # 1. Chapter list from the table of contents
    # ---------------------------------------------------------------
    toc: "OrderedDict[int, dict]" = OrderedDict()
    for i, ln in enumerate(lines[:1200]):
        m = TOC_CHAPTER.match(ln.rstrip())
        if not m:
            continue
        num = int(m.group(1))
        if num in toc:
            continue
        toc[num] = {
            "chapter": num,
            "asc": m.group(2),
            "title": re.sub(r"\s+", " ", m.group(3)).strip(),
            "toc_line": i,
        }
    print(f"chapters in ToC: {len(toc)}")
    toc_end = max(v["toc_line"] for v in toc.values()) + 40

    # ---------------------------------------------------------------
    # 2. Locate each chapter's body start
    # ---------------------------------------------------------------
    # Chapters appear in the body in the same order as the ToC, so the scan
    # carries a cursor and never looks backwards. Searching each chapter
    # independently lets an early cross-reference ("see ASC 606") win, which
    # makes that chapter start hundreds of pages too soon and swallow every
    # chapter between. The cursor is what prevents that.
    # Three signals separate a real chapter opening from the hundreds of
    # cross-references and subtopic lists that also begin "ASC NNN":
    #   1. the remainder of the line is an ALL-CAPS title, not prose and not a
    #      subtopic tail like ", Investments-Other" or "-10-45-1";
    #   2. a section banner (Perspective and Issues) follows within a few lines,
    #      because titles wrap but the banner always comes straight after;
    #   3. openings appear in ToC order, so the scan never looks backwards.

    def banner_distance(i: int, span: int = 10) -> int:
        for d in range(span):
            j = i + d
            if j >= n:
                break
            if lines[j].strip().upper().startswith(SECTION_MARKERS):
                return d
        return -1

    def is_caps_title(rest: str) -> bool:
        letters = [c for c in rest if c.isalpha()]
        if not letters:
            return True  # title wrapped entirely onto the next line
        upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
        return upper_ratio >= 0.9 and len(rest) <= 60

    # The banner is not a reliable opening marker after all: the larger chapters
    # (ASC 605, 606) open with a contents outline instead, and stub chapters
    # (ASC 430 is ten lines that just point at ASC 605-50) have no banner at
    # all. Matching the ToC title is what actually discriminates, because a
    # cross-reference never restates the full chapter title.
    def title_tokens(title: str) -> list:
        words = re.findall(r"[A-Z]{4,}", title.upper())
        stop = {"FROM", "WITH", "OTHER", "THE", "AND", "FOR"}
        return [w for w in words if w not in stop]

    cursor = toc_end
    for num in sorted(toc):
        ch = toc[num]
        toks = title_tokens(ch["title"])
        pat = re.compile(
            rf"^\s*(?:\d{{1,2}}\s+)?ASC\s+{re.escape(ch['asc'])}\s*(.*)$"
        )
        found = None
        for i in range(cursor, n):
            m = pat.match(lines[i])
            if not m:
                continue
            rest = m.group(1).strip()
            if rest.startswith((",", "-", ".")):
                continue
            if not is_caps_title(rest):
                continue
            if toks:
                # Titles wrap, so score across a short window rather than one line.
                window = " ".join(lines[i:i + 3]).upper()
                if sum(1 for t in toks if t in window) / len(toks) < 0.6:
                    continue
            found = i
            break
        ch["body_line"] = found
        if found is not None:
            cursor = found + 1

    print(f"chapter openings matched by title: "
          f"{sum(1 for c in toc.values() if c['body_line'] is not None)}")

    located = [c for c in toc.values() if c["body_line"] is not None]
    print(f"chapter bodies located: {len(located)} / {len(toc)}")

    # The back matter must not be swallowed by the last chapter. Appendix A is
    # the book-wide definitions list, which is the natural glossary source, so
    # it is worth isolating rather than leaving inside ASC 985.
    APPENDIX = re.compile(r"^\s*APPENDIX\s+([AB])\b(.*)$")
    appendices = []
    last_body = max((c["body_line"] for c in located), default=toc_end)
    for i in range(last_body, n):
        m = APPENDIX.match(lines[i])
        if not m:
            continue
        # Skip the ToC echo; the real appendix has substantial text after it.
        if len("\n".join(lines[i:i + 40]).strip()) < 400:
            continue
        appendices.append({"letter": m.group(1), "line": i,
                           "title": m.group(2).strip()})
    # Keep the first occurrence of each letter after the last chapter.
    seen_letters = {}
    for a in appendices:
        seen_letters.setdefault(a["letter"], a)
    appendices = sorted(seen_letters.values(), key=lambda a: a["line"])
    back_matter_start = appendices[0]["line"] if appendices else n
    print(f"back matter starts at line {back_matter_start} "
          f"({len(appendices)} appendix section(s))")

    # Order by position and derive end boundaries.
    ordered = sorted(located, key=lambda c: c["body_line"])
    for i, ch in enumerate(ordered):
        ch["end_line"] = (ordered[i + 1]["body_line"] if i + 1 < len(ordered)
                          else back_matter_start)

    # Chapters whose heading was not found fall back to interpolation between
    # their located neighbours so no chapter is silently dropped.
    for num, ch in toc.items():
        if ch["body_line"] is None:
            prev = [c for c in ordered if c["chapter"] < num]
            nxt = [c for c in ordered if c["chapter"] > num]
            ch["body_line"] = prev[-1]["end_line"] if prev else toc_end
            ch["end_line"] = nxt[0]["body_line"] if nxt else n
            ch["inferred"] = True

    # ---------------------------------------------------------------
    # 3. Industry sections inside chapter 64
    # ---------------------------------------------------------------
    ind_chapter = toc.get(64)
    industries = []
    if ind_chapter:
        lo = ind_chapter["body_line"]
        hi = ind_chapter["end_line"]
        raw_hits = []
        # Industry headings wrap mid-reference ("... (ASC" / "946)"), so match
        # against a joined two-line window rather than a single line.
        for i in range(lo, min(hi, n) - 1):
            window = lines[i].rstrip() + " " + lines[i + 1].strip()
            m = INDUSTRY_REF.search(window)
            if not m:
                continue
            refs = re.findall(r"9\d{2}", m.group(1))
            before = window[:m.start()].strip()
            if len(before) < 4:
                before = lines[i - 1].strip() if i > lo else ""
            title = re.sub(r"\s+", " ", before).strip(" -\u2014")
            letters = [c for c in title if c.isalpha()]
            if not letters:
                continue
            # Section headings are set in caps; running-text mentions are not.
            if sum(1 for c in letters if c.isupper()) / len(letters) < 0.85:
                continue
            if banner_distance(i, 12) < 0:
                continue
            raw_hits.append((i, tuple(refs), title))

        # The chapter repeats its own contents list before the body; keep the
        # last occurrence of each topic, which is the real section.
        by_topic: "OrderedDict[tuple, tuple]" = OrderedDict()
        for i, refs, title in raw_hits:
            by_topic[refs] = (i, refs, title)
        picked = sorted(by_topic.values(), key=lambda x: x[0])
        for j, (i, refs, title) in enumerate(picked):
            end = picked[j + 1][0] if j + 1 < len(picked) else hi
            industries.append({
                "asc": list(refs),
                "primary": refs[0],
                "title": title.title().replace("Asc", "ASC"),
                "start_line": i,
                "end_line": end,
            })
    print(f"industry sections: {len(industries)}")

    # ---------------------------------------------------------------
    # 4. Write slices + build the reference index
    # ---------------------------------------------------------------
    (OUTDIR / "chapters").mkdir(parents=True, exist_ok=True)
    (OUTDIR / "industries").mkdir(parents=True, exist_ok=True)

    def citations_in(block: str, limit: int = 400) -> list:
        found = OrderedDict()
        for m in CITATION.finditer(block):
            parts = [m.group(1), m.group(2)]
            if m.group(3):
                parts.append(m.group(3))
            if m.group(4):
                parts.append(m.group(4))
            found["-".join(parts)] = None
        return list(found)[:limit]

    def defined_terms(block_lines: list) -> list:
        """Pull the DEFINITIONS OF TERMS section's bolded term entries.

        pdftotext loses bold, so terms are recovered structurally: inside the
        definitions section, a short Title Case line followed by prose is a term.
        """
        terms = []
        try:
            start = next(i for i, line in enumerate(block_lines)
                         if line.strip().upper().startswith("DEFINITIONS OF TERMS"))
        except StopIteration:
            return terms
        for i in range(start + 1, min(start + 900, len(block_lines))):
            s = block_lines[i].strip()
            if s.upper().startswith("CONCEPTS, RULES"):
                break
            if not (3 < len(s) < 68):
                continue
            if s.endswith((".", ",", ";", ":")):
                continue
            if not re.match(r"^[A-Z][A-Za-z0-9 ,'()/\u2014\u2013-]+$", s):
                continue
            if s.isupper():
                continue
            words = s.split()
            if not (1 <= len(words) <= 8):
                continue
            nxt = block_lines[i + 1].strip() if i + 1 < len(block_lines) else ""
            if (len(nxt) > 25 and nxt[0].isupper()) or (nxt and nxt[0].islower()):
                terms.append(s)
        out, seen = [], set()
        for t in terms:
            k = t.lower()
            if k not in seen:
                seen.add(k)
                out.append(t)
        return out[:150]

    index = {"chapters": [], "industries": []}

    for num in sorted(toc):
        ch = toc[num]
        block_lines = lines[ch["body_line"]:ch["end_line"]]
        block = "\n".join(block_lines)
        slug = slugify(ch["title"])
        fname = f"ch{num:02d}-{slug}.txt"
        (OUTDIR / "chapters" / fname).write_text(block, encoding="utf-8")
        index["chapters"].append({
            "chapter": num,
            "asc": ch["asc"],
            "title": ch["title"],
            "slug": slug,
            "file": f"chapters/{fname}",
            "lines": len(block_lines),
            "chars": len(block),
            "words": len(block.split()),
            "inferred_boundary": bool(ch.get("inferred")),
            "citations": citations_in(block),
            "defined_terms": defined_terms(block_lines),
        })

    for ind in industries:
        block_lines = lines[ind["start_line"]:ind["end_line"]]
        block = "\n".join(block_lines)
        slug = slugify(ind["title"])
        fname = f"asc{ind['primary']}-{slug}.txt"
        (OUTDIR / "industries" / fname).write_text(block, encoding="utf-8")
        index["industries"].append({
            "asc": ind["asc"],
            "primary": ind["primary"],
            "title": ind["title"],
            "slug": slug,
            "file": f"industries/{fname}",
            "lines": len(block_lines),
            "chars": len(block),
            "words": len(block.split()),
            "citations": citations_in(block),
            "defined_terms": defined_terms(block_lines),
        })

    # -- back matter -----------------------------------------------------
    index["appendices"] = []
    if appendices:
        (OUTDIR / "appendices").mkdir(parents=True, exist_ok=True)
        for j, a in enumerate(appendices):
            end = appendices[j + 1]["line"] if j + 1 < len(appendices) else n
            block = "\n".join(lines[a["line"]:end])
            fname = f"appendix-{a['letter'].lower()}.txt"
            (OUTDIR / "appendices" / fname).write_text(block, encoding="utf-8")
            index["appendices"].append({
                "letter": a["letter"],
                "title": a["title"],
                "file": f"appendices/{fname}",
                "start_line": a["line"],
                "words": len(block.split()),
            })

    (OUTDIR / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")

    # ---------------------------------------------------------------
    print("\n=== CHAPTERS ===")
    thin = 0
    for c in index["chapters"]:
        flag = " INFERRED" if c["inferred_boundary"] else ""
        if c["words"] < 400:
            thin += 1
            flag += " THIN"
        print(f"  ch{c['chapter']:02d} ASC {c['asc']:<5} {c['title'][:44]:<44} "
              f"{c['words']:>7,}w {len(c['citations']):>4}cit {len(c['defined_terms']):>4}def{flag}")

    print("\n=== INDUSTRIES ===")
    for c in index["industries"]:
        print(f"  ASC {c['primary']:<5} {c['title'][:46]:<46} "
              f"{c['words']:>7,}w {len(c['citations']):>4}cit {len(c['defined_terms']):>4}def")

    tot_w = sum(c["words"] for c in index["chapters"])
    print(f"\nchapters {len(index['chapters'])}  industries {len(index['industries'])}"
          f"  thin {thin}  total {tot_w:,} words")
    print(f"wrote {OUTDIR / 'index.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
