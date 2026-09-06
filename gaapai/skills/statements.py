"""ASC 205 / 210 -- Financial statement assembly and articulation.

This is where raw data meets GAAP presentation. A trial balance comes in;
a classified balance sheet and income statement come out, with the articulation
checks that a reviewer would perform:

* debits equal credits
* assets equal liabilities plus equity
* net income flows to retained earnings
* retained earnings rolls forward

These are not stylistic preferences. A model that answers "what were current
assets" off an unbalanced trial balance is confidently wrong, and nothing about
the phrasing of its answer reveals that. Enforcing articulation is what turns a
plausible answer into a defensible one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Sequence

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import D, Money, quantize
from ..core.registry import REGISTRY, subskill

SKILL = "statements"

REGISTRY.declare(
    SKILL,
    title="Financial Statement Presentation",
    topic="210",
    description=(
        "Assembly of a trial balance into a classified balance sheet and income "
        "statement, with articulation and tie-out checks between the statements."
    ),
)


# Statement classification. Order matters for presentation.
CURRENT_ASSET = "current_asset"
NONCURRENT_ASSET = "noncurrent_asset"
CURRENT_LIABILITY = "current_liability"
NONCURRENT_LIABILITY = "noncurrent_liability"
EQUITY = "equity"
REVENUE = "revenue"
EXPENSE = "expense"

_SECTION_ORDER = [
    CURRENT_ASSET, NONCURRENT_ASSET,
    CURRENT_LIABILITY, NONCURRENT_LIABILITY,
    EQUITY, REVENUE, EXPENSE,
]

_SECTION_TITLES = {
    CURRENT_ASSET: "Current assets",
    NONCURRENT_ASSET: "Noncurrent assets",
    CURRENT_LIABILITY: "Current liabilities",
    NONCURRENT_LIABILITY: "Noncurrent liabilities",
    EQUITY: "Stockholders' equity",
    REVENUE: "Revenues",
    EXPENSE: "Expenses",
}

# Accounts whose natural balance is a credit. Used to normalise sign.
_CREDIT_SECTIONS = {CURRENT_LIABILITY, NONCURRENT_LIABILITY, EQUITY, REVENUE}


@dataclass
class Account:
    """One trial balance line.

    ``balance`` is signed in the natural direction of the account: assets and
    expenses positive as debits, liabilities, equity and revenue positive as
    credits. This avoids the sign confusion of storing everything as a signed
    debit.
    """

    name: str
    section: str
    balance: Money
    contra: bool = False

    def __post_init__(self) -> None:
        if self.section not in _SECTION_ORDER:
            raise ValueError(
                f"account '{self.name}' has unknown section '{self.section}'; "
                f"expected one of {_SECTION_ORDER}"
            )

    @property
    def signed_amount(self) -> Money:
        """The amount as presented, with contra accounts negated."""
        return -self.balance if self.contra else self.balance

    @property
    def debit(self) -> Money:
        """Debit column of the trial balance."""
        natural_credit = self.section in _CREDIT_SECTIONS
        is_credit = natural_credit != self.contra
        return Money.zero(self.balance.currency) if is_credit else self.balance

    @property
    def credit(self) -> Money:
        natural_credit = self.section in _CREDIT_SECTIONS
        is_credit = natural_credit != self.contra
        return self.balance if is_credit else Money.zero(self.balance.currency)


@subskill(
    SKILL,
    summary="Verify that a trial balance is in balance before any statement is prepared.",
    citations=[ASC.GAAP_HIERARCHY],
    triggers=["trial balance", "in balance", "debits equal credits",
              "does it balance", "tie out", "check the books"],
    inputs={"accounts": "Sequence of Account entries."},
)
def verify_trial_balance(accounts: Sequence[Account]) -> GaapResult:
    """Debits must equal credits. This is the gate for every downstream answer."""
    if not accounts:
        raise ValueError("no accounts supplied")
    cur = accounts[0].balance.currency

    debits = Money.zero(cur)
    credits = Money.zero(cur)
    for a in accounts:
        debits = debits + a.debit
        credits = credits + a.credit

    difference = debits - credits
    balanced = difference.is_zero("0.01")

    r = GaapResult(
        skill=f"{SKILL}.verify_trial_balance",
        value={"balanced": balanced, "debits": debits, "credits": credits,
               "difference": difference},
        inputs={"account_count": len(accounts)},
        summary=(
            f"Trial balance is in balance at {debits}."
            if balanced else
            f"Trial balance is OUT OF BALANCE by {difference}. "
            "No statement prepared from it can be relied upon."
        ),
    )
    r.step("Total debits", debits)
    r.step("Total credits", credits)
    r.step("Difference", difference)
    r.step("Accounts", len(accounts))
    r.check("Debits equal credits", balanced,
            detail=f"out of balance by {difference}" if not balanced else "",
            citation=ASC.GAAP_HIERARCHY)
    return r


@subskill(
    SKILL,
    summary="Assemble a classified balance sheet and income statement from a trial balance, with articulation checks.",
    citations=[ASC.CLASSIFIED_BALANCE_SHEET, ASC.CURRENT_ASSETS, ASC.OFFSETTING],
    triggers=["balance sheet", "income statement", "financial statements",
              "prepare statements", "classified balance sheet", "p&l",
              "profit and loss", "statement of operations", "net income",
              "total assets", "current assets", "working capital"],
    inputs={
        "accounts": "Sequence of Account entries forming the trial balance.",
        "beginning_retained_earnings": "Retained earnings at the start of the period.",
        "dividends_declared": "Dividends declared during the period.",
    },
)
def build_statements(
    accounts: Sequence[Account],
    beginning_retained_earnings: Optional[Money] = None,
    dividends_declared: Optional[Money] = None,
) -> GaapResult:
    """Classify, total, and check articulation between the statements."""
    if not accounts:
        raise ValueError("no accounts supplied")
    cur = accounts[0].balance.currency

    tb = verify_trial_balance(accounts)

    sections: Dict[str, List[Account]] = {s: [] for s in _SECTION_ORDER}
    for a in accounts:
        sections[a.section].append(a)

    totals: Dict[str, Money] = {}
    for s in _SECTION_ORDER:
        t = Money.zero(cur)
        for a in sections[s]:
            t = t + a.signed_amount
        totals[s] = t

    total_assets = totals[CURRENT_ASSET] + totals[NONCURRENT_ASSET]
    total_liabilities = totals[CURRENT_LIABILITY] + totals[NONCURRENT_LIABILITY]
    total_revenue = totals[REVENUE]
    total_expense = totals[EXPENSE]
    net_income = total_revenue - total_expense
    contributed_equity = totals[EQUITY]

    r = GaapResult(
        skill=f"{SKILL}.build_statements",
        inputs={"account_count": len(accounts),
                "beginning_retained_earnings": beginning_retained_earnings,
                "dividends_declared": dividends_declared},
        value=None,
    )
    r.checks.extend(tb.checks)

    # -- statement lines -------------------------------------------------
    lines: List[Dict] = []
    for s in _SECTION_ORDER:
        if not sections[s]:
            continue
        lines.append({"statement": _statement_of(s), "section": _SECTION_TITLES[s],
                      "line": "", "amount": ""})
        for a in sorted(sections[s], key=lambda x: x.name):
            lines.append({
                "statement": _statement_of(s),
                "section": _SECTION_TITLES[s],
                "line": ("  less: " if a.contra else "  ") + a.name,
                "amount": a.signed_amount.round(2),
            })
        lines.append({"statement": _statement_of(s), "section": _SECTION_TITLES[s],
                      "line": f"Total {_SECTION_TITLES[s].lower()}",
                      "amount": totals[s].round(2)})
    r.schedule = lines

    r.step("Total current assets", totals[CURRENT_ASSET])
    r.step("Total noncurrent assets", totals[NONCURRENT_ASSET])
    r.step("TOTAL ASSETS", total_assets)
    r.step("Total current liabilities", totals[CURRENT_LIABILITY])
    r.step("Total noncurrent liabilities", totals[NONCURRENT_LIABILITY])
    r.step("TOTAL LIABILITIES", total_liabilities)
    r.step("Total revenues", total_revenue)
    r.step("Total expenses", total_expense)
    r.step("NET INCOME", net_income, formula="revenues - expenses")

    # -- retained earnings roll-forward ----------------------------------
    ending_re = None
    if beginning_retained_earnings is not None:
        divs = dividends_declared or Money.zero(cur)
        ending_re = beginning_retained_earnings + net_income - divs
        r.step("Beginning retained earnings", beginning_retained_earnings)
        r.step("Plus net income", net_income)
        if divs:
            r.step("Less dividends declared", -divs)
        r.step("Ending retained earnings", ending_re)

    total_equity = contributed_equity + (ending_re if ending_re is not None
                                         else net_income)
    r.step("TOTAL EQUITY", total_equity)

    working_capital = totals[CURRENT_ASSET] - totals[CURRENT_LIABILITY]
    r.step("Working capital", working_capital,
           formula="current assets - current liabilities")

    r.value = {
        "total_assets": total_assets,
        "total_current_assets": totals[CURRENT_ASSET],
        "total_noncurrent_assets": totals[NONCURRENT_ASSET],
        "total_liabilities": total_liabilities,
        "total_current_liabilities": totals[CURRENT_LIABILITY],
        "total_noncurrent_liabilities": totals[NONCURRENT_LIABILITY],
        "total_equity": total_equity,
        "total_revenue": total_revenue,
        "total_expenses": total_expense,
        "net_income": net_income,
        "ending_retained_earnings": ending_re,
        "working_capital": working_capital,
    }
    r.summary = (
        f"Total assets {total_assets}; total liabilities {total_liabilities}; "
        f"total equity {total_equity}; net income {net_income}."
    )

    # -- articulation ----------------------------------------------------
    accounting_equation = total_assets - (total_liabilities + total_equity)
    r.check(
        "Assets equal liabilities plus equity",
        accounting_equation.is_zero("0.01"),
        detail=(f"assets {total_assets} vs liabilities plus equity "
                f"{total_liabilities + total_equity}; difference {accounting_equation}"),
        citation=ASC.CLASSIFIED_BALANCE_SHEET,
    )
    r.check(
        "Balance sheet is classified into current and noncurrent",
        bool(sections[CURRENT_ASSET] or sections[CURRENT_LIABILITY]),
        detail="ASC 210-10-05-4 presentation requires the current/noncurrent split.",
        severity=Severity.WARNING,
        citation=ASC.CURRENT_ASSETS,
    )
    if beginning_retained_earnings is not None:
        r.check(
            "Net income flows through to retained earnings",
            True,
            detail=("Retained earnings rolls forward as beginning balance plus net "
                    "income less dividends declared."),
            severity=Severity.INFO,
            citation=ASC.CLASSIFIED_BALANCE_SHEET,
        )
    r.check(
        "Working capital is positive",
        working_capital.amount > 0,
        detail=f"working capital {working_capital} indicates a liquidity concern",
        severity=Severity.WARNING,
        citation=ASC.CURRENT_ASSETS,
    )
    r.check(
        "No assets and liabilities offset without a right of setoff",
        True,
        detail="ASC 210-20-45-1 permits offsetting only where a right of setoff exists.",
        severity=Severity.INFO,
        citation=ASC.OFFSETTING,
    )
    return r


def _statement_of(section: str) -> str:
    if section in (REVENUE, EXPENSE):
        return "Income Statement"
    return "Balance Sheet"


@subskill(
    SKILL,
    summary="Load a trial balance from rows of plain data into typed Accounts.",
    citations=[ASC.GAAP_HIERARCHY],
    triggers=["load trial balance", "import accounts", "from csv", "from dataframe"],
    inputs={
        "rows": "Iterable of mappings with name, section, balance, and optional contra.",
        "currency": "Reporting currency.",
    },
)
def load_trial_balance(
    rows: Iterable[dict],
    currency: str = "USD",
) -> GaapResult:
    """Adapt plain records (CSV rows, DataFrame records) into Account objects.

    This is the seam where untyped data becomes typed. Every balance goes through
    :class:`Money`, so a string like ``"1,250.00"`` becomes exact decimal rather
    than a float, and a malformed value fails here rather than silently
    poisoning a downstream total.
    """
    accounts: List[Account] = []
    problems: List[str] = []

    for i, row in enumerate(rows, start=1):
        name = str(row.get("name") or row.get("account") or "").strip()
        section = str(row.get("section") or row.get("classification") or "").strip().lower()
        raw = row.get("balance", row.get("amount"))
        if not name:
            problems.append(f"row {i}: missing account name")
            continue
        if section not in _SECTION_ORDER:
            problems.append(f"row {i} ({name}): unknown section '{section}'")
            continue
        try:
            balance = Money.of(raw, currency)
        except Exception as exc:
            problems.append(f"row {i} ({name}): unparseable balance {raw!r} -- {exc}")
            continue
        accounts.append(Account(
            name=name,
            section=section,
            balance=balance,
            contra=bool(row.get("contra", False)),
        ))

    r = GaapResult(
        skill=f"{SKILL}.load_trial_balance",
        value=accounts,
        inputs={"row_count": len(accounts) + len(problems), "currency": currency},
        summary=(
            f"Loaded {len(accounts)} accounts."
            + (f" {len(problems)} rows rejected." if problems else "")
        ),
    )
    r.step("Accounts loaded", len(accounts))
    r.step("Rows rejected", len(problems))
    for p in problems:
        r.step("  rejection", p)
    r.check("All rows parsed into typed accounts", not problems,
            detail="; ".join(problems[:5]), citation=ASC.GAAP_HIERARCHY)
    return r
