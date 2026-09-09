"""Check the reference pack is present, complete, and consistent with the code.

Run by CI and worth running locally after regenerating the pack:

    python scripts/check_pack.py

The pack and the citation catalog can drift apart in both directions -- a rule
can cite a paragraph nobody added, or the pack can lose a file the router
expects -- and neither failure shows up in a normal test run against a machine
that happens to have an older copy installed at ~/.claude/skills.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gaapai  # noqa: E402
from gaapai import semantics  # noqa: E402
from gaapai.core import asc  # noqa: E402
from gaapai.router import Router  # noqa: E402

EXPECTED_INDUSTRIES = 20
EXPECTED_CHAPTERS = 64


def main() -> int:
    problems: list[str] = []

    # -- the pack resolves, and to this checkout rather than a stale install --
    router = Router()
    if router.pack_path is None:
        print("FAIL  no reference pack found")
        return 1
    local = ROOT / "skills" / "gaap-accounting"
    if router.pack_path.resolve() != local.resolve():
        problems.append(
            f"router resolved {router.pack_path}, not the checkout at {local}; "
            "an installed copy is shadowing this one")

    industries, chapters = router.industries(), router.chapters()
    if len(industries) != EXPECTED_INDUSTRIES:
        problems.append(f"{len(industries)} industries, expected {EXPECTED_INDUSTRIES}")
    if len(chapters) != EXPECTED_CHAPTERS:
        problems.append(f"{len(chapters)} chapters, expected {EXPECTED_CHAPTERS}")

    # -- every file the index names is actually on disk ---------------------
    for entry in industries + chapters:
        target = router.pack_path / entry["file"]
        if not target.exists():
            problems.append(f"index names {entry['file']}, which is missing")

    # -- every citation a rule relies on exists in the catalog --------------
    for code in semantics.industries():
        for rule in semantics.profile_for(code).row_rules:
            try:
                asc.cite(rule.citation)
            except KeyError:
                problems.append(
                    f"row rule {code}/{rule.name} cites ASC {rule.citation}, "
                    "which is not in the catalog")

    # -- nothing that computes may rest on an unverified paragraph ----------
    for sub in gaapai.REGISTRY.subskills():
        for c in sub.citations:
            if not c.verified:
                problems.append(
                    f"{sub.qualified_name} cites unverified ASC {c.key}; only "
                    "row rules may do that")

    citations = asc.all_citations()
    unverified = [c for c in citations if not c.verified]

    if problems:
        print(f"FAIL  {len(problems)} problem(s)")
        for p in problems:
            print(f"  - {p}")
        return 1

    print("OK")
    print(f"  pack        {router.pack_path.relative_to(ROOT)}")
    print(f"  industries  {len(industries)}")
    print(f"  chapters    {len(chapters)}")
    print(f"  computations {len(gaapai.REGISTRY.subskills())}")
    print(f"  citations   {len(citations)}  ({len(unverified)} unverified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
