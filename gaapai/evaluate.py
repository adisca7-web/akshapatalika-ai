"""Evaluate row rules against real data and quantify what they would change.

The semantic layer decides *which rows carry which concept*. Until now it could
only say so in prose, rendered into the code-generation prompt. That is enough
to instruct a model and not nearly enough to review a rule: "exclude gift card
line items" is unfalsifiable until someone says how many rows that is and how
much money moves.

This module closes that gap. It applies a :class:`~gaapai.semantics.RowRule` to
actual rows and reports the effect as a number, which is what makes the
propose-and-ratify loop possible:

* a *candidate* rule reports its impact and is **not** applied;
* a *ratified* rule is applied and its impact is part of the answer;
* a *rejected* rule is recorded so it is not proposed again.

Fail-closed is the point. A rule nobody has ratified never silently changes a
figure -- it produces a warning carrying the delta it would have made, so the
reviewer sees both the number they got and the number they would have got.

Dependency note: rows are ``Mapping`` objects, not DataFrames, so the core
stays standard-library only. :func:`rows_from_frame` adapts pandas at the edge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .core import asc
from .semantics import AggregationPlan, Concept, RowRule

__all__ = [
    "AmountBasis",
    "RuleImpact",
    "choose_amount_basis",
    "citation_status",
    "evaluate_row_rules",
    "rows_from_frame",
]

CANDIDATE = "candidate"
RATIFIED = "ratified"
REJECTED = "rejected"


def _norm(name: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


# Tokens an empty cell arrives as once a DataFrame has been converted to plain
# mappings. This is not cosmetic: pandas yields float('nan') for a blank cell,
# str(nan) is "nan", and "nan" matches a permissive rule pattern such as /.+/.
# Without this guard the cancelled-order rule matched all 81 rows of a file with
# no cancellations at all, and reported the entire revenue base as excluded.
_BLANK_TOKENS = {"", "nan", "nat", "none", "null", "<na>"}


def is_blank(value: Any) -> bool:
    """True when a cell holds no value, however the source spells that."""
    if value is None:
        return True
    # NaN is the only value not equal to itself; catches float and numpy nan
    # without importing numpy.
    if value != value:
        return True
    return str(value).strip().lower() in _BLANK_TOKENS


_MONEY_NOISE = re.compile(r"[,$\s ]")


def to_decimal(value: Any) -> Optional[Decimal]:
    """Parse a cell into an exact Decimal, or None when it is not a number.

    Never returns a float. A cell that cannot be parsed is None rather than
    zero, because silently treating an unparseable amount as nothing is exactly
    how a total goes quietly wrong.
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):          # bool is an int subclass; not an amount
        return None
    if isinstance(value, int):
        return Decimal(value)
    text = _MONEY_NOISE.sub("", str(value)).strip()
    if not text or text.lower() in {"nan", "none", "null", "-"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    try:
        d = Decimal(text)
    except (InvalidOperation, ValueError):
        return None
    return -d if negative else d


def citation_status(citation: str) -> Tuple[bool, str]:
    """Whether a citation resolves in the ASC catalog, and why not if it does not.

    This is the guard that already existed for subskills and was never wired to
    row rules -- which is how 22 of the shipped rules came to cite paragraphs
    that were never verified.
    """
    try:
        found = asc.cite(citation)
    except KeyError:
        return False, f"ASC {citation} is not in the catalog"
    return True, str(found)


# ---------------------------------------------------------------------------
# Choosing what "amount" means for a matched row
# ---------------------------------------------------------------------------


@dataclass
class AmountBasis:
    """How the money moved by a rule is measured, and why that basis was chosen.

    Reported rather than assumed. A line-item rule measured against an
    order-level total overstates its own impact, and a reviewer cannot catch
    that unless the basis is on screen.
    """

    kind: str                     # "product" | "columns" | "none"
    columns: List[str] = field(default_factory=list)
    factor_column: str = ""
    rationale: str = ""

    def amount_for(self, row: Mapping[str, Any]) -> Optional[Decimal]:
        if self.kind == "product":
            price = to_decimal(row.get(self.columns[0])) if self.columns else None
            qty = to_decimal(row.get(self.factor_column))
            if price is None:
                return None
            return price * (qty if qty is not None else Decimal(1))
        if self.kind == "columns":
            total = Decimal(0)
            seen = False
            for col in self.columns:
                d = to_decimal(row.get(col))
                if d is not None:
                    total += d
                    seen = True
            return total if seen else None
        return None

    def describe(self) -> str:
        if self.kind == "product":
            return f"{self.columns[0]} x {self.factor_column} -- {self.rationale}"
        if self.kind == "columns":
            return f"SUM({', '.join(self.columns)}) -- {self.rationale}"
        return "no amount column identified -- impact reported as row count only"


_PRICE_PAT = re.compile(r"(lineitem_price|line_item_price|item_price|unit_price)")
_QTY_PAT = re.compile(r"(lineitem_quantity|line_item_quantity|item_quantity|^quantity$|^qty$)")


def choose_amount_basis(
    columns: Sequence[str], plan: Optional[AggregationPlan] = None
) -> AmountBasis:
    """Pick the most defensible measure of a row's amount for this schema.

    Line-level price x quantity wins when both are present, because row rules
    overwhelmingly match line-level facts (a gift card line, a test item) while
    the columns bound to gross revenue are usually order-level totals repeated
    across every line of the order. Summing an order total once per line
    multiplies the impact by the line count.
    """
    by_norm = {_norm(c): c for c in columns}
    price = next((orig for n, orig in by_norm.items() if _PRICE_PAT.search(n)), None)
    qty = next((orig for n, orig in by_norm.items() if _QTY_PAT.search(n)), None)
    if price and qty:
        return AmountBasis(
            kind="product", columns=[price], factor_column=qty,
            rationale="line-level price x quantity; order totals repeat per line",
        )
    if price:
        return AmountBasis(
            kind="product", columns=[price], factor_column="",
            rationale="line-level price; no quantity column found, assuming 1",
        )
    if plan is not None:
        gross = plan.columns_for(Concept.GROSS_REVENUE)
        if gross:
            return AmountBasis(
                kind="columns", columns=gross,
                rationale="columns bound to gross revenue; verify these are not "
                          "order totals repeated across line items",
            )
        net = plan.columns_for(Concept.NET_REVENUE)
        if net:
            return AmountBasis(kind="columns", columns=net,
                               rationale="columns bound to net revenue")
    return AmountBasis(kind="none")


# ---------------------------------------------------------------------------
# Impact
# ---------------------------------------------------------------------------


@dataclass
class RuleImpact:
    """What one row rule would do to this data set."""

    rule: RowRule
    trigger_columns: List[str]
    row_indices: List[int]
    amount: Optional[Decimal]
    basis: AmountBasis
    samples: List[Dict[str, Any]]
    status: str = CANDIDATE

    @property
    def row_count(self) -> int:
        return len(self.row_indices)

    @property
    def fires(self) -> bool:
        return bool(self.row_indices)

    @property
    def citation_ok(self) -> bool:
        return citation_status(self.rule.citation)[0]

    @property
    def applied(self) -> bool:
        """Only a ratified rule changes a number. Candidates warn instead."""
        return self.status == RATIFIED

    def to_dict(self) -> dict:
        return {
            "rule": self.rule.name,
            "status": self.status,
            "applied": self.applied,
            "citation": self.rule.citation,
            "citation_ok": self.citation_ok,
            "becomes": self.rule.becomes,
            "severity": self.rule.severity,
            "trigger_columns": self.trigger_columns,
            "rows": self.row_count,
            "amount": str(self.amount) if self.amount is not None else None,
            "amount_basis": self.basis.describe(),
            "requirement": self.rule.requirement,
        }

    def render(self) -> str:
        head = {CANDIDATE: "CANDIDATE RULE  (unratified -- NOT applied)",
                RATIFIED: "RATIFIED RULE  (applied)",
                REJECTED: "REJECTED RULE  (not applied)"}[self.status]
        flag = "ok, in catalog" if self.citation_ok else "NOT IN CATALOG -- unverified"
        amt = f"{self.amount}" if self.amount is not None else "not measurable"
        return (
            f"{head}\n"
            f"  {self.rule.name}\n"
            f"  WHERE {', '.join(self.trigger_columns) or '(no column)'} "
            f"matches /{self.rule.match_value}/\n"
            f"  -> {self.rule.becomes}     ASC {self.rule.citation}  [{flag}]\n"
            f"  Impact: {self.row_count} rows, {amt}\n"
            f"          basis: {self.basis.describe()}\n"
            f"  {self.rule.requirement}"
        )


def evaluate_row_rules(
    rows: Sequence[Mapping[str, Any]],
    plan: AggregationPlan,
    *,
    ratified: Iterable[str] = (),
    rejected: Iterable[str] = (),
    basis: Optional[AmountBasis] = None,
    sample_size: int = 3,
    include_silent: bool = False,
) -> List[RuleImpact]:
    """Apply this industry's row rules to real rows and measure each one.

    Nothing is mutated and nothing is netted here. The caller decides what to do
    with a candidate; this function only establishes what is true about the data.

    ``include_silent`` keeps rules that matched no rows, which is useful in the
    harness -- a rule that never fires on a schema it should cover is itself a
    finding, and it is invisible if silent rules are dropped.
    """
    ratified_set, rejected_set = set(ratified), set(rejected)
    columns = [b.column for b in plan.bindings]
    amount_basis = basis or choose_amount_basis(columns, plan)

    out: List[RuleImpact] = []
    for rule, trigger_columns in plan.applicable_row_rules():
        try:
            value_pat = re.compile(rule.match_value)
        except re.error:
            continue
        matched: List[int] = []
        samples: List[Dict[str, Any]] = []
        total = Decimal(0)
        measured = False
        for i, row in enumerate(rows):
            hit = any(
                not is_blank(row.get(col))
                and value_pat.search(str(row.get(col)))
                for col in trigger_columns
            )
            if not hit:
                continue
            matched.append(i)
            amt = amount_basis.amount_for(row)
            if amt is not None:
                total += amt
                measured = True
            if len(samples) < sample_size:
                samples.append({c: row.get(c) for c in trigger_columns
                                + amount_basis.columns
                                + ([amount_basis.factor_column]
                                   if amount_basis.factor_column else [])})
        if not matched and not include_silent:
            continue
        status = (RATIFIED if rule.name in ratified_set
                  else REJECTED if rule.name in rejected_set else CANDIDATE)
        out.append(RuleImpact(
            rule=rule, trigger_columns=trigger_columns, row_indices=matched,
            amount=total if measured else None, basis=amount_basis,
            samples=samples, status=status,
        ))
    # Largest money impact first: that is the order a reviewer should read them.
    out.sort(key=lambda im: (im.amount or Decimal(0)), reverse=True)
    return out


def rows_from_frame(df: Any) -> List[Dict[str, Any]]:
    """Adapt a pandas DataFrame to plain mappings at the boundary."""
    return df.to_dict(orient="records")
