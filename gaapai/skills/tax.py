"""ASC 740 -- Income Taxes.

Deferred tax measurement on temporary differences, valuation allowances, and
the statutory-to-effective rate reconciliation.

The distinction that drives everything: *temporary* differences reverse and
therefore create deferred tax; *permanent* differences never reverse and only
move the effective rate. Treating a permanent difference as temporary creates a
deferred tax balance that will never unwind.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import D, Money, quantize
from ..core.registry import REGISTRY, subskill

SKILL = "tax"

REGISTRY.declare(
    SKILL,
    title="Income Taxes",
    topic="740",
    description=(
        "Deferred tax assets and liabilities arising from temporary differences, "
        "valuation allowances under the more-likely-than-not threshold, and the "
        "effective tax rate reconciliation."
    ),
)


@dataclass
class TemporaryDifference:
    """A difference between book and tax basis that will reverse."""

    label: str
    book_basis: Money
    tax_basis: Money
    is_asset: bool = True  # True for an asset account, False for a liability

    @property
    def difference(self) -> Money:
        return self.book_basis - self.tax_basis

    @property
    def creates_liability(self) -> bool:
        """Book > tax on an asset (or tax > book on a liability) defers tax to the future."""
        d = self.difference.amount
        return (d > 0) if self.is_asset else (d < 0)


@dataclass
class PermanentDifference:
    """An item that never reverses -- affects the effective rate only."""

    label: str
    pretax_amount: Money
    deductible: bool = False


@subskill(
    SKILL,
    summary="Measure deferred tax assets and liabilities from temporary differences and apply a valuation allowance.",
    citations=[ASC.TAX_DEFERRED, ASC.TAX_RATE, ASC.TAX_VALUATION_ALLOWANCE],
    triggers=["deferred tax", "temporary difference", "dta", "dtl",
              "valuation allowance", "deferred tax asset", "deferred tax liability",
              "more likely than not"],
    inputs={
        "differences": "TemporaryDifference entries.",
        "enacted_rate": "Enacted rate expected to apply when the difference reverses.",
        "nol_carryforward": "Net operating loss carryforward, if any.",
        "realization_probability": "Probability (0..1) that deferred tax assets will be realised.",
    },
)
def deferred_tax(
    differences: Sequence[TemporaryDifference],
    enacted_rate: Decimal | float | str,
    nol_carryforward: Optional[Money] = None,
    realization_probability: Decimal | float | str = 1,
) -> GaapResult:
    """Gross up temporary differences at the enacted rate, then test DTA realisation.

    The valuation allowance is a threshold test, not a probability weighting: if
    realisation is more likely than not (>50%), no allowance; otherwise reduce
    the DTA to the portion that *is* more likely than not. Scaling the DTA by the
    probability is a common but incorrect shortcut.
    """
    rate = D(enacted_rate)
    if not (0 <= rate < 1):
        raise ValueError("enacted rate must be a fraction between 0 and 1")
    if not differences and not nol_carryforward:
        raise ValueError("supply at least one temporary difference or an NOL")

    cur = (differences[0].book_basis.currency if differences
           else nol_carryforward.currency)

    r = GaapResult(
        skill=f"{SKILL}.deferred_tax",
        inputs={"enacted_rate": rate,
                "differences": [{"label": d.label, "book": d.book_basis,
                                 "tax": d.tax_basis, "is_asset": d.is_asset}
                                for d in differences],
                "nol_carryforward": nol_carryforward,
                "realization_probability": D(realization_probability)},
        value=None,
    )
    r.assume("Enacted tax rate", f"{quantize(rate * 100, 2)}%", "observed", ASC.TAX_RATE)

    dtl = Money.zero(cur)
    dta = Money.zero(cur)
    schedule: List[Dict] = []

    for d in differences:
        diff = d.difference
        tax_effect = abs(diff) * rate
        if d.creates_liability:
            dtl = dtl + tax_effect
            kind = "deferred tax liability"
        else:
            dta = dta + tax_effect
            kind = "deferred tax asset"
        schedule.append({
            "item": d.label,
            "book basis": d.book_basis,
            "tax basis": d.tax_basis,
            "difference": diff,
            "tax effect": tax_effect,
            "type": kind,
        })
        r.step(f"{d.label}: book {d.book_basis} vs tax {d.tax_basis}", tax_effect,
               note=kind)

    if nol_carryforward:
        nol_dta = nol_carryforward * rate
        dta = dta + nol_dta
        schedule.append({
            "item": "NOL carryforward",
            "book basis": nol_carryforward,
            "tax basis": Money.zero(cur),
            "difference": nol_carryforward,
            "tax effect": nol_dta,
            "type": "deferred tax asset",
        })
        r.step("NOL carryforward deferred tax asset", nol_dta,
               formula=f"{quantize(nol_carryforward.amount, 2):,} x {rate}")

    r.schedule = schedule
    r.step("Gross deferred tax assets", dta)
    r.step("Gross deferred tax liabilities", dtl)

    prob = D(realization_probability)
    more_likely_than_not = prob > D("0.5")
    if more_likely_than_not:
        allowance = Money.zero(cur)
        r.step("Valuation allowance", allowance,
               note="Realisation is more likely than not; no allowance required.")
    else:
        allowance = dta  # none of the DTA meets the threshold
        r.step("Valuation allowance", -allowance,
               note=f"Realisation probability {prob} does not exceed 50%.")
    r.assume("DTA realisation assessment",
             f"{quantize(prob * 100, 1)}% -- "
             + ("more likely than not" if more_likely_than_not else "not more likely than not"),
             "estimated", ASC.TAX_VALUATION_ALLOWANCE)

    net_dta = dta - allowance
    net_position = net_dta - dtl

    r.step("Net deferred tax asset after allowance", net_dta)
    r.step("Net deferred tax position", net_position,
           note="asset" if net_position.amount >= 0 else "liability")

    r.value = {
        "gross_dta": dta,
        "gross_dtl": dtl,
        "valuation_allowance": allowance,
        "net_deferred_tax": net_position,
    }
    r.summary = (
        f"Gross deferred tax assets {dta}, liabilities {dtl}, valuation allowance "
        f"{allowance}; net deferred tax "
        f"{'asset' if net_position.amount >= 0 else 'liability'} of {abs(net_position)}."
    )
    r.check(
        "Valuation allowance applies the more-likely-than-not threshold",
        True,
        detail=("ASC 740-10-30-5 is a >50% threshold test, not a probability "
                "weighting of the deferred tax asset."),
        severity=Severity.INFO,
        citation=ASC.TAX_VALUATION_ALLOWANCE,
    )
    r.check(
        "Deferred taxes measured at the enacted rate",
        True,
        detail="Proposed or expected rate changes are not anticipated (ASC 740-10-30-8).",
        severity=Severity.INFO,
        citation=ASC.TAX_RATE,
    )
    r.check(
        "Deferred tax assets are realisable",
        more_likely_than_not or dta.amount == 0,
        detail="A full valuation allowance has been recorded against deferred tax assets.",
        severity=Severity.WARNING,
        citation=ASC.TAX_VALUATION_ALLOWANCE,
    )
    return r


@subskill(
    SKILL,
    summary="Reconcile the statutory tax rate to the effective tax rate.",
    citations=[ASC.TAX_RATE_RECONCILIATION, ASC.TAX_DEFERRED],
    triggers=["effective tax rate", "etr", "rate reconciliation", "tax reconciliation",
              "statutory rate", "permanent difference", "why is our tax rate"],
    inputs={
        "pretax_income": "Income before income taxes.",
        "statutory_rate": "Statutory federal rate.",
        "permanent_differences": "PermanentDifference entries.",
        "state_tax_rate_net": "State taxes net of federal benefit, as a rate.",
        "other_items": "Other reconciling items as {label: Money tax effect}.",
    },
)
def effective_tax_rate(
    pretax_income: Money,
    statutory_rate: Decimal | float | str,
    permanent_differences: Optional[Sequence[PermanentDifference]] = None,
    state_tax_rate_net: Decimal | float | str = 0,
    other_items: Optional[Dict[str, Money]] = None,
) -> GaapResult:
    """Build the rate reconciliation from statutory to effective."""
    if pretax_income.amount == 0:
        raise ValueError("effective rate is undefined when pretax income is zero")

    stat = D(statutory_rate)
    perms = list(permanent_differences or [])
    others = dict(other_items or {})
    cur = pretax_income.currency

    r = GaapResult(
        skill=f"{SKILL}.effective_tax_rate",
        inputs={"pretax_income": pretax_income, "statutory_rate": stat,
                "permanent_differences": [{"label": p.label,
                                           "amount": p.pretax_amount,
                                           "deductible": p.deductible} for p in perms],
                "state_tax_rate_net": D(state_tax_rate_net),
                "other_items": others},
        value=None,
    )

    tax_at_statutory = pretax_income * stat
    total_tax = tax_at_statutory
    schedule: List[Dict] = [{
        "item": "Tax at statutory rate",
        "amount": tax_at_statutory.round(2),
        "rate %": quantize(stat * 100, 2),
    }]
    r.step("Pretax income", pretax_income)
    r.step(f"Tax at statutory rate of {quantize(stat * 100, 2)}%", tax_at_statutory)

    for p in perms:
        effect = p.pretax_amount * stat * (Decimal(-1) if p.deductible else Decimal(1))
        total_tax = total_tax + effect
        rate_pts = effect / pretax_income
        schedule.append({
            "item": p.label,
            "amount": effect.round(2),
            "rate %": quantize(rate_pts * 100, 2),
        })
        r.step(f"  {p.label}", effect,
               note=("permanently deductible" if p.deductible else "permanently nondeductible"))

    state = D(state_tax_rate_net)
    if state:
        state_effect = pretax_income * state
        total_tax = total_tax + state_effect
        schedule.append({
            "item": "State taxes, net of federal benefit",
            "amount": state_effect.round(2),
            "rate %": quantize(state * 100, 2),
        })
        r.step("  State taxes, net of federal benefit", state_effect)

    for label, amt in others.items():
        total_tax = total_tax + amt
        schedule.append({
            "item": label,
            "amount": amt.round(2),
            "rate %": quantize((amt / pretax_income) * 100, 2),
        })
        r.step(f"  {label}", amt)

    etr = total_tax / pretax_income
    schedule.append({
        "item": "Total income tax expense",
        "amount": total_tax.round(2),
        "rate %": quantize(etr * 100, 2),
    })
    r.schedule = schedule
    r.step("Total income tax expense", total_tax)
    r.step("Effective tax rate", quantize(etr * 100, 2),
           formula="total tax expense / pretax income")

    r.value = {
        "tax_expense": total_tax,
        "effective_rate": etr,
        "statutory_rate": stat,
        "net_income": pretax_income - total_tax,
    }
    r.summary = (
        f"Effective tax rate is {quantize(etr * 100, 2)}% versus a statutory rate "
        f"of {quantize(stat * 100, 2)}%, on tax expense of {total_tax}."
    )
    r.check(
        "Reconciling items explain the full difference from statutory",
        True,
        detail="Every basis point between statutory and effective is itemised above.",
        severity=Severity.INFO,
        citation=ASC.TAX_RATE_RECONCILIATION,
    )
    r.check(
        "Effective rate is within a plausible range",
        Decimal("-0.5") <= etr <= Decimal("1"),
        detail=f"effective rate {quantize(etr * 100, 2)}% warrants explanation",
        severity=Severity.WARNING,
        citation=ASC.TAX_RATE_RECONCILIATION,
    )
    r.check(
        "Permanent differences excluded from deferred tax",
        True,
        detail=("Permanent differences move the effective rate but never create a "
                "deferred tax balance, because they do not reverse."),
        severity=Severity.INFO,
        citation=ASC.TAX_DEFERRED,
    )
    return r
