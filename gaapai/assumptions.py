"""Assumptions the user states in conversation, carried across turns.

"Cost of goods is 50% of product revenue" is not a question and not a fact in
the data. It is an *assumption the preparer is supplying*, and until now it went
nowhere: the deterministic engine saw the word "revenue", answered with total
revenue, and the statement was lost. The next question then had no idea a cost
rate had been given.

Assumptions are the third kind of input this system takes, alongside the data
and the entity profile:

* **data**   -- what happened, read from the file;
* **profile** -- durable facts about the entity, asserted once and versioned;
* **assumptions** -- working hypotheses for this conversation ("assume 50%
  cost"), which change with the question and belong in the answer's caveats.

They are kept separate from the profile deliberately. A cost ratio someone
tried out mid-conversation must never quietly become a permanent property of
the entity, and every figure derived from one has to say it rests on an
estimate rather than on the books.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

__all__ = ["Assumptions", "parse_assumptions", "is_assumption_statement"]


def _pct(raw: str) -> Optional[Decimal]:
    """"50", "50%", "0.5" -> Decimal("0.50"). Out-of-range values are rejected."""
    try:
        value = Decimal(str(raw).strip().rstrip("%").strip())
    except (InvalidOperation, ValueError):
        return None
    if value > 1:
        value = value / Decimal(100)
    if value < 0 or value > 1:
        return None
    return value


# Cost stated directly: "cost of goods is 50% of revenue", "COGS = 60%",
# "products cost 45% of the sale price".
_COST_PATTERNS = (
    r"(?:cogs|cost of (?:goods|sales|revenue|products?)|product costs?|"
    r"cost of the products?)\s*(?:sold\s*)?(?:is|are|=|:|at|equals?)?\s*"
    r"(\d+(?:\.\d+)?)\s*%",
    r"(?:products?|goods|items?)\s+cost\s+(\d+(?:\.\d+)?)\s*%",
    r"assume\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s+cost",
)

# Margin stated instead: cost is the complement.
_MARGIN_PATTERNS = (
    r"(?:gross\s+)?margins?\s*(?:is|are|of|=|:|at)?\s*(\d+(?:\.\d+)?)\s*%",
    r"(\d+(?:\.\d+)?)\s*%\s+(?:gross\s+)?margin",
    r"mark\s*up\s*(?:is|of|=)?\s*(\d+(?:\.\d+)?)\s*%",   # treated as margin
)

_OPEX_PATTERNS = (
    r"(?:operating expenses?|opex|overheads?|running costs?)\s*"
    r"(?:is|are|=|:|at)?\s*(\d+(?:\.\d+)?)\s*%",
)


@dataclass
class Assumptions:
    """Working hypotheses supplied in conversation."""

    cogs_rate: Optional[Decimal] = None      # cost as a fraction of revenue
    opex_rate: Optional[Decimal] = None
    stated: List[str] = field(default_factory=list)   # what the user actually said

    @property
    def gross_margin_rate(self) -> Optional[Decimal]:
        if self.cogs_rate is None:
            return None
        return Decimal(1) - self.cogs_rate

    @property
    def any(self) -> bool:
        return self.cogs_rate is not None or self.opex_rate is not None

    def describe(self) -> List[str]:
        out = []
        if self.cogs_rate is not None:
            out.append(f"cost of goods at {self.cogs_rate * 100:.0f}% of revenue "
                       f"(gross margin {self.gross_margin_rate * 100:.0f}%)")
        if self.opex_rate is not None:
            out.append(f"operating expenses at {self.opex_rate * 100:.0f}% of revenue")
        return out

    def caveat(self) -> str:
        if not self.any:
            return ""
        return ("These figures rest on assumptions you supplied, not on your "
                "books: " + "; ".join(self.describe()) + ". They are an "
                "estimate, not a GAAP cost of sales — actual cost comes from "
                "inventory records under ASC 330.")

    def copy(self) -> "Assumptions":
        return Assumptions(self.cogs_rate, self.opex_rate, list(self.stated))


def parse_assumptions(
    text: str, existing: Optional[Assumptions] = None
) -> Tuple[Assumptions, List[str]]:
    """Extract any assumptions stated in ``text``, merged over ``existing``.

    Returns the merged assumptions and a list of plain-language changes, so the
    caller can confirm what it understood rather than silently absorbing a
    number the user may have mistyped.
    """
    out = existing.copy() if existing else Assumptions()
    changes: List[str] = []
    low = (text or "").lower()

    for pattern in _COST_PATTERNS:
        m = re.search(pattern, low)
        if m:
            rate = _pct(m.group(1))
            if rate is not None and rate != out.cogs_rate:
                out.cogs_rate = rate
                changes.append(f"cost of goods = {rate * 100:.0f}% of revenue")
            break
    else:
        for pattern in _MARGIN_PATTERNS:
            m = re.search(pattern, low)
            if m:
                margin = _pct(m.group(1))
                if margin is not None and (Decimal(1) - margin) != out.cogs_rate:
                    out.cogs_rate = Decimal(1) - margin
                    changes.append(
                        f"gross margin = {margin * 100:.0f}%, so cost of goods = "
                        f"{out.cogs_rate * 100:.0f}% of revenue")
                break

    for pattern in _OPEX_PATTERNS:
        m = re.search(pattern, low)
        if m:
            rate = _pct(m.group(1))
            if rate is not None and rate != out.opex_rate:
                out.opex_rate = rate
                changes.append(f"operating expenses = {rate * 100:.0f}% of revenue")
            break

    if changes:
        out.stated.append(text.strip())
    return out, changes


_QUESTION_HINT = re.compile(
    r"\?|\b(show|chart|graph|plot|what|how|which|can you|give me|list|"
    r"compare|trend|breakdown|calculate|compute|profitability|profit|margin)\b")


def is_assumption_statement(text: str) -> bool:
    """True when the message only *supplies* an assumption and asks nothing.

    "Cost of goods is 50% of product revenue" contains the word "revenue", which
    was enough for the revenue intent to claim it and answer with total revenue
    — an unrelated figure presented as if it were the reply.
    """
    merged, changes = parse_assumptions(text)
    if not changes:
        return False
    return not _QUESTION_HINT.search((text or "").lower())
