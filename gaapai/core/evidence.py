"""Workpapers: the audit trail that travels with every computed number.

The point of this layer is that a financial answer is not just a scalar. An
auditor asked to accept "revenue for Q3 was 4,812,000" needs four more things:
what inputs went in, what rule was applied, which paragraph authorises it, and
what the intermediate steps were. A number without those is unreviewable.

So every deterministic skill returns a :class:`GaapResult`, not a float. The
result renders to a workpaper -- the same tie-out schedule a preparer would
hand to a reviewer -- and to JSON for machine consumption.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from .asc import Citation
from .money import Money, quantize

__all__ = [
    "Step",
    "Assumption",
    "Check",
    "GaapResult",
    "Severity",
]


class Severity:
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


def _plain(value: Any) -> Any:
    """Render a value into something JSON can hold, without losing precision."""
    if isinstance(value, Money):
        return {"amount": str(quantize(value.amount, 2)), "currency": value.currency}
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, Citation):
        return value.to_dict()
    return value


@dataclass
class Step:
    """One line of a computation, in the order it was performed."""

    label: str
    value: Any
    formula: Optional[str] = None
    note: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"label": self.label, "value": _plain(self.value)}
        if self.formula:
            d["formula"] = self.formula
        if self.note:
            d["note"] = self.note
        return d


@dataclass
class Assumption:
    """A judgement the caller supplied or the skill defaulted.

    Assumptions are surfaced rather than buried. A discount rate, a useful life,
    or an SSP estimate materially changes the answer, and a reviewer must see
    which ones were asserted versus observed.
    """

    name: str
    value: Any
    basis: str  # "observed", "entity policy", "estimated", "default"
    citation: Optional[Citation] = None

    def to_dict(self) -> dict:
        d = {"name": self.name, "value": _plain(self.value), "basis": self.basis}
        if self.citation:
            d["authority"] = self.citation.key
        return d


@dataclass
class Check:
    """A GAAP assertion that was tested, and whether it held."""

    name: str
    passed: bool
    detail: str = ""
    severity: str = Severity.ERROR
    citation: Optional[Citation] = None

    def to_dict(self) -> dict:
        d = {
            "check": self.name,
            "passed": self.passed,
            "severity": self.severity,
        }
        if self.detail:
            d["detail"] = self.detail
        if self.citation:
            d["authority"] = self.citation.key
        return d


@dataclass
class GaapResult:
    """A computed answer plus everything needed to review it."""

    skill: str
    value: Any
    summary: str = ""
    steps: List[Step] = field(default_factory=list)
    assumptions: List[Assumption] = field(default_factory=list)
    checks: List[Check] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    schedule: List[Dict[str, Any]] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)
    diagram: Optional[str] = None

    # -- building -------------------------------------------------------

    def step(self, label: str, value: Any, formula: str = None, note: str = None) -> "GaapResult":
        self.steps.append(Step(label, value, formula, note))
        return self

    def assume(self, name: str, value: Any, basis: str = "default",
               citation: Citation = None) -> "GaapResult":
        self.assumptions.append(Assumption(name, value, basis, citation))
        return self

    def check(self, name: str, passed: bool, detail: str = "",
              severity: str = Severity.ERROR, citation: Citation = None) -> "GaapResult":
        self.checks.append(Check(name, passed, detail, severity, citation))
        return self

    def cite(self, *citations: Citation) -> "GaapResult":
        for c in citations:
            if c not in self.citations:
                self.citations.append(c)
        return self

    # -- inspection -----------------------------------------------------

    @property
    def ok(self) -> bool:
        """True when no error-severity check failed."""
        return not any(
            (not c.passed) and c.severity == Severity.ERROR for c in self.checks
        )

    @property
    def failures(self) -> List[Check]:
        return [c for c in self.checks if not c.passed]

    @property
    def fingerprint(self) -> str:
        """Stable hash of inputs and result.

        Two runs of the same skill on the same inputs produce the same
        fingerprint. This is what makes the layer *deterministic* in a way a
        reviewer can verify rather than take on faith: rerun it, compare the
        hash.
        """
        payload = json.dumps(
            {"skill": self.skill, "inputs": _plain(self.inputs), "value": _plain(self.value)},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    # -- rendering ------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "summary": self.summary,
            "value": _plain(self.value),
            "fingerprint": self.fingerprint,
            "authorities": [c.to_dict() for c in self.citations],
            "assumptions": [a.to_dict() for a in self.assumptions],
            "steps": [s.to_dict() for s in self.steps],
            "checks": [c.to_dict() for c in self.checks],
            "schedule": _plain(self.schedule),
            "ok": self.ok,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def workpaper(self, width: int = 78) -> str:
        """Render as a reviewable workpaper."""
        out: List[str] = []
        rule = "=" * width

        out.append(rule)
        out.append(f"WORKPAPER  {self.skill}")
        out.append(f"Ref: {self.fingerprint}")
        out.append(rule)

        if self.summary:
            out.append("")
            out.append(self.summary)

        if self.citations:
            out.append("")
            out.append("AUTHORITY")
            out.append("-" * width)
            for c in self.citations:
                out.append(f"  ASC {c.key}  {c.topic}")
                out.append(f"      {c.requirement}")

        if self.assumptions:
            out.append("")
            out.append("ASSUMPTIONS AND JUDGEMENTS")
            out.append("-" * width)
            for a in self.assumptions:
                auth = f"  [ASC {a.citation.key}]" if a.citation else ""
                out.append(f"  {a.name}: {_fmt(a.value)}  ({a.basis}){auth}")

        if self.steps:
            out.append("")
            out.append("COMPUTATION")
            out.append("-" * width)
            label_w = max((len(s.label) for s in self.steps), default=0)
            label_w = min(max(label_w, 20), 44)
            for s in self.steps:
                out.append(f"  {s.label:<{label_w}}  {_fmt(s.value):>18}")
                if s.formula:
                    out.append(f"  {'':<{label_w}}  = {s.formula}")
                if s.note:
                    out.append(f"  {'':<{label_w}}    {s.note}")

        if self.schedule:
            out.append("")
            out.append("SCHEDULE")
            out.append("-" * width)
            out.extend(_table(self.schedule))

        if self.checks:
            out.append("")
            out.append("GAAP CHECKS")
            out.append("-" * width)
            for c in self.checks:
                mark = "PASS" if c.passed else ("WARN" if c.severity == Severity.WARNING else "FAIL")
                auth = f" [ASC {c.citation.key}]" if c.citation else ""
                out.append(f"  [{mark}] {c.name}{auth}")
                if c.detail:
                    out.append(f"         {c.detail}")

        out.append(rule)
        status = "TIES" if self.ok else "EXCEPTIONS NOTED"
        out.append(f"Status: {status}")
        out.append(rule)
        return "\n".join(out)

    def __str__(self) -> str:
        return self.workpaper()


def _fmt(value: Any) -> str:
    if isinstance(value, Money):
        return f"{quantize(value.amount, 2):,}"
    if isinstance(value, Decimal):
        q = quantize(value, 6).normalize()
        return f"{q:,}"
    if isinstance(value, float):
        return f"{value:,.4f}"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _table(rows: Sequence[Dict[str, Any]], max_rows: int = 40) -> List[str]:
    """Fixed-width rendering of a schedule."""
    if not rows:
        return []
    cols: List[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)

    shown = list(rows[:max_rows])
    cells = [[_fmt(r.get(c, "")) for c in cols] for r in shown]
    widths = [
        max(len(str(c)), max((len(row[i]) for row in cells), default=0))
        for i, c in enumerate(cols)
    ]

    lines = ["  " + "  ".join(str(c).rjust(widths[i]) for i, c in enumerate(cols))]
    lines.append("  " + "  ".join("-" * w for w in widths))
    for row in cells:
        lines.append("  " + "  ".join(row[i].rjust(widths[i]) for i in range(len(cols))))
    if len(rows) > max_rows:
        lines.append(f"  ... {len(rows) - max_rows} further periods omitted")
    return lines
