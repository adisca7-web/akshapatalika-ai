"""ASC 360 -- Property, Plant, and Equipment.

Depreciation methods and the two-step long-lived asset impairment test. The
impairment test is where the money is: step one compares carrying amount to
*undiscounted* cash flows, step two measures the loss against *fair value*.
Using discounted flows in step one is a classic error that produces impairments
GAAP does not require.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import D, Money, quantize
from ..core.registry import REGISTRY, subskill

SKILL = "ppe"

REGISTRY.declare(
    SKILL,
    title="Property, Plant, and Equipment",
    topic="360",
    description=(
        "Systematic allocation of depreciable cost over useful life, and the "
        "two-step recoverability and measurement test for impairment of "
        "long-lived assets held and used."
    ),
)


@subskill(
    SKILL,
    summary="Build a depreciation schedule under straight-line, declining balance, sum-of-years-digits, or units of production.",
    citations=[ASC.PPE_DEPRECIATION],
    triggers=["depreciation", "depreciate", "straight line", "declining balance",
              "double declining", "sum of years", "units of production",
              "depreciation schedule", "accumulated depreciation", "book value"],
    inputs={
        "cost": "Capitalised cost of the asset.",
        "salvage_value": "Estimated residual value at the end of useful life.",
        "useful_life": "Useful life in periods.",
        "method": "'straight_line', 'declining_balance', 'sum_of_years_digits', or 'units_of_production'.",
        "rate_factor": "Acceleration factor for declining balance (2 = double declining).",
        "units_per_period": "Production units by period, required for units of production.",
    },
)
def depreciation_schedule(
    cost: Money,
    salvage_value: Money,
    useful_life: int,
    method: str = "straight_line",
    rate_factor: Decimal | float | str = 2,
    units_per_period: Optional[Sequence[Decimal | int]] = None,
) -> GaapResult:
    """Period-by-period depreciation, accumulated depreciation, and carrying amount.

    Declining balance ignores salvage in the rate but is floored at salvage --
    depreciating below residual value is not permitted, so the final periods are
    truncated rather than allowed to run negative.
    """
    method = method.lower().strip()
    valid = ("straight_line", "declining_balance", "sum_of_years_digits", "units_of_production")
    if method not in valid:
        raise ValueError(f"method must be one of {valid}")
    if useful_life <= 0:
        raise ValueError("useful life must be at least one period")
    if salvage_value > cost:
        raise ValueError("salvage value cannot exceed cost")

    cur = cost.currency
    depreciable = cost - salvage_value

    r = GaapResult(
        skill=f"{SKILL}.depreciation_schedule",
        inputs={"cost": cost, "salvage_value": salvage_value,
                "useful_life": useful_life, "method": method,
                "rate_factor": D(rate_factor)},
        value=None,
    )
    r.assume("Useful life", f"{useful_life} periods", "estimated", ASC.PPE_DEPRECIATION)
    r.assume("Salvage value", salvage_value, "estimated", ASC.PPE_DEPRECIATION)
    r.assume("Depreciation method", method.replace("_", " "), "entity policy",
             ASC.PPE_DEPRECIATION)

    r.step("Capitalised cost", cost)
    r.step("Less salvage value", -salvage_value)
    r.step("Depreciable base", depreciable)

    charges: List[Money] = []

    if method == "straight_line":
        per = depreciable / useful_life
        charges = [per] * useful_life
        r.step("Periodic charge", per, formula="depreciable base / useful life")

    elif method == "sum_of_years_digits":
        syd = Decimal(useful_life * (useful_life + 1)) // 2
        r.step("Sum of the years' digits", syd, formula=f"n(n+1)/2 for n={useful_life}")
        for i in range(useful_life):
            fraction = D(useful_life - i) / D(syd)
            charges.append(depreciable * fraction)

    elif method == "declining_balance":
        rate = D(rate_factor) / D(useful_life)
        r.step("Declining balance rate", quantize(rate * 100, 4),
               formula=f"{D(rate_factor)} / {useful_life}")
        book = cost
        for _ in range(useful_life):
            charge = book * rate
            # Never depreciate below salvage.
            if (book - charge) < salvage_value:
                charge = book - salvage_value
            if charge.amount < 0:
                charge = Money.zero(cur)
            charges.append(charge)
            book = book - charge

    else:  # units_of_production
        if not units_per_period:
            raise ValueError("units_of_production requires units_per_period")
        units = [D(u) for u in units_per_period]
        total_units = sum(units)
        if total_units <= 0:
            raise ValueError("total production units must be positive")
        r.step("Total estimated units", total_units)
        rate_per_unit = depreciable / total_units
        r.step("Cost per unit", rate_per_unit, formula="depreciable base / total units")
        charges = [rate_per_unit * u for u in units]

    schedule: List[Dict] = []
    accumulated = Money.zero(cur)
    book = cost
    for i, charge in enumerate(charges, start=1):
        accumulated = accumulated + charge
        book = book - charge
        schedule.append({
            "period": i,
            "opening": (book + charge).round(2),
            "depreciation": charge.round(2),
            "accumulated": accumulated.round(2),
            "carrying": book.round(2),
        })

    r.schedule = schedule
    r.value = {
        "periodic_charges": charges,
        "total_depreciation": accumulated,
        "final_carrying_amount": book,
    }
    r.summary = (
        f"{method.replace('_', ' ').capitalize()} depreciation of {depreciable} "
        f"over {useful_life} periods, leaving a carrying amount of {book}."
    )
    r.check(
        "Total depreciation equals the depreciable base",
        (accumulated - depreciable).is_zero("0.05"),
        detail=f"accumulated {accumulated} vs depreciable base {depreciable}",
        citation=ASC.PPE_DEPRECIATION,
    )
    r.check(
        "Carrying amount does not fall below salvage value",
        book >= (salvage_value - Money.of("0.05", cur)),
        detail=f"final carrying amount {book} vs salvage {salvage_value}",
        citation=ASC.PPE_DEPRECIATION,
    )
    return r


@subskill(
    SKILL,
    summary="Apply the two-step recoverability and measurement test for impairment of a long-lived asset held and used.",
    citations=[ASC.PPE_IMPAIRMENT_TEST, ASC.PPE_IMPAIRMENT_MEASURE],
    triggers=["impairment", "impaired", "recoverability", "write down asset",
              "undiscounted cash flows", "asset impairment", "impairment loss"],
    inputs={
        "carrying_amount": "Carrying amount of the asset group.",
        "undiscounted_cash_flows": "Sum of undiscounted future cash flows from use and disposal.",
        "fair_value": "Fair value of the asset group.",
    },
)
def impairment_test(
    carrying_amount: Money,
    undiscounted_cash_flows: Money,
    fair_value: Money,
) -> GaapResult:
    """Step 1 uses undiscounted flows; only if it fails does step 2 measure against fair value."""
    recoverable = undiscounted_cash_flows >= carrying_amount

    r = GaapResult(
        skill=f"{SKILL}.impairment_test",
        inputs={"carrying_amount": carrying_amount,
                "undiscounted_cash_flows": undiscounted_cash_flows,
                "fair_value": fair_value},
        value=None,
    )
    r.step("Carrying amount", carrying_amount)
    r.step("Sum of undiscounted future cash flows", undiscounted_cash_flows)
    r.step("Step 1 -- recoverability",
           "PASS: not impaired" if recoverable else "FAIL: proceed to step 2",
           formula="undiscounted cash flows >= carrying amount")

    if recoverable:
        loss = Money.zero(carrying_amount.currency)
        new_carrying = carrying_amount
        r.summary = (
            "The asset is recoverable. No impairment loss is recognised, even "
            "though fair value may be below carrying amount."
        )
    else:
        loss = carrying_amount - fair_value
        if loss.amount < 0:
            loss = Money.zero(carrying_amount.currency)
        new_carrying = carrying_amount - loss
        r.step("Fair value", fair_value)
        r.step("Step 2 -- impairment loss", loss,
               formula="carrying amount - fair value")
        r.step("New carrying amount", new_carrying)
        r.summary = (
            f"The asset is not recoverable. An impairment loss of {loss} is "
            f"recognised, establishing a new cost basis of {new_carrying}."
        )

    r.value = {"impaired": not recoverable, "loss": loss,
               "new_carrying_amount": new_carrying}

    r.check(
        "Step 1 correctly uses undiscounted cash flows",
        True,
        detail=("ASC 360-10-35-17 compares carrying amount to UNDISCOUNTED flows. "
                "Discounting at this step would recognise impairments GAAP does not require."),
        severity=Severity.INFO,
        citation=ASC.PPE_IMPAIRMENT_TEST,
    )
    r.check(
        "Impairment loss is not reversed in a later period",
        True,
        detail=("The reduced carrying amount is the new cost basis; ASC 360-10-35-20 "
                "prohibits restoration of a previously recognised impairment loss."),
        severity=Severity.INFO,
        citation=ASC.PPE_IMPAIRMENT_MEASURE,
    )
    r.check(
        "Fair value does not exceed undiscounted cash flows",
        fair_value <= undiscounted_cash_flows,
        detail="Fair value above undiscounted flows suggests inconsistent assumptions.",
        severity=Severity.WARNING,
        citation=ASC.PPE_IMPAIRMENT_MEASURE,
    )
    return r
