"""Financial statement analysis ratios.

Not a GAAP topic — ASC prescribes no ratios — but analysis questions are the
ones most often asked of a financial data tool, and they are exactly where an
unconstrained model invents plausible-looking arithmetic. Defining them once,
with explicit numerators and denominators, means "what is our current ratio"
resolves to one computation rather than to whatever the model recalls.

Every ratio here records its formula in the workpaper, so a reviewer can see
which definition was used. That matters: "debt to equity" has at least three
defensible definitions, and they give materially different answers.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import D, Money, quantize
from ..core.registry import REGISTRY, subskill

SKILL = "ratios"

REGISTRY.declare(
    SKILL,
    title="Financial Statement Analysis",
    topic="205",
    description=(
        "Liquidity, leverage, profitability, and efficiency measures computed "
        "from GAAP statement amounts, each recording the definition used."
    ),
)


def _safe_ratio(numerator: Money, denominator: Money, label: str) -> Decimal:
    if denominator.amount == 0:
        raise ZeroDivisionError(f"{label} is undefined: denominator is zero")
    return numerator / denominator


@subskill(
    SKILL,
    summary="Compute liquidity ratios from current assets and liabilities.",
    citations=[ASC.CURRENT_ASSETS, ASC.CLASSIFIED_BALANCE_SHEET],
    triggers=["current ratio", "quick ratio", "acid test", "liquidity",
              "working capital", "can we pay our bills"],
    inputs={
        "current_assets": "Total current assets.",
        "current_liabilities": "Total current liabilities.",
        "inventory": "Inventory, excluded from the quick ratio.",
        "prepaid_expenses": "Prepaid expenses, excluded from the quick ratio.",
    },
)
def liquidity(
    current_assets: Money,
    current_liabilities: Money,
    inventory: Optional[Money] = None,
    prepaid_expenses: Optional[Money] = None,
) -> GaapResult:
    """Current ratio, quick ratio, and working capital."""
    cur = current_assets.currency
    inv = inventory or Money.zero(cur)
    prepaid = prepaid_expenses or Money.zero(cur)

    working_capital = current_assets - current_liabilities
    current_ratio = _safe_ratio(current_assets, current_liabilities, "current ratio")
    quick_assets = current_assets - inv - prepaid
    quick_ratio = _safe_ratio(quick_assets, current_liabilities, "quick ratio")

    r = GaapResult(
        skill=f"{SKILL}.liquidity",
        value={
            "current_ratio": quantize(current_ratio, 4),
            "quick_ratio": quantize(quick_ratio, 4),
            "working_capital": working_capital,
        },
        inputs={"current_assets": current_assets,
                "current_liabilities": current_liabilities,
                "inventory": inv, "prepaid_expenses": prepaid},
    )
    r.step("Current assets", current_assets)
    r.step("Current liabilities", current_liabilities)
    r.step("Working capital", working_capital, formula="current assets - current liabilities")
    r.step("Current ratio", quantize(current_ratio, 4),
           formula="current assets / current liabilities")
    r.step("Quick assets", quick_assets,
           formula="current assets - inventory - prepaid expenses")
    r.step("Quick ratio", quantize(quick_ratio, 4),
           formula="quick assets / current liabilities")

    r.summary = (
        f"Current ratio {quantize(current_ratio, 2)}, quick ratio "
        f"{quantize(quick_ratio, 2)}, working capital {working_capital}."
    )
    r.assume("Quick asset definition",
             "current assets less inventory and prepaid expenses",
             "entity policy")
    r.check("Working capital is positive", working_capital.amount > 0,
            detail=f"working capital {working_capital}",
            severity=Severity.WARNING, citation=ASC.CURRENT_ASSETS)
    r.check("Current ratio is at least 1.0", current_ratio >= 1,
            severity=Severity.WARNING)
    return r


@subskill(
    SKILL,
    summary="Compute leverage ratios, stating which debt definition was used.",
    citations=[ASC.CLASSIFIED_BALANCE_SHEET],
    triggers=["debt to equity", "leverage", "gearing", "debt ratio",
              "interest coverage", "times interest earned", "solvency"],
    inputs={
        "total_liabilities": "All liabilities.",
        "total_equity": "Total stockholders' equity.",
        "total_assets": "Total assets.",
        "interest_bearing_debt": "Only borrowings, if the narrower definition is wanted.",
        "ebit": "Earnings before interest and taxes, for coverage.",
        "interest_expense": "Interest expense, for coverage.",
    },
)
def leverage(
    total_liabilities: Money,
    total_equity: Money,
    total_assets: Optional[Money] = None,
    interest_bearing_debt: Optional[Money] = None,
    ebit: Optional[Money] = None,
    interest_expense: Optional[Money] = None,
) -> GaapResult:
    """Debt-to-equity on both the all-liabilities and interest-bearing bases.

    Both are reported because "debt to equity" is ambiguous in practice and the
    two can differ by a factor of several for a company with large operating
    liabilities. Naming the definition is the point.
    """
    if total_equity.amount == 0:
        raise ZeroDivisionError("leverage is undefined: equity is zero")

    value: Dict[str, object] = {}
    r = GaapResult(
        skill=f"{SKILL}.leverage",
        value=value,
        inputs={"total_liabilities": total_liabilities, "total_equity": total_equity,
                "total_assets": total_assets,
                "interest_bearing_debt": interest_bearing_debt},
    )

    d_to_e = _safe_ratio(total_liabilities, total_equity, "debt to equity")
    value["debt_to_equity_total_liabilities"] = quantize(d_to_e, 4)
    r.step("Total liabilities", total_liabilities)
    r.step("Total equity", total_equity)
    r.step("Debt to equity (all liabilities)", quantize(d_to_e, 4),
           formula="total liabilities / total equity")

    if interest_bearing_debt is not None:
        narrow = _safe_ratio(interest_bearing_debt, total_equity, "debt to equity")
        value["debt_to_equity_interest_bearing"] = quantize(narrow, 4)
        r.step("Interest-bearing debt", interest_bearing_debt)
        r.step("Debt to equity (interest-bearing only)", quantize(narrow, 4),
               formula="interest-bearing debt / total equity",
               note="Excludes payables, accruals, and deferred revenue.")

    if total_assets is not None and total_assets.amount != 0:
        debt_ratio = _safe_ratio(total_liabilities, total_assets, "debt ratio")
        equity_multiplier = _safe_ratio(total_assets, total_equity, "equity multiplier")
        value["debt_ratio"] = quantize(debt_ratio, 4)
        value["equity_multiplier"] = quantize(equity_multiplier, 4)
        r.step("Debt ratio", quantize(debt_ratio, 4),
               formula="total liabilities / total assets")
        r.step("Equity multiplier", quantize(equity_multiplier, 4),
               formula="total assets / total equity")

    if ebit is not None and interest_expense is not None:
        if interest_expense.amount == 0:
            r.step("Interest coverage", "not meaningful", note="no interest expense")
        else:
            coverage = _safe_ratio(ebit, interest_expense, "interest coverage")
            value["interest_coverage"] = quantize(coverage, 4)
            r.step("EBIT", ebit)
            r.step("Interest expense", interest_expense)
            r.step("Interest coverage", quantize(coverage, 4),
                   formula="EBIT / interest expense")
            r.check("Interest coverage exceeds 1.5x", coverage >= D("1.5"),
                    detail=f"coverage {quantize(coverage, 2)}x",
                    severity=Severity.WARNING)

    r.summary = (
        f"Debt to equity {quantize(d_to_e, 2)} on all liabilities"
        + (f", {quantize(value['debt_to_equity_interest_bearing'], 2)} on "
           "interest-bearing debt only."
           if "debt_to_equity_interest_bearing" in value else ".")
    )
    r.assume("Debt definition", "both all-liabilities and interest-bearing reported",
             "default")
    return r


@subskill(
    SKILL,
    summary="Decompose return on equity into margin, turnover, and leverage (DuPont).",
    citations=[ASC.CLASSIFIED_BALANCE_SHEET],
    triggers=["dupont", "return on equity", "roe", "return on assets", "roa",
              "profit margin", "asset turnover", "profitability"],
    inputs={
        "net_income": "Net income for the period.",
        "revenue": "Total revenue for the period.",
        "total_assets": "Average or ending total assets.",
        "total_equity": "Average or ending total equity.",
    },
)
def dupont(
    net_income: Money,
    revenue: Money,
    total_assets: Money,
    total_equity: Money,
) -> GaapResult:
    """ROE = net margin x asset turnover x equity multiplier.

    The identity is the value here: it shows *why* returns moved. Two companies
    with identical ROE can differ entirely in whether it came from pricing,
    efficiency, or borrowing.
    """
    if revenue.amount == 0:
        raise ZeroDivisionError("DuPont is undefined: revenue is zero")
    if total_assets.amount == 0 or total_equity.amount == 0:
        raise ZeroDivisionError("DuPont is undefined: assets or equity is zero")

    margin = net_income / revenue
    turnover = revenue / total_assets
    multiplier = total_assets / total_equity
    roe = margin * turnover * multiplier
    roa = net_income / total_assets
    direct_roe = net_income / total_equity

    r = GaapResult(
        skill=f"{SKILL}.dupont",
        value={
            "net_margin": quantize(margin, 6),
            "asset_turnover": quantize(turnover, 6),
            "equity_multiplier": quantize(multiplier, 6),
            "return_on_equity": quantize(roe, 6),
            "return_on_assets": quantize(roa, 6),
        },
        inputs={"net_income": net_income, "revenue": revenue,
                "total_assets": total_assets, "total_equity": total_equity},
    )
    r.step("Net income", net_income)
    r.step("Revenue", revenue)
    r.step("Net profit margin", quantize(margin * 100, 4),
           formula="net income / revenue")
    r.step("Asset turnover", quantize(turnover, 4), formula="revenue / total assets")
    r.step("Equity multiplier", quantize(multiplier, 4),
           formula="total assets / total equity")
    r.step("Return on equity", quantize(roe * 100, 4),
           formula="margin x turnover x multiplier")
    r.step("Return on assets", quantize(roa * 100, 4),
           formula="net income / total assets")

    r.summary = (
        f"ROE of {quantize(roe * 100, 2)}% decomposes into a "
        f"{quantize(margin * 100, 2)}% net margin, {quantize(turnover, 2)}x asset "
        f"turnover, and {quantize(multiplier, 2)}x equity multiplier."
    )
    r.check(
        "DuPont decomposition reconciles to direct ROE",
        abs(roe - direct_roe) <= D("0.0000001"),
        detail=f"decomposed {quantize(roe, 6)} vs direct {quantize(direct_roe, 6)}",
    )
    r.assume("Balance sheet basis", "as supplied (average or ending)", "default",
             ASC.CLASSIFIED_BALANCE_SHEET)
    return r
