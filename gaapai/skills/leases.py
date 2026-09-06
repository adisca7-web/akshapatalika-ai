"""ASC 842 -- Leases.

Classification, initial measurement, and the subsequent-measurement schedules
for both lessee models. The two models diverge in a way that trips people up:
a finance lease produces front-loaded total expense (interest plus straight-line
amortisation), while an operating lease produces a flat single lease cost with a
plugged amortisation figure. Both start from the same liability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import D, Money, quantize
from ..core.registry import REGISTRY, subskill
from ..core.timevalue import (
    effective_interest_schedule,
    periodic_rate,
    present_value,
    pv_annuity,
)

SKILL = "leases"

REGISTRY.declare(
    SKILL,
    title="Leases",
    topic="842",
    description=(
        "Lessee accounting: classify the lease, measure the liability at the "
        "present value of unpaid payments, recognise a right-of-use asset, and "
        "amortise both over the lease term."
    ),
)


@dataclass
class LeaseTerms:
    """The inputs that drive classification and measurement."""

    payment: Money
    periods: int
    annual_discount_rate: Decimal
    periods_per_year: int = 12
    payments_in_advance: bool = True  # annuity due is the market norm
    transfers_ownership: bool = False
    purchase_option_reasonably_certain: bool = False
    economic_life_periods: Optional[int] = None
    fair_value: Optional[Money] = None
    specialised_asset: bool = False
    initial_direct_costs: Optional[Money] = None
    incentives_received: Optional[Money] = None
    prepaid_at_commencement: Optional[Money] = None
    residual_value_guarantee: Optional[Money] = None

    def __post_init__(self) -> None:
        self.annual_discount_rate = D(self.annual_discount_rate)
        if self.periods <= 0:
            raise ValueError("lease term must cover at least one period")

    @property
    def rate(self) -> Decimal:
        return periodic_rate(self.annual_discount_rate, self.periods_per_year)

    @property
    def term_years(self) -> Decimal:
        return D(self.periods) / D(self.periods_per_year)


@subskill(
    SKILL,
    summary="Classify a lessee's lease as finance or operating using the five ASC 842-10-25-2 criteria.",
    citations=[ASC.LEASE_CLASSIFY, ASC.LEASE_SHORT_TERM],
    triggers=["classify lease", "finance or operating", "lease classification",
              "is it a capital lease", "operating lease", "finance lease"],
    inputs={"terms": "LeaseTerms describing the arrangement."},
    judgement=True,
)
def classify_lease(terms: LeaseTerms) -> GaapResult:
    """Any one criterion met means finance; none met means operating.

    ASC 842 removed the bright lines that ASC 840 had (75% / 90%), but the Board
    kept them as *examples* of "major part" and "substantially all". They are
    applied here as the conventional thresholds and flagged as a policy
    assumption rather than presented as a rule of the standard.
    """
    major_part = Decimal("0.75")
    substantially_all = Decimal("0.90")

    life_test = None
    if terms.economic_life_periods:
        life_ratio = D(terms.periods) / D(terms.economic_life_periods)
        life_test = life_ratio >= major_part

    # The classification test uses the PV of lease payments. A residual value
    # guarantee is part of that stream, so it belongs in the numerator here as
    # well as in measurement.
    pv = pv_annuity(terms.payment, terms.rate, terms.periods,
                    due=terms.payments_in_advance)
    if terms.residual_value_guarantee:
        pv = pv + Money(
            terms.residual_value_guarantee.amount
            / ((Decimal(1) + terms.rate) ** terms.periods),
            terms.payment.currency,
        )

    fv_test = None
    fv_ratio = None
    if terms.fair_value and terms.fair_value.amount > 0:
        fv_ratio = pv.amount / terms.fair_value.amount
        fv_test = fv_ratio >= substantially_all

    criteria = {
        "(a) Ownership transfers by end of term": terms.transfers_ownership,
        "(b) Purchase option reasonably certain of exercise": terms.purchase_option_reasonably_certain,
        "(c) Term is a major part of remaining economic life": bool(life_test),
        "(d) PV of payments is substantially all of fair value": bool(fv_test),
        "(e) Asset is so specialised it has no alternative use": terms.specialised_asset,
    }
    is_finance = any(criteria.values())

    r = GaapResult(
        skill=f"{SKILL}.classify_lease",
        value="finance" if is_finance else "operating",
        inputs={
            "payment": terms.payment, "periods": terms.periods,
            "annual_discount_rate": terms.annual_discount_rate,
            "transfers_ownership": terms.transfers_ownership,
            "purchase_option": terms.purchase_option_reasonably_certain,
            "economic_life_periods": terms.economic_life_periods,
            "fair_value": terms.fair_value,
            "specialised_asset": terms.specialised_asset,
        },
        summary="",
    )
    r.assume("'Major part' threshold", f"{major_part:%}", "entity policy", ASC.LEASE_CLASSIFY)
    r.assume("'Substantially all' threshold", f"{substantially_all:%}", "entity policy",
             ASC.LEASE_CLASSIFY)
    r.assume("Discount rate (annual)", terms.annual_discount_rate, "estimated",
             ASC.LEASE_INITIAL)

    for label, met in criteria.items():
        r.step(label, "MET" if met else "not met")
    if life_test is not None:
        r.step("  lease term / economic life",
               quantize(D(terms.periods) / D(terms.economic_life_periods) * 100, 2))
    if fv_ratio is not None:
        r.step("  PV of payments / fair value", quantize(fv_ratio * 100, 2))

    r.value = "finance" if is_finance else "operating"
    r.summary = (
        "Finance lease: recognise interest on the liability and straight-line "
        "amortisation of the right-of-use asset separately."
        if is_finance else
        "Operating lease: recognise a single straight-line lease cost over the term."
    )
    r.check(
        "Lease exceeds the twelve-month short-term threshold",
        terms.term_years > 1,
        detail=("Term is twelve months or less. If there is no purchase option "
                "reasonably certain of exercise, the entity may elect the "
                "short-term exemption and recognise cost straight-line with no "
                "balance sheet asset or liability."),
        severity=Severity.WARNING,
        citation=ASC.LEASE_SHORT_TERM,
    )
    r.check("Fair value supplied for the 90% test", terms.fair_value is not None,
            detail="Without fair value, criterion (d) cannot be evaluated.",
            severity=Severity.WARNING, citation=ASC.LEASE_CLASSIFY)
    return r


@subskill(
    SKILL,
    summary="Measure the lease liability and right-of-use asset at commencement.",
    citations=[ASC.LEASE_INITIAL, ASC.LEASE_ROU],
    triggers=["initial measurement", "lease liability", "right of use asset",
              "rou asset", "commencement", "present value of lease payments"],
    inputs={"terms": "LeaseTerms describing the arrangement."},
)
def initial_measurement(terms: LeaseTerms) -> GaapResult:
    """Liability is the PV of unpaid payments; the ROU asset adjusts it for costs and incentives."""
    cur = terms.payment.currency
    rate = terms.rate

    liability = pv_annuity(terms.payment, rate, terms.periods,
                           due=terms.payments_in_advance)
    if terms.residual_value_guarantee:
        rvg_pv = present_value([terms.residual_value_guarantee], rate,
                               due=False, currency=cur)
        # A guarantee is settled at the end of the term, discount over full term.
        rvg_pv = Money(terms.residual_value_guarantee.amount /
                       ((Decimal(1) + rate) ** terms.periods), cur)
        liability = liability + rvg_pv

    idc = terms.initial_direct_costs or Money.zero(cur)
    inc = terms.incentives_received or Money.zero(cur)
    prepaid = terms.prepaid_at_commencement or Money.zero(cur)
    rou = liability + idc + prepaid - inc

    r = GaapResult(
        skill=f"{SKILL}.initial_measurement",
        value={"lease_liability": liability, "rou_asset": rou},
        inputs={"payment": terms.payment, "periods": terms.periods,
                "annual_rate": terms.annual_discount_rate,
                "periods_per_year": terms.periods_per_year,
                "payments_in_advance": terms.payments_in_advance,
                "initial_direct_costs": idc, "incentives": inc, "prepaid": prepaid},
        summary=f"Lease liability {liability}; right-of-use asset {rou}.",
    )
    r.assume("Discount rate (annual)", terms.annual_discount_rate, "estimated",
             ASC.LEASE_INITIAL)
    r.assume("Payment timing",
             "beginning of period (annuity due)" if terms.payments_in_advance
             else "end of period (ordinary annuity)",
             "observed", ASC.LEASE_INITIAL)

    r.step("Periodic payment", terms.payment)
    r.step("Number of periods", terms.periods)
    r.step("Periodic discount rate", quantize(rate * 100, 6))
    r.step("PV of lease payments", liability, formula="annuity PV at the periodic rate")
    if terms.residual_value_guarantee:
        r.step("Plus PV of residual value guarantee", rvg_pv)
    r.step("Lease liability", liability)
    if idc:
        r.step("Plus initial direct costs", idc)
    if prepaid:
        r.step("Plus prepaid lease payments", prepaid)
    if inc:
        r.step("Less lease incentives received", -inc)
    r.step("Right-of-use asset", rou)

    r.check("Lease liability is positive", liability.amount > 0, citation=ASC.LEASE_INITIAL)
    r.check("Right-of-use asset is not negative", rou.amount >= 0,
            detail="Incentives exceeding the liability indicate a day-one gain requiring analysis.",
            citation=ASC.LEASE_ROU)
    r.check(
        "Discount rate is the rate implicit in the lease",
        False,
        detail=("Rate supplied is treated as the incremental borrowing rate. "
                "ASC 842-20-30-3 requires the implicit rate when readily determinable."),
        severity=Severity.WARNING,
        citation=ASC.LEASE_INITIAL,
    )
    return r


@subskill(
    SKILL,
    summary="Build the full amortisation schedule for a finance or operating lease.",
    citations=[ASC.LEASE_FINANCE_SUBSEQUENT, ASC.LEASE_OPERATING_SUBSEQUENT],
    triggers=["lease schedule", "amortization schedule", "lease amortisation",
              "roll forward", "lease expense", "interest on lease"],
    inputs={
        "terms": "LeaseTerms describing the arrangement.",
        "classification": "'finance' or 'operating'.",
    },
)
def amortization_schedule(terms: LeaseTerms, classification: str = "operating") -> GaapResult:
    """Period-by-period liability roll-forward and expense recognition.

    The liability half is identical under both models -- effective interest on
    the same PV. What differs is the asset and the expense presentation:

    * finance: interest expense + straight-line ROU amortisation, front-loaded.
    * operating: one straight-line lease cost; ROU amortisation is the plug
      between that flat cost and the declining interest accretion.
    """
    classification = classification.lower().strip()
    if classification not in ("finance", "operating"):
        raise ValueError("classification must be 'finance' or 'operating'")

    cur = terms.payment.currency
    rate = terms.rate
    init = initial_measurement(terms)
    liability: Money = init.value["lease_liability"]
    rou: Money = init.value["rou_asset"]

    payments = [terms.payment] * terms.periods
    liab_rows = effective_interest_schedule(
        liability, payments, rate, due=terms.payments_in_advance
    )

    total_payments = terms.payment * terms.periods
    idc = terms.initial_direct_costs or Money.zero(cur)
    inc = terms.incentives_received or Money.zero(cur)
    total_cost = total_payments + idc - inc
    straight_line_cost = total_cost / terms.periods
    straight_line_amort = rou / terms.periods

    schedule: List[Dict] = []
    rou_balance = rou
    total_interest = Money.zero(cur)
    total_expense = Money.zero(cur)

    for row in liab_rows:
        interest: Money = row["interest"]
        total_interest = total_interest + interest

        if classification == "finance":
            amort = straight_line_amort
            expense = interest + amort
        else:
            expense = straight_line_cost
            amort = expense - interest  # the plug
        rou_balance = rou_balance - amort
        total_expense = total_expense + expense

        schedule.append({
            "period": row["period"],
            "liab open": row["opening"].round(2),
            "interest": interest.round(2),
            "payment": row["payment"].round(2),
            "liab close": row["closing"].round(2),
            "rou amort": amort.round(2),
            "rou close": rou_balance.round(2),
            "expense": expense.round(2),
        })

    r = GaapResult(
        skill=f"{SKILL}.amortization_schedule",
        value={
            "classification": classification,
            "opening_liability": liability,
            "opening_rou": rou,
            "total_interest": total_interest,
            "total_expense": total_expense,
            "periodic_expense": straight_line_cost if classification == "operating" else None,
        },
        inputs=init.inputs | {"classification": classification},
        schedule=schedule,
    )
    r.assumptions.extend(init.assumptions)
    r.step("Opening lease liability", liability)
    r.step("Opening right-of-use asset", rou)
    r.step("Total cash payments", total_payments)
    r.step("Total interest accreted", total_interest)
    r.step("Total expense over the term", total_expense)
    if classification == "operating":
        r.step("Straight-line periodic lease cost", straight_line_cost,
               formula="total lease cost / periods")

    r.summary = (
        f"{classification.capitalize()} lease over {terms.periods} periods: "
        f"liability {liability}, right-of-use asset {rou}, "
        f"total expense {total_expense}."
    )

    final_liab = liab_rows[-1]["closing"]
    r.check(
        "Lease liability amortises to zero at end of term",
        final_liab.is_zero("0.02"),
        detail=f"closing balance {final_liab}",
        citation=ASC.LEASE_FINANCE_SUBSEQUENT,
    )
    r.check(
        "Right-of-use asset amortises to zero at end of term",
        rou_balance.is_zero("0.02"),
        detail=f"closing balance {rou_balance}",
        citation=ASC.LEASE_ROU,
    )
    r.check(
        "Total expense equals cash payments plus initial direct costs less incentives",
        (total_expense - total_cost).is_zero("0.05"),
        detail=f"expense {total_expense} vs cost {total_cost}",
        citation=ASC.LEASE_OPERATING_SUBSEQUENT,
    )
    if classification == "operating":
        distinct_costs = {row["expense"].round(2).amount for row in schedule}
        r.check(
            "Operating lease cost is straight-line",
            len(distinct_costs) <= 2,  # allows a rounding cent in the final period
            detail="A single lease cost is recognised each period (ASC 842-20-25-6).",
            citation=ASC.LEASE_OPERATING_SUBSEQUENT,
        )
    else:
        front = schedule[0]["expense"]
        back = schedule[-1]["expense"]
        r.check(
            "Finance lease expense is front-loaded",
            front >= back,
            detail=f"period 1 expense {front} vs final period {back}",
            severity=Severity.INFO,
            citation=ASC.LEASE_FINANCE_SUBSEQUENT,
        )
    return r
