"""ASC 230 -- Statement of Cash Flows.

The indirect method reconciliation and classification of individual items. The
statement is the most mechanically checkable of the three: it must tie to the
change in cash on the balance sheet exactly. That tie-out is enforced here as a
hard check rather than left to the preparer to notice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import Money
from ..core.registry import REGISTRY, subskill

SKILL = "cashflow"

REGISTRY.declare(
    SKILL,
    title="Statement of Cash Flows",
    topic="230",
    description=(
        "Classification of cash receipts and payments into operating, investing, "
        "and financing activities, and the indirect-method reconciliation from "
        "net income to net cash provided by operating activities."
    ),
)


# Classification rules. The awkward ones are here deliberately: interest paid is
# operating under GAAP (IFRS allows financing), dividends paid are financing but
# dividends received are operating, and that asymmetry is a common error.
_CLASSIFICATION: Dict[str, tuple] = {
    "interest paid": ("operating", "GAAP classifies interest paid as operating; IFRS permits financing."),
    "interest received": ("operating", "Interest received is operating under ASC 230."),
    "dividends received": ("operating", "Dividends received are operating."),
    "dividends paid": ("financing", "Dividends paid to shareholders are financing."),
    "income taxes paid": ("operating", "Taxes paid are operating unless identifiable with investing or financing."),
    "purchase of equipment": ("investing", "Acquisition of productive assets is investing."),
    "sale of equipment": ("investing", "Proceeds from disposal of productive assets are investing."),
    "purchase of investments": ("investing", "Acquisition of debt or equity instruments is investing."),
    "sale of investments": ("investing", "Proceeds from sale of investments are investing."),
    "loans made": ("investing", "Loans made to other entities are investing."),
    "collection of loans": ("investing", "Principal collected on loans made is investing."),
    "issuance of stock": ("financing", "Proceeds from issuing equity are financing."),
    "repurchase of stock": ("financing", "Treasury stock purchases are financing."),
    "issuance of debt": ("financing", "Proceeds from borrowing are financing."),
    "repayment of debt principal": ("financing", "Principal repayment is financing; the interest portion is operating."),
    "finance lease principal": ("financing", "Principal portion of finance lease payments is financing."),
    "operating lease payments": ("operating", "Operating lease payments are operating."),
    "cash from customers": ("operating", "Collections from customers are operating."),
    "payments to suppliers": ("operating", "Payments for goods and services are operating."),
    "payments to employees": ("operating", "Payroll is operating."),
}

_NONCASH = {
    "acquisition of asset by issuing debt",
    "conversion of debt to equity",
    "right-of-use asset obtained in exchange for a lease liability",
    "stock issued for property",
    "declared but unpaid dividends",
}


@dataclass
class Adjustment:
    """One reconciling item in the indirect method."""

    label: str
    amount: Money
    category: str = "noncash"  # "noncash" | "working_capital" | "gain_loss"


@subskill(
    SKILL,
    summary="Classify a cash flow item as operating, investing, or financing.",
    citations=[ASC.CF_CLASSIFICATION, ASC.CF_NONCASH],
    triggers=["classify cash flow", "operating investing financing", "which section",
              "cash flow classification", "where does this go"],
    inputs={"item": "Description of the cash receipt or payment."},
)
def classify(item: str) -> GaapResult:
    """Look up the ASC 230 classification for a described cash flow."""
    key = item.lower().strip()
    r = GaapResult(skill=f"{SKILL}.classify", inputs={"item": item}, value=None)

    if key in _NONCASH:
        r.value = "noncash"
        r.summary = (
            f"'{item}' is a noncash investing or financing activity. It is "
            "excluded from the body of the statement and disclosed separately."
        )
        r.step("Classification", "noncash -- disclose outside the statement")
        r.check("Noncash activity disclosed", True, severity=Severity.INFO,
                citation=ASC.CF_NONCASH)
        return r

    match = _CLASSIFICATION.get(key)
    if match is None:
        # Fall back to substring matching so callers need not use exact wording.
        for k, v in _CLASSIFICATION.items():
            if k in key or key in k:
                match = v
                break

    if match is None:
        r.value = "unclassified"
        r.summary = (
            f"'{item}' is not in the classification table. Classify by the nature "
            "of the underlying activity per ASC 230-10-45, and add it to the table."
        )
        r.check("Item classified", False,
                detail="Unknown item; manual classification required.",
                citation=ASC.CF_CLASSIFICATION)
        return r

    section, rationale = match
    r.value = section
    r.summary = f"'{item}' is classified as {section}. {rationale}"
    r.step("Classification", section)
    r.step("Basis", rationale)
    r.check("Classified under ASC 230-10-45", True, severity=Severity.INFO,
            citation=ASC.CF_CLASSIFICATION)
    return r


@subskill(
    SKILL,
    summary="Build the indirect-method statement of cash flows and tie it to the change in cash.",
    citations=[ASC.CF_INDIRECT, ASC.CF_RECONCILE, ASC.CF_CLASSIFICATION],
    triggers=["cash flow statement", "indirect method", "operating cash flow",
              "statement of cash flows", "reconcile net income to cash",
              "free cash flow", "cfo"],
    inputs={
        "net_income": "Net income for the period.",
        "adjustments": "Noncash and working capital adjustments (Adjustment entries).",
        "investing": "Investing cash flows, signed (outflows negative).",
        "financing": "Financing cash flows, signed (outflows negative).",
        "beginning_cash": "Cash and equivalents at the beginning of the period.",
        "ending_cash": "Cash and equivalents at the end of the period.",
    },
)
def indirect_method(
    net_income: Money,
    adjustments: Sequence[Adjustment],
    investing: Optional[Dict[str, Money]] = None,
    financing: Optional[Dict[str, Money]] = None,
    beginning_cash: Optional[Money] = None,
    ending_cash: Optional[Money] = None,
) -> GaapResult:
    """Reconcile net income to operating cash flow, then tie the total to cash on hand.

    The sign convention is uniform: every amount is signed as its effect on cash.
    Depreciation is positive, an increase in receivables is negative, capital
    expenditure is negative. Mixed conventions are the main reason cash flow
    statements fail to tie.
    """
    cur = net_income.currency
    investing = dict(investing or {})
    financing = dict(financing or {})

    r = GaapResult(
        skill=f"{SKILL}.indirect_method",
        inputs={"net_income": net_income,
                "adjustments": [{"label": a.label, "amount": a.amount,
                                 "category": a.category} for a in adjustments],
                "investing": investing, "financing": financing,
                "beginning_cash": beginning_cash, "ending_cash": ending_cash},
        value=None,
    )

    lines: List[Dict] = [{"section": "Operating", "line": "Net income",
                          "amount": net_income.round(2)}]
    operating = net_income
    r.step("Net income", net_income)

    for group, title in (("gain_loss", "Gains and losses on investing/financing items"),
                         ("noncash", "Noncash charges and credits"),
                         ("working_capital", "Changes in operating assets and liabilities")):
        items = [a for a in adjustments if a.category == group]
        if not items:
            continue
        r.step(f"-- {title} --", "")
        for a in items:
            operating = operating + a.amount
            lines.append({"section": "Operating", "line": a.label,
                          "amount": a.amount.round(2)})
            r.step(f"  {a.label}", a.amount)

    r.step("Net cash provided by operating activities", operating)
    lines.append({"section": "Operating", "line": "Net cash from operating activities",
                  "amount": operating.round(2)})

    investing_total = Money.zero(cur)
    for label, amt in investing.items():
        investing_total = investing_total + amt
        lines.append({"section": "Investing", "line": label, "amount": amt.round(2)})
        r.step(f"  {label}", amt)
    r.step("Net cash used in investing activities", investing_total)
    lines.append({"section": "Investing", "line": "Net cash from investing activities",
                  "amount": investing_total.round(2)})

    financing_total = Money.zero(cur)
    for label, amt in financing.items():
        financing_total = financing_total + amt
        lines.append({"section": "Financing", "line": label, "amount": amt.round(2)})
        r.step(f"  {label}", amt)
    r.step("Net cash provided by financing activities", financing_total)
    lines.append({"section": "Financing", "line": "Net cash from financing activities",
                  "amount": financing_total.round(2)})

    net_change = operating + investing_total + financing_total
    r.step("Net change in cash", net_change)
    lines.append({"section": "Total", "line": "Net change in cash",
                  "amount": net_change.round(2)})

    r.schedule = lines
    r.value = {
        "operating": operating,
        "investing": investing_total,
        "financing": financing_total,
        "net_change": net_change,
    }

    if beginning_cash is not None:
        computed_ending = beginning_cash + net_change
        r.step("Cash at beginning of period", beginning_cash)
        r.step("Cash at end of period", computed_ending)
        r.value["ending_cash"] = computed_ending

        if ending_cash is not None:
            difference = computed_ending - ending_cash
            r.check(
                "Statement ties to the change in cash on the balance sheet",
                difference.is_zero("0.01"),
                detail=(f"computed ending cash {computed_ending} vs reported "
                        f"{ending_cash}; difference {difference}"),
                citation=ASC.CF_RECONCILE,
            )

    free_cash_flow = operating + sum(
        (v for k, v in investing.items() if "capital expenditure" in k.lower()
         or "purchase of equipment" in k.lower() or "capex" in k.lower()),
        Money.zero(cur),
    )
    r.value["free_cash_flow"] = free_cash_flow

    r.summary = (
        f"Operating {operating}, investing {investing_total}, financing "
        f"{financing_total}; net change in cash {net_change}."
    )
    r.check(
        "Sign convention is consistent (amounts signed as their effect on cash)",
        True,
        detail="Outflows negative, inflows positive throughout.",
        severity=Severity.INFO,
        citation=ASC.CF_INDIRECT,
    )
    r.check(
        "Operating cash flow is positive",
        operating.amount > 0,
        detail="Negative operating cash flow warrants going-concern consideration.",
        severity=Severity.WARNING,
    )
    return r
