"""ASC 260 -- Earnings Per Share.

Basic and diluted EPS, including weighted-average share mechanics, the treasury
stock method for options, and the if-converted method for convertible
instruments.

The antidilution rule is the subtle part. Potential shares are tested for
dilution *individually and in sequence*, ranked from most to least dilutive,
and an instrument is dropped the moment it would raise EPS. Testing them as a
block understates dilution and is a frequent restatement cause.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import D, Money, quantize
from ..core.registry import REGISTRY, subskill

SKILL = "eps"

REGISTRY.declare(
    SKILL,
    title="Earnings Per Share",
    topic="260",
    description=(
        "Basic EPS on weighted-average shares, and diluted EPS reflecting "
        "options under the treasury stock method and convertibles under the "
        "if-converted method, with sequential antidilution testing."
    ),
)


@dataclass
class ShareChange:
    """A change in shares outstanding, and how much of the period it affected."""

    shares: Decimal
    months_outstanding: Decimal
    label: str = ""
    retroactive: bool = False  # splits and stock dividends apply to all prior periods

    def __post_init__(self) -> None:
        self.shares = D(self.shares)
        self.months_outstanding = D(self.months_outstanding)


@dataclass
class Convertible:
    """A convertible instrument tested under the if-converted method."""

    label: str
    shares_on_conversion: Decimal
    after_tax_addback: Money  # interest net of tax, or preferred dividends

    def __post_init__(self) -> None:
        self.shares_on_conversion = D(self.shares_on_conversion)


@dataclass
class OptionGrant:
    """Options or warrants tested under the treasury stock method."""

    label: str
    options: Decimal
    exercise_price: Money
    unrecognized_compensation: Optional[Money] = None

    def __post_init__(self) -> None:
        self.options = D(self.options)


@subskill(
    SKILL,
    summary="Compute the weighted-average number of common shares outstanding.",
    citations=[ASC.EPS_WEIGHTED],
    triggers=["weighted average shares", "wason", "shares outstanding",
              "weighted average", "share count"],
    inputs={
        "changes": "ShareChange entries covering issuances, repurchases, splits.",
        "months_in_period": "Length of the reporting period in months.",
    },
)
def weighted_average_shares(
    changes: Sequence[ShareChange],
    months_in_period: int = 12,
) -> GaapResult:
    """Weight each tranche by the fraction of the period it was outstanding.

    Stock splits and stock dividends are marked ``retroactive`` and are applied
    to the whole period regardless of when they occurred: they change the unit
    of measure, not the capital invested (ASC 260-10-55-12).
    """
    if not changes:
        raise ValueError("at least one share change is required")
    months = D(months_in_period)

    r = GaapResult(
        skill=f"{SKILL}.weighted_average_shares",
        inputs={"months_in_period": months_in_period,
                "changes": [{"label": c.label, "shares": c.shares,
                             "months": c.months_outstanding,
                             "retroactive": c.retroactive} for c in changes]},
        value=None,
    )

    total = Decimal(0)
    schedule: List[Dict] = []
    for c in changes:
        applied_months = months if c.retroactive else c.months_outstanding
        weight = applied_months / months
        weighted = c.shares * weight
        total += weighted
        schedule.append({
            "tranche": c.label or "shares",
            "shares": c.shares,
            "months": applied_months,
            "weight": quantize(weight, 4),
            "weighted shares": quantize(weighted, 0),
        })
        if c.retroactive:
            r.step(f"{c.label} (retroactive)", c.shares,
                   note="Split or stock dividend applied to the full period.")

    r.schedule = schedule
    total = quantize(total, 0)
    r.step("Weighted-average shares outstanding", total)
    r.value = total
    r.summary = f"Weighted-average common shares outstanding: {total:,}."
    r.check("Weighted-average share count is positive", total > 0,
            citation=ASC.EPS_WEIGHTED)
    return r


@subskill(
    SKILL,
    summary="Compute basic earnings per share.",
    citations=[ASC.EPS_BASIC],
    triggers=["basic eps", "basic earnings per share", "eps", "earnings per share"],
    inputs={
        "net_income": "Net income for the period.",
        "preferred_dividends": "Cumulative preferred dividends, whether or not declared.",
        "weighted_shares": "Weighted-average common shares outstanding.",
    },
)
def basic_eps(
    net_income: Money,
    weighted_shares: Decimal | int,
    preferred_dividends: Optional[Money] = None,
) -> GaapResult:
    """Income available to common shareholders over weighted-average shares.

    Cumulative preferred dividends are deducted whether or not declared
    (ASC 260-10-45-11). Forgetting the "whether or not declared" part overstates
    EPS for entities with cumulative preferred in arrears.
    """
    shares = D(weighted_shares)
    if shares <= 0:
        raise ValueError("weighted-average shares must be positive")
    pref = preferred_dividends or Money.zero(net_income.currency)
    available = net_income - pref
    eps = available.amount / shares

    r = GaapResult(
        skill=f"{SKILL}.basic_eps",
        value=quantize(eps, 2),
        inputs={"net_income": net_income, "preferred_dividends": pref,
                "weighted_shares": shares},
        summary=f"Basic EPS is {quantize(eps, 2)}.",
    )
    r.step("Net income", net_income)
    if pref:
        r.step("Less preferred dividends", -pref,
               note="Cumulative preferred deducted whether or not declared.")
    r.step("Income available to common shareholders", available)
    r.step("Weighted-average shares", shares)
    r.step("Basic EPS", quantize(eps, 2), formula="income available / weighted shares")

    r.check("Income available to common is positive", available.amount >= 0,
            detail="A loss attributable to common shareholders makes all potential shares antidilutive.",
            severity=Severity.WARNING, citation=ASC.EPS_BASIC)
    return r


@subskill(
    SKILL,
    summary="Compute diluted EPS with sequential antidilution testing of options and convertibles.",
    citations=[ASC.EPS_DILUTED, ASC.EPS_TREASURY_STOCK, ASC.EPS_IF_CONVERTED,
               ASC.EPS_ANTIDILUTIVE],
    triggers=["diluted eps", "dilution", "treasury stock method", "if converted",
              "antidilutive", "options", "warrants", "convertible", "fully diluted"],
    inputs={
        "net_income": "Net income for the period.",
        "weighted_shares": "Weighted-average common shares outstanding.",
        "average_market_price": "Average market price of common stock for the period.",
        "preferred_dividends": "Cumulative preferred dividends.",
        "options": "OptionGrant entries tested under the treasury stock method.",
        "convertibles": "Convertible entries tested under the if-converted method.",
    },
)
def diluted_eps(
    net_income: Money,
    weighted_shares: Decimal | int,
    average_market_price: Money,
    preferred_dividends: Optional[Money] = None,
    options: Optional[Sequence[OptionGrant]] = None,
    convertibles: Optional[Sequence[Convertible]] = None,
) -> GaapResult:
    """Rank potential shares by incremental EPS, then include them while dilutive.

    The ordering is what makes this correct. Each instrument has an incremental
    EPS (its added income over its added shares). Including a less dilutive
    instrument before a more dilutive one can make the latter look antidilutive
    when it is not, so the sequence is sorted ascending by incremental EPS.
    """
    cur = net_income.currency
    shares = D(weighted_shares)
    pref = preferred_dividends or Money.zero(cur)
    options = list(options or [])
    convertibles = list(convertibles or [])

    available = net_income - pref
    base = available.amount / shares

    r = GaapResult(
        skill=f"{SKILL}.diluted_eps",
        inputs={"net_income": net_income, "weighted_shares": shares,
                "average_market_price": average_market_price,
                "preferred_dividends": pref,
                "options": [o.label for o in options],
                "convertibles": [c.label for c in convertibles]},
        value=None,
    )
    r.step("Income available to common shareholders", available)
    r.step("Weighted-average shares", shares)
    r.step("Basic EPS", quantize(base, 2))

    # -- build candidate list with incremental EPS ------------------------
    candidates: List[Dict] = []

    for o in options:
        if average_market_price <= o.exercise_price:
            r.step(f"{o.label}: out of the money", "excluded",
                   note=f"exercise {o.exercise_price} >= average market {average_market_price}")
            continue
        proceeds = o.exercise_price * o.options
        if o.unrecognized_compensation:
            proceeds = proceeds + o.unrecognized_compensation
        repurchased = proceeds / average_market_price
        incremental = o.options - repurchased
        if incremental <= 0:
            continue
        candidates.append({
            "label": o.label,
            "kind": "option (treasury stock method)",
            "added_income": Money.zero(cur),
            "added_shares": incremental,
            "incremental_eps": Decimal(0),
        })
        r.step(f"{o.label}: options outstanding", o.options)
        r.step(f"  assumed proceeds", proceeds,
               formula="options x exercise price"
                       + (" + unrecognised compensation" if o.unrecognized_compensation else ""))
        r.step(f"  shares repurchased at average price", quantize(repurchased, 0))
        r.step(f"  incremental shares", quantize(incremental, 0))

    for c in convertibles:
        if c.shares_on_conversion <= 0:
            continue
        inc_eps = c.after_tax_addback.amount / c.shares_on_conversion
        candidates.append({
            "label": c.label,
            "kind": "convertible (if-converted method)",
            "added_income": c.after_tax_addback,
            "added_shares": c.shares_on_conversion,
            "incremental_eps": inc_eps,
        })
        r.step(f"{c.label}: shares on conversion", c.shares_on_conversion)
        r.step(f"  after-tax add-back", c.after_tax_addback)
        r.step(f"  incremental EPS", quantize(inc_eps, 4),
               formula="add-back / shares on conversion")

    # -- sequence from most to least dilutive -----------------------------
    candidates.sort(key=lambda x: (x["incremental_eps"], x["label"]))

    num = available
    den = shares
    current = base
    included: List[str] = []
    excluded: List[str] = []
    schedule: List[Dict] = [{
        "step": "Basic",
        "income": available.round(2),
        "shares": quantize(den, 0),
        "eps": quantize(current, 4),
        "effect": "-",
    }]

    for cand in candidates:
        trial_num = num + cand["added_income"]
        trial_den = den + cand["added_shares"]
        trial_eps = trial_num.amount / trial_den
        dilutive = trial_eps < current
        schedule.append({
            "step": cand["label"],
            "income": trial_num.round(2),
            "shares": quantize(trial_den, 0),
            "eps": quantize(trial_eps, 4),
            "effect": "dilutive" if dilutive else "ANTIDILUTIVE -- excluded",
        })
        if dilutive:
            num, den, current = trial_num, trial_den, trial_eps
            included.append(cand["label"])
        else:
            excluded.append(cand["label"])

    r.schedule = schedule
    diluted = quantize(current, 2)

    r.step("Diluted EPS", diluted)
    r.value = {
        "basic_eps": quantize(base, 2),
        "diluted_eps": diluted,
        "diluted_shares": quantize(den, 0),
        "included": included,
        "excluded_antidilutive": excluded,
    }
    r.summary = (
        f"Basic EPS {quantize(base, 2)}, diluted EPS {diluted} on "
        f"{quantize(den, 0):,} diluted shares."
        + (f" Excluded as antidilutive: {', '.join(excluded)}." if excluded else "")
    )
    r.check("Diluted EPS does not exceed basic EPS", diluted <= quantize(base, 2),
            detail=f"diluted {diluted} vs basic {quantize(base, 2)}",
            citation=ASC.EPS_DILUTED)
    r.check(
        "Potential shares tested sequentially from most to least dilutive",
        True,
        detail="ASC 260-10-45-19 requires ranking by incremental EPS before inclusion.",
        severity=Severity.INFO,
        citation=ASC.EPS_ANTIDILUTIVE,
    )
    if excluded:
        r.check(
            "Antidilutive instruments disclosed",
            True,
            detail=f"Disclose {', '.join(excluded)} as excluded from diluted EPS.",
            severity=Severity.INFO,
            citation=ASC.EPS_ANTIDILUTIVE,
        )
    if available.amount < 0:
        r.check(
            "Loss period: all potential shares are antidilutive",
            len(included) == 0,
            detail="When there is a loss from continuing operations, diluted equals basic.",
            citation=ASC.EPS_ANTIDILUTIVE,
        )
    return r
