"""Deterministic routing from a question to skills and reference material.

Two catalogs are searched, and they answer different questions:

* the **deterministic registry** (``gaapai.skills``) answers *compute this* --
  it returns callable subskills with exact arithmetic and ASC citations;
* the **reference pack** (``skills/gaap-accounting``) answers *what does the standard
  require* -- it returns chapter and industry files distilled from Wiley GAAP.

Routing is lexical and deterministic on purpose. A model can paraphrase a
question a hundred ways, but the same question must always reach the same
subskill, or the "deterministic" claim is hollow. Where the router is unsure it
returns ranked candidates and says so, rather than guessing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from .core.registry import REGISTRY, SubSkill

__all__ = ["Route", "Router", "route", "default_pack_path"]

_ASC_IN_TEXT = re.compile(r"\basc\s*(\d{3})\b", re.IGNORECASE)
_TOKEN = re.compile(r"[a-z0-9]+")

# Words that carry no routing signal. Kept small: over-aggressive stopping
# throws away real terms like "cost", "value", and "share".
_STOP = {
    "the", "a", "an", "of", "for", "to", "in", "on", "is", "are", "was", "were",
    "what", "which", "how", "do", "does", "did", "our", "we", "us", "my", "i",
    "and", "or", "but", "with", "by", "at", "from", "this", "that", "these",
    "it", "be", "been", "can", "should", "would", "will", "if", "as", "any",
    "please", "you", "me", "about", "much", "many",
}


def default_pack_path() -> Optional[Path]:
    """Locate the GaapAccounting reference pack, project copy first."""
    candidates = [
        Path(__file__).resolve().parent.parent / "skills" / "gaap-accounting",
        Path.home() / ".claude" / "skills" / "gaap-accounting",
        Path.home() / ".agents" / "skills" / "gaap-accounting",
    ]
    for c in candidates:
        if (c / "_index.json").exists() or (c / "SKILL.md").exists():
            return c
    return None


def _stem(token: str) -> str:
    """Fold trivial plurals so "lease" matches the chapter titled "Leases".

    Deliberately minimal -- a real stemmer would collapse distinctions the
    Codification cares about (``receivable`` vs ``receivables`` is harmless,
    but ``interest`` vs ``interests`` is not always).
    """
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("es") and not token.endswith("ses"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokens(text: str) -> List[str]:
    return [
        _stem(t)
        for t in _TOKEN.findall(text.lower())
        if t not in _STOP and len(t) > 1
    ]


@dataclass
class Route:
    """A routing decision, with everything needed to act on or audit it."""

    query: str
    subskills: List[SubSkill] = field(default_factory=list)
    references: List[Dict] = field(default_factory=list)
    asc_topics: List[str] = field(default_factory=list)
    confident: bool = False
    rationale: str = ""

    @property
    def best(self) -> Optional[SubSkill]:
        return self.subskills[0] if self.subskills else None

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "confident": self.confident,
            "rationale": self.rationale,
            "asc_topics": self.asc_topics,
            "subskills": [s.qualified_name for s in self.subskills],
            "references": [r.get("file") for r in self.references],
        }

    def explain(self) -> str:
        out = [f"Query: {self.query}", ""]
        out.append(f"Confidence: {'high' if self.confident else 'low -- candidates only'}")
        if self.rationale:
            out.append(f"Basis: {self.rationale}")
        if self.asc_topics:
            out.append(f"ASC topics detected: {', '.join(self.asc_topics)}")
        if self.subskills:
            out.append("")
            out.append("Deterministic subskills (these compute the answer):")
            for s in self.subskills:
                refs = ", ".join(c.key for c in s.citations[:3])
                out.append(f"  - {s.qualified_name}  [{refs}]")
                out.append(f"      {s.summary}")
        else:
            out.append("")
            out.append("No deterministic subskill matches. This is a reference "
                       "question, not a computation.")
        if self.references:
            out.append("")
            out.append("Reference material (what the standard requires):")
            for r in self.references:
                out.append(f"  - {r.get('title')}  ({r.get('file')})")
        return "\n".join(out)


class Router:
    """Matches a question against the deterministic registry and reference pack."""

    def __init__(self, pack_path: Optional[Path] = None) -> None:
        self.pack_path = pack_path if pack_path is not None else default_pack_path()
        self._pack: Dict = {"chapters": [], "industries": []}
        if self.pack_path:
            index = self.pack_path / "_index.json"
            if index.exists():
                self._pack = json.loads(index.read_text(encoding="utf-8"))

    # -- scoring ---------------------------------------------------------

    def _score_subskill(self, sub: SubSkill, query: str, toks: Sequence[str]) -> float:
        q = query.lower()
        score = 0.0

        # An explicit trigger phrase is the strongest signal available: it is a
        # curated declaration by the subskill's author, whereas a name match is
        # inferred. Weighted above the full-name bonus below so that "build the
        # statement of cash flows" reaches cashflow.indirect_method rather than
        # statements.build_statements, which merely shares two words.
        for trigger in sub.triggers:
            if trigger in q:
                score += 14.0 + len(trigger) / 20.0

        # The subskill's own name, spelled out. Every word of the name being
        # present is much stronger evidence than a partial overlap: "classify
        # this lease" names classify_lease exactly even though it matches no
        # trigger phrase, whereas "film costs" shares only "cost" with
        # cost_flow and should not select it.
        name_words = {_stem(w) for w in sub.name.split("_")}
        matched = name_words & set(toks)
        score += 2.5 * len(matched)
        if name_words and matched == name_words:
            score += 8.0

        # Summary overlap, weighted low so prose does not outvote triggers.
        summary_words = set(_tokens(sub.summary))
        score += 0.4 * len(summary_words & set(toks))

        # An ASC topic named in the query that this subskill implements.
        for topic in _ASC_IN_TEXT.findall(query):
            if any(c.key.startswith(topic) for c in sub.citations):
                score += 8.0
        return score

    def _score_reference(self, entry: Dict, query: str, toks: Sequence[str]) -> float:
        """Rank a chapter or industry file against the query.

        The title dominates deliberately. Section headings inside a long chapter
        mention many topics in passing -- ASC 805 discusses leases, ASC 815
        discusses revenue -- so letting heading overlap compete with the title
        routes "is this lease finance or operating" to Business Combinations.
        Headings break ties; they do not decide.
        """
        score = 0.0
        tokset = set(toks)

        title_words = set(_tokens(entry.get("title", "")))
        score += 9.0 * len(title_words & tokset)

        asc = str(entry.get("asc", entry.get("primary", "")))
        for topic in _ASC_IN_TEXT.findall(query):
            if topic == asc or topic in [str(a) for a in entry.get("asc", [])]:
                score += 20.0

        heading_hits = 0
        for sub in entry.get("subskills", [])[:40]:
            overlap = len(set(_tokens(sub)) & tokset)
            if overlap >= 2:
                heading_hits += overlap
        # Capped so a sprawling chapter cannot out-score an on-point title.
        score += min(heading_hits * 0.3, 2.5)
        return score

    # -- routing ---------------------------------------------------------

    def route(self, query: str, limit: int = 5) -> Route:
        toks = _tokens(query)
        topics = _ASC_IN_TEXT.findall(query)

        # A bare name-word overlap is not evidence. "How do we amortise film
        # costs?" shares the token "cost" with inventory.cost_flow, which would
        # otherwise make an inventory function the answer to a film question.
        # Below this floor the query is treated as a reference lookup instead.
        MIN_SCORE = 6.0

        scored_subs = [
            (self._score_subskill(s, query, toks), s)
            for s in REGISTRY.subskills()
        ]
        scored_subs = [(sc, s) for sc, s in scored_subs if sc >= MIN_SCORE]
        scored_subs.sort(key=lambda x: (-x[0], x[1].qualified_name))

        entries: List[Dict] = []
        for e in self._pack.get("industries", []):
            entries.append({**e, "kind": "industry"})
        for e in self._pack.get("chapters", []):
            entries.append({**e, "kind": "chapter"})

        top = scored_subs[0][0] if scored_subs else 0.0
        runner = scored_subs[1][0] if len(scored_subs) > 1 else 0.0
        # Confident when a trigger fired and nothing else is close behind.
        confident = top >= 10.0 and (top - runner) >= 2.0

        # The matched subskill is the best available hint about which chapter is
        # on point, and it is information the lexical scorer cannot recover: a
        # question about lease classification never contains the word "842".
        # Only a confident match earns the boost -- otherwise a weak subskill
        # guess would drag the reference lookup off-topic with it.
        topic_boost: Dict[str, float] = {}
        if confident:
            for rank, (_, sub) in enumerate(scored_subs[:3]):
                skill_topic = REGISTRY.skill(sub.skill).topic
                topic_boost[skill_topic] = max(
                    topic_boost.get(skill_topic, 0.0), 25.0 - rank * 6.0
                )

        scored_refs = []
        for e in entries:
            score = self._score_reference(e, query, toks)
            asc_values = {str(e.get("asc", ""))} | {
                str(a) for a in e.get("asc", []) if not isinstance(e.get("asc"), str)
            }
            asc_values.add(str(e.get("primary", "")))
            for topic, boost in topic_boost.items():
                if topic in asc_values:
                    score += boost
            if score > 0:
                scored_refs.append((score, e))
        scored_refs.sort(key=lambda x: (-x[0], str(x[1].get("title"))))

        if confident:
            rationale = f"matched a declared trigger phrase (score {top:.1f})"
        elif scored_subs:
            rationale = (f"weak or ambiguous match (top {top:.1f}, runner-up "
                         f"{runner:.1f}); confirm the subskill before computing")
        else:
            rationale = "no deterministic subskill matched; reference lookup only"

        return Route(
            query=query,
            subskills=[s for _, s in scored_subs[:limit]],
            references=[e for _, e in scored_refs[:limit]],
            asc_topics=sorted(set(topics)),
            confident=confident,
            rationale=rationale,
        )

    # -- reference lookup -------------------------------------------------

    def industries(self) -> List[Dict]:
        return list(self._pack.get("industries", []))

    def chapters(self) -> List[Dict]:
        return list(self._pack.get("chapters", []))

    def by_asc(self, topic: str) -> List[Dict]:
        """Every reference file covering an ASC topic number."""
        topic = str(topic).strip()
        out = []
        for e in self._pack.get("industries", []):
            if topic in [str(a) for a in e.get("asc", [])] or topic == e.get("primary"):
                out.append({**e, "kind": "industry"})
        for e in self._pack.get("chapters", []):
            if str(e.get("asc")) == topic:
                out.append({**e, "kind": "chapter"})
        return out

    def read(self, entry: Dict) -> str:
        """Load a reference file's text."""
        if not self.pack_path:
            raise FileNotFoundError("reference pack not found")
        return (self.pack_path / entry["file"]).read_text(encoding="utf-8")


_DEFAULT: Optional[Router] = None


def route(query: str, limit: int = 5) -> Route:
    """Route a question using a shared default Router."""
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Router()
    return _DEFAULT.route(query, limit)
