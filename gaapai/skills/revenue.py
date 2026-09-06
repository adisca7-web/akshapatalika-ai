"""ASC 606 -- Revenue from Contracts with Customers.

The five-step model, decomposed into subskills a caller can invoke individually
or run end to end. The arithmetic is deterministic; the *judgements* (is this
promise distinct, what is the standalone selling price, is a reversal probable)
stay with the preparer and are recorded as assumptions rather than guessed.

That split is the whole design. A language model asked "what is our Q3 revenue"
should not be deciding whether a software licence and its implementation service
are separately identifiable. It should be routing to a function that applies the
allocation mechanics correctly once a human has answered that question, and
saying so in the workpaper.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import D, Money, allocate, money, quantize
from ..core.registry import REGISTRY, subskill
from ..core.timevalue import discount_factor, effective_interest_schedule

SKILL = "revenue"

REGISTRY.declare(
    SKILL,
    title="Revenue from Contracts with Customers",
    topic="606",
    description=(
        "The five-step model: identify the contract, identify performance "
        "obligations, determine the transaction price, allocate it, and "
        "recognise revenue as control transfers."
    ),
)


# ---------------------------------------------------------------------------
# Input types
# ---------------------------------------------------------------------------


@dataclass
class PerformanceObligation:
    """A distinct promise in a contract.

    ``standalone_price`` is the SSP under ASC 606-10-32-33. ``observable``
    records whether it was taken from an actual standalone sale or estimated,
    because estimated SSPs are a disclosed judgement.
    """

    name: str
    standalone_price: Money
    observable: bool = True
    satisfied_over_time: bool = False
    progress: Decimal = Decimal(0)  # 0..1, only meaningful when over time
    method: str = "point in time"

    def __post_init__(self) -> None:
        self.progress = D(self.progress)
        if not (0 <= self.progress <= 1):
            raise ValueError(
                f"progress for '{self.name}' must be between 0 and 1, got {self.progress}"
            )
        if self.standalone_price.amount < 0:
            raise ValueError(f"standalone price for '{self.name}' cannot be negative")


@dataclass
class Outcome:
    """One possible outcome of variable consideration, with its probability."""

    label: str
    amount: Money
    probability: Decimal

    def __post_init__(self) -> None:
        self.probability = D(self.probability)
        if not (0 <= self.probability <= 1):
            raise ValueError(f"probability for '{self.label}' must be in [0, 1]")


# ---------------------------------------------------------------------------
# Step 1 -- contract existence
# ---------------------------------------------------------------------------


@subskill(
    SKILL,
    summary="Test whether an arrangement qualifies as a contract with a customer.",
    citations=[ASC.REV_STEP1_CONTRACT],
    triggers=["is this a contract", "contract exists", "step 1", "collectibility",
              "commercial substance", "does the contract qualify"],
    inputs={
        "approved": "Parties have approved and are committed to perform.",
        "rights_identifiable": "Each party's rights to goods or services are identifiable.",
        "payment_terms_identifiable": "Payment terms are identifiable.",
        "commercial_substance": "The arrangement changes the risk, timing, or amount of future cash flows.",
        "collection_probable": "Collection of substantially all consideration is probable.",
    },
    judgement=True,
)
def contract_exists(
    approved: bool,
    rights_identifiable: bool,
    payment_terms_identifiable: bool,
    commercial_substance: bool,
    collection_probable: bool,
) -> GaapResult:
    """Apply the five ASC 606-10-25-1 criteria. All must hold."""
    criteria = {
        "Parties approved and committed": approved,
        "Rights to goods/services identifiable": rights_identifiable,
        "Payment terms identifiable": payment_terms_identifiable,
        "Commercial substance": commercial_substance,
        "Collection probable": collection_probable,
    }
    qualifies = all(criteria.values())

    r = GaapResult(
        skill=f"{SKILL}.contract_exists",
        value=qualifies,
        inputs={k: v for k, v in criteria.items()},
        summary=(
            "The arrangement meets all five criteria and is accounted for under ASC 606."
            if qualifies else
            "One or more criteria fail. The arrangement is not yet a contract under ASC 606; "
            "consideration received is accounted for under ASC 606-10-25-7 (deposit method) "
            "until the criteria are met or the consideration is nonrefundable and performance "
            "is complete."
        ),
    )
    for label, met in criteria.items():
        r.step(label, "met" if met else "NOT MET")
        r.check(label, met, severity=Severity.ERROR if not met else Severity.INFO,
                citation=ASC.REV_STEP1_CONTRACT)
    return r


# ---------------------------------------------------------------------------
# Step 2 -- distinct performance obligations
# ---------------------------------------------------------------------------


@subskill(
    SKILL,
    summary="Test whether a promised good or service is distinct and therefore a separate performance obligation.",
    citations=[ASC.REV_STEP2_PO, ASC.REV_DISTINCT],
    # "performance obligation" alone is too generic to be a trigger -- it appears
    # in almost every ASC 606 question, including allocation ones. The triggers
    # here are phrases that only a distinctness question would use.
    triggers=["is it distinct", "separate performance obligation", "bundle",
              "step 2", "distinct", "capable of being distinct",
              "separately identifiable"],
    inputs={
        "benefit_on_own": "Customer can benefit from the item alone or with readily available resources.",
        "separately_identifiable": "The promise is separately identifiable from other promises in the contract.",
        "significant_integration": "The entity provides a significant integration service.",
        "significantly_modifies": "The item significantly modifies or customises another promised item.",
        "highly_interdependent": "The items are highly interdependent or interrelated.",
    },
    judgement=True,
)
def is_distinct(
    benefit_on_own: bool,
    separately_identifiable: bool,
    significant_integration: bool = False,
    significantly_modifies: bool = False,
    highly_interdependent: bool = False,
) -> GaapResult:
    """Two-limb distinct test, with the three combining factors that defeat limb two."""
    combining = {
        "Significant integration service": significant_integration,
        "Significantly modifies/customises another promise": significantly_modifies,
        "Highly interdependent or interrelated": highly_interdependent,
    }
    any_combining = any(combining.values())
    limb_two = separately_identifiable and not any_combining
    distinct = benefit_on_own and limb_two

    r = GaapResult(
        skill=f"{SKILL}.is_distinct",
        value=distinct,
        inputs={"benefit_on_own": benefit_on_own,
                "separately_identifiable": separately_identifiable, **combining},
        summary=(
            "Distinct: account for as a separate performance obligation."
            if distinct else
            "Not distinct: combine with other promised goods or services until the "
            "bundle is distinct (ASC 606-10-25-22)."
        ),
    )
    r.step("Limb 1 -- capable of being distinct", "met" if benefit_on_own else "NOT MET",
           note="Customer can benefit on its own or with readily available resources.")
    r.step("Limb 2 -- distinct within the contract", "met" if limb_two else "NOT MET")
    for label, present in combining.items():
        if present:
            r.step(f"  combining factor: {label}", "present",
                   note="Defeats limb 2.")
    r.check("Both limbs of the distinct test met", distinct,
            detail="" if distinct else "Promise must be bundled.",
            severity=Severity.INFO, citation=ASC.REV_DISTINCT)
    return r


# ---------------------------------------------------------------------------
# Step 3 -- transaction price
# ---------------------------------------------------------------------------


@subskill(
    SKILL,
    summary="Estimate variable consideration and apply the constraint.",
    citations=[ASC.REV_VARIABLE, ASC.REV_CONSTRAINT],
    triggers=["variable consideration", "rebate", "refund", "bonus", "penalty",
              "constraint", "expected value", "most likely amount", "earnout"],
    inputs={
        "outcomes": "List of Outcome(label, amount, probability).",
        "method": "'expected_value' for many outcomes, 'most_likely' for a binary outcome.",
        "constraint_pct": "Portion (0..1) retained after the significant-reversal constraint.",
    },
    judgement=True,
)
def variable_consideration(
    outcomes: Sequence[Outcome],
    method: str = "expected_value",
    constraint_pct: Decimal | float | str = 1,
) -> GaapResult:
    """Expected value or most likely amount, then constrained under 606-10-32-11."""
    if not outcomes:
        raise ValueError("at least one outcome is required")

    currency = outcomes[0].amount.currency
    total_p = sum(o.probability for o in outcomes)

    r = GaapResult(
        skill=f"{SKILL}.variable_consideration",
        inputs={
            "method": method,
            "outcomes": [
                {"label": o.label, "amount": o.amount, "probability": o.probability}
                for o in outcomes
            ],
            "constraint_pct": D(constraint_pct),
        },
        value=None,
    )

    r.check(
        "Outcome probabilities sum to 1",
        abs(total_p - 1) <= D("0.0001"),
        detail=f"probabilities total {total_p}",
        severity=Severity.WARNING,
    )

    if method == "expected_value":
        est = Money.zero(currency)
        for o in outcomes:
            contribution = o.amount * o.probability
            est = est + contribution
            r.step(f"{o.label}", contribution,
                   formula=f"{quantize(o.amount.amount, 2):,} x {o.probability}")
        r.step("Expected value", est, formula="sum of probability-weighted outcomes")
        r.assume("Estimation method", "expected value", "entity policy", ASC.REV_VARIABLE)
    elif method == "most_likely":
        best = max(outcomes, key=lambda o: (o.probability, -outcomes.index(o)))
        est = best.amount
        for o in outcomes:
            r.step(f"{o.label}", o.amount, note=f"p = {o.probability}")
        r.step("Most likely amount", est, note=f"outcome '{best.label}'")
        r.assume("Estimation method", "most likely amount", "entity policy", ASC.REV_VARIABLE)
    else:
        raise ValueError(
            f"method must be 'expected_value' or 'most_likely', got '{method}'"
        )

    pct = D(constraint_pct)
    if not (0 <= pct <= 1):
        raise ValueError("constraint_pct must be between 0 and 1")
    constrained = est * pct

    if pct < 1:
        r.step("Constraint applied", constrained,
               formula=f"{quantize(est.amount, 2):,} x {pct}",
               note="Amount for which a significant revenue reversal is not probable.")
        r.assume("Constraint retained portion", pct, "estimated", ASC.REV_CONSTRAINT)

    r.value = constrained
    r.summary = (
        f"Variable consideration included in the transaction price: {constrained}."
        + ("" if pct == 1 else f" Constrained from {est}.")
    )
    r.check("Constrained amount does not exceed the estimate", constrained <= est,
            citation=ASC.REV_CONSTRAINT)
    return r


@subskill(
    SKILL,
    summary="Adjust the transaction price for a significant financing component.",
    citations=[ASC.REV_FINANCING],
    triggers=["significant financing", "financing component", "deferred payment",
              "advance payment", "time value of money", "imputed interest"],
    inputs={
        "stated_amount": "Contractual consideration.",
        "periods": "Number of periods between payment and transfer of control.",
        "discount_rate": "Rate reflecting a separate financing transaction with the customer.",
        "customer_pays_in_advance": "True when the customer pays before the entity performs.",
    },
)
def significant_financing_component(
    stated_amount: Money,
    periods: int,
    discount_rate: Decimal | float | str,
    customer_pays_in_advance: bool = False,
) -> GaapResult:
    """Restate consideration to the cash selling price and split out interest.

    Practical expedient (606-10-32-18): if the gap between transfer and payment
    is one year or less, no adjustment is required. That is flagged, not
    silently applied, because it is a policy election.
    """
    rate = D(discount_rate)
    r = GaapResult(
        skill=f"{SKILL}.significant_financing_component",
        inputs={"stated_amount": stated_amount, "periods": periods,
                "discount_rate": rate, "customer_pays_in_advance": customer_pays_in_advance},
        value=None,
    )
    r.assume("Discount rate", rate, "estimated", ASC.REV_FINANCING)
    r.step("Stated consideration", stated_amount)

    if customer_pays_in_advance:
        # Entity holds customer cash: accrete interest expense up to transfer.
        revenue = stated_amount * ((Decimal(1) + rate) ** periods)
        interest = revenue - stated_amount
        direction = "interest expense (entity is financed by the customer)"
    else:
        factor = discount_factor(rate, periods)
        revenue = stated_amount * factor
        interest = stated_amount - revenue
        direction = "interest income (entity finances the customer)"

    r.step("Periods", periods)
    r.step("Revenue at cash selling price", revenue,
           formula=f"stated x (1+{rate})^{'+' if customer_pays_in_advance else '-'}{periods}")
    r.step("Financing component", interest, note=direction)

    r.value = {"revenue": revenue, "financing": interest}
    r.summary = (
        f"Revenue recognised at the cash selling price of {revenue}; "
        f"{interest} is presented separately as {direction.split(' (')[0]}."
    )
    r.check(
        "Term exceeds the one-year practical expedient",
        periods > 1,
        detail=("Term is one period or less; the entity may elect the 606-10-32-18 "
                "expedient and not adjust for financing."),
        severity=Severity.WARNING,
        citation=ASC.REV_FINANCING,
    )
    r.check("Revenue plus financing ties to stated consideration",
            (revenue + interest if not customer_pays_in_advance else revenue - interest)
            .round(2) == stated_amount.round(2),
            citation=ASC.REV_FINANCING)
    return r


# ---------------------------------------------------------------------------
# Step 4 -- allocation
# ---------------------------------------------------------------------------


@subskill(
    SKILL,
    summary="Allocate the transaction price across performance obligations by relative standalone selling price.",
    citations=[ASC.REV_STEP4_ALLOCATE, ASC.REV_SSP_ESTIMATE, ASC.REV_DISCOUNT_ALLOC],
    triggers=["allocate", "allocation", "transaction price", "standalone selling price",
              "ssp", "relative selling price", "step 4", "split the price",
              "contract price", "how much of the", "goes to each",
              "each performance obligation", "across performance obligations"],
    inputs={
        "transaction_price": "Total consideration determined in step 3.",
        "obligations": "List of PerformanceObligation with standalone prices.",
        "discount_to": "Optional names of obligations the discount is allocated entirely to.",
    },
)
def allocate_transaction_price(
    transaction_price: Money,
    obligations: Sequence[PerformanceObligation],
    discount_to: Optional[Sequence[str]] = None,
) -> GaapResult:
    """Relative-SSP allocation with exact residual handling.

    Rounding matters here. Proportional shares almost never land on whole cents,
    and ASC 606-10-32-31 requires the *entire* transaction price to be allocated.
    :func:`gaapai.core.money.allocate` uses largest-remainder so the parts always
    sum back to the whole.
    """
    if not obligations:
        raise ValueError("at least one performance obligation is required")

    ssp_total = Money.zero(transaction_price.currency)
    for po in obligations:
        ssp_total = ssp_total + po.standalone_price

    r = GaapResult(
        skill=f"{SKILL}.allocate_transaction_price",
        inputs={
            "transaction_price": transaction_price,
            "obligations": [
                {"name": p.name, "ssp": p.standalone_price, "observable": p.observable}
                for p in obligations
            ],
            "discount_to": list(discount_to or []),
        },
        value=None,
    )

    r.step("Transaction price", transaction_price)
    r.step("Sum of standalone selling prices", ssp_total)
    discount = ssp_total - transaction_price
    r.step("Aggregate discount" if discount.amount > 0 else "Aggregate premium",
           abs(discount), formula="sum(SSP) - transaction price")

    for po in obligations:
        if not po.observable:
            r.assume(f"SSP -- {po.name}", po.standalone_price, "estimated",
                     ASC.REV_SSP_ESTIMATE)

    targets = set(discount_to or [])
    if targets:
        unknown = targets - {p.name for p in obligations}
        if unknown:
            raise ValueError(f"discount_to names unknown obligations: {sorted(unknown)}")
        # Discount allocated entirely to specified obligations (606-10-32-37).
        r.assume("Discount allocation", f"entirely to {sorted(targets)}",
                 "observed", ASC.REV_DISCOUNT_ALLOC)
        untargeted = [p for p in obligations if p.name not in targets]
        targeted = [p for p in obligations if p.name in targets]
        untargeted_total = Money.zero(transaction_price.currency)
        for p in untargeted:
            untargeted_total = untargeted_total + p.standalone_price
        remaining = transaction_price - untargeted_total
        targeted_shares = allocate(remaining, [p.standalone_price.amount for p in targeted])
        amounts: Dict[str, Money] = {p.name: p.standalone_price for p in untargeted}
        amounts.update({p.name: s for p, s in zip(targeted, targeted_shares)})
        allocated = [amounts[p.name] for p in obligations]
    else:
        r.assume("Discount allocation", "proportionate to all obligations",
                 "default", ASC.REV_DISCOUNT_ALLOC)
        allocated = allocate(transaction_price, [p.standalone_price.amount for p in obligations])

    schedule = []
    for po, amt in zip(obligations, allocated):
        pct = (po.standalone_price.amount / ssp_total.amount) if ssp_total.amount else Decimal(0)
        schedule.append({
            "obligation": po.name,
            "ssp": po.standalone_price,
            "ssp %": quantize(pct * 100, 2),
            "allocated": amt,
            "basis": "observable" if po.observable else "estimated",
        })
    r.schedule = schedule

    total_allocated = Money.zero(transaction_price.currency)
    for a in allocated:
        total_allocated = total_allocated + a

    r.value = {po.name: amt for po, amt in zip(obligations, allocated)}
    r.summary = (
        f"{transaction_price} allocated across {len(obligations)} performance "
        f"obligations on a relative standalone selling price basis."
    )
    r.check(
        "Allocated amounts sum to the transaction price",
        total_allocated == transaction_price,
        detail=f"allocated {total_allocated} vs price {transaction_price}",
        citation=ASC.REV_STEP4_ALLOCATE,
    )
    r.check(
        "All standalone selling prices are observable",
        all(p.observable for p in obligations),
        detail="Estimated SSPs are a significant judgement requiring disclosure.",
        severity=Severity.WARNING,
        citation=ASC.REV_SSP_ESTIMATE,
    )
    return r


# ---------------------------------------------------------------------------
# Step 5 -- recognition
# ---------------------------------------------------------------------------


@subskill(
    SKILL,
    summary="Determine whether a performance obligation is satisfied over time or at a point in time.",
    citations=[ASC.REV_OVER_TIME, ASC.REV_STEP5_RECOGNIZE],
    triggers=["over time", "point in time", "when to recognize", "control transfer",
              "step 5", "recognition timing", "percentage of completion"],
    inputs={
        "simultaneous_benefit": "Customer simultaneously receives and consumes the benefit.",
        "customer_controls_asset": "The entity's performance creates or enhances an asset the customer controls.",
        "no_alternative_use": "The asset has no alternative use to the entity.",
        "enforceable_right_to_payment": "The entity has an enforceable right to payment for performance to date.",
    },
    judgement=True,
)
def recognition_timing(
    simultaneous_benefit: bool,
    customer_controls_asset: bool,
    no_alternative_use: bool,
    enforceable_right_to_payment: bool,
) -> GaapResult:
    """Apply the three over-time criteria; failing all three means point in time."""
    third = no_alternative_use and enforceable_right_to_payment
    criteria = {
        "(a) Customer simultaneously receives and consumes": simultaneous_benefit,
        "(b) Performance creates an asset the customer controls": customer_controls_asset,
        "(c) No alternative use AND enforceable right to payment": third,
    }
    over_time = any(criteria.values())

    r = GaapResult(
        skill=f"{SKILL}.recognition_timing",
        value="over time" if over_time else "point in time",
        inputs={"simultaneous_benefit": simultaneous_benefit,
                "customer_controls_asset": customer_controls_asset,
                "no_alternative_use": no_alternative_use,
                "enforceable_right_to_payment": enforceable_right_to_payment},
        summary=(
            "Revenue is recognised over time; select a single method of measuring "
            "progress under ASC 606-10-25-31."
            if over_time else
            "No over-time criterion is met. Revenue is recognised at the point in "
            "time control transfers, per the ASC 606-10-25-30 indicators."
        ),
    )
    for label, met in criteria.items():
        r.step(label, "met" if met else "not met")
    if not third and no_alternative_use != enforceable_right_to_payment:
        r.step("  note", "criterion (c) requires BOTH conditions",
               note="No alternative use alone is insufficient.")
    r.check("At least one over-time criterion met", over_time,
            severity=Severity.INFO, citation=ASC.REV_OVER_TIME)
    return r


@subskill(
    SKILL,
    summary="Measure progress and revenue for an over-time obligation using the cost-to-cost input method.",
    citations=[ASC.REV_PROGRESS, ASC.REV_STEP5_RECOGNIZE],
    triggers=["cost to cost", "percentage of completion", "progress", "input method",
              "costs incurred", "revenue to date", "poc"],
    inputs={
        "transaction_price": "Amount allocated to this performance obligation.",
        "costs_incurred_to_date": "Cumulative costs incurred that depict progress.",
        "estimated_total_costs": "Current estimate of total costs to satisfy the obligation.",
        "revenue_recognized_previously": "Cumulative revenue recognised in prior periods.",
        "uninstalled_materials": "Costs that do not depict progress and are excluded.",
    },
)
def cost_to_cost_progress(
    transaction_price: Money,
    costs_incurred_to_date: Money,
    estimated_total_costs: Money,
    revenue_recognized_previously: Optional[Money] = None,
    uninstalled_materials: Optional[Money] = None,
) -> GaapResult:
    """Cost-to-cost progress, current-period revenue, and loss recognition.

    Uninstalled materials are stripped from both numerator and denominator:
    ASC 606-10-55-21 says costs that are not proportionate to progress do not
    depict transfer of control, and leaving them in overstates early revenue on
    equipment-heavy contracts.
    """
    cur = transaction_price.currency
    prior = revenue_recognized_previously or Money.zero(cur)
    excluded = uninstalled_materials or Money.zero(cur)

    if estimated_total_costs.amount <= 0:
        raise ValueError("estimated total costs must be positive")

    r = GaapResult(
        skill=f"{SKILL}.cost_to_cost_progress",
        inputs={"transaction_price": transaction_price,
                "costs_incurred_to_date": costs_incurred_to_date,
                "estimated_total_costs": estimated_total_costs,
                "revenue_recognized_previously": prior,
                "uninstalled_materials": excluded},
        value=None,
    )

    num = costs_incurred_to_date - excluded
    den = estimated_total_costs - excluded
    if den.amount <= 0:
        raise ValueError("estimated total costs net of excluded items must be positive")

    pct = num / den
    pct = min(pct, Decimal(1))

    r.step("Costs incurred to date", costs_incurred_to_date)
    if excluded:
        r.step("Less uninstalled materials", -excluded,
               note="Excluded from the measure of progress (ASC 606-10-55-21).")
    r.step("Costs used to measure progress", num)
    r.step("Estimated total costs (net)", den)
    r.step("Progress", quantize(pct * 100, 4), formula="costs to date / estimated total costs")

    cumulative = transaction_price * pct
    if excluded:
        # Uninstalled materials are recognised at zero margin.
        cumulative = cumulative + excluded
        r.step("Plus uninstalled materials at zero margin", excluded,
               note="Revenue equals cost; no margin until installed.")
    current = cumulative - prior

    r.step("Cumulative revenue", cumulative, formula="transaction price x progress")
    r.step("Less recognised previously", -prior)
    r.step("Revenue this period", current)

    expected_total_margin = transaction_price - estimated_total_costs
    r.value = {
        "progress": pct,
        "cumulative_revenue": cumulative,
        "current_period_revenue": current,
    }
    r.summary = (
        f"Progress is {quantize(pct * 100, 2)}%; cumulative revenue {cumulative}, "
        f"of which {current} arises this period."
    )

    r.check(
        "Progress does not exceed 100%",
        num <= den,
        detail=f"costs to date {num} vs estimated total {den}; revise the estimate",
        citation=ASC.REV_PROGRESS,
    )
    r.check(
        "Contract is not in a loss position",
        expected_total_margin.amount >= 0,
        detail=(f"Expected loss of {abs(expected_total_margin)} must be recognised "
                "immediately and in full (ASC 605-35-25-46 / ASC 606 loss provisions)."),
        severity=Severity.WARNING,
    )
    r.check(
        "Current period revenue is not negative",
        current.amount >= 0,
        detail="A negative amount indicates a cumulative catch-up from a downward estimate revision.",
        severity=Severity.WARNING,
        citation=ASC.REV_PROGRESS,
    )
    return r


@subskill(
    SKILL,
    summary="Classify the net contract position as a contract asset or contract liability.",
    citations=[ASC.REV_CONTRACT_BALANCES],
    triggers=["contract asset", "contract liability", "deferred revenue",
              "unbilled receivable", "contract balance"],
    inputs={
        "revenue_recognized": "Cumulative revenue recognised to date.",
        "amounts_billed": "Cumulative amounts billed to the customer.",
        "unconditional_right": "True when only the passage of time is required for payment.",
    },
)
def contract_balance(
    revenue_recognized: Money,
    amounts_billed: Money,
    unconditional_right: bool = False,
) -> GaapResult:
    """Performance ahead of billing is an asset; billing ahead of performance is a liability."""
    net = revenue_recognized - amounts_billed
    if net.amount > 0:
        label = "receivable" if unconditional_right else "contract asset"
        detail = (
            "An unconditional right to consideration exists, so the balance is a "
            "receivable rather than a contract asset."
            if unconditional_right else
            "Right to consideration is conditional on something other than the "
            "passage of time."
        )
    elif net.amount < 0:
        label = "contract liability"
        detail = "The entity has been paid or has an unconditional right to payment before performing."
    else:
        label = "no net position"
        detail = "Performance and billing are level."

    r = GaapResult(
        skill=f"{SKILL}.contract_balance",
        value={"classification": label, "amount": abs(net)},
        inputs={"revenue_recognized": revenue_recognized,
                "amounts_billed": amounts_billed,
                "unconditional_right": unconditional_right},
        summary=f"Net position of {abs(net)} presented as a {label}. {detail}",
    )
    r.step("Cumulative revenue recognised", revenue_recognized)
    r.step("Cumulative amounts billed", amounts_billed)
    r.step("Net contract position", net, formula="revenue - billings")
    r.check("Contract balances presented net by contract", True,
            detail="ASC 606-10-45-1 requires a single net position per contract.",
            severity=Severity.INFO, citation=ASC.REV_CONTRACT_BALANCES)
    return r


@subskill(
    SKILL,
    summary="Determine principal versus agent and whether revenue is reported gross or net.",
    citations=[ASC.REV_PRINCIPAL_AGENT],
    triggers=["principal", "agent", "gross", "net", "gross or net", "reseller",
              "marketplace", "pass through"],
    inputs={
        "primarily_responsible": "The entity is primarily responsible for fulfilling the promise.",
        "inventory_risk": "The entity bears inventory risk before or after transfer.",
        "pricing_discretion": "The entity has discretion in establishing the price.",
        "gross_amount": "Amount billed to the customer.",
        "amount_paid_to_supplier": "Amount owed to the third-party supplier.",
    },
    judgement=True,
)
def principal_or_agent(
    primarily_responsible: bool,
    inventory_risk: bool,
    pricing_discretion: bool,
    gross_amount: Optional[Money] = None,
    amount_paid_to_supplier: Optional[Money] = None,
) -> GaapResult:
    """Weigh the three control indicators; two or more point to principal."""
    indicators = {
        "Primarily responsible for fulfilment": primarily_responsible,
        "Bears inventory risk": inventory_risk,
        "Discretion in establishing price": pricing_discretion,
    }
    score = sum(1 for v in indicators.values() if v)
    is_principal = score >= 2

    r = GaapResult(
        skill=f"{SKILL}.principal_or_agent",
        value="principal" if is_principal else "agent",
        inputs={**indicators},
        summary=(
            f"{score} of 3 control indicators present -- the entity acts as "
            f"{'principal and reports revenue gross' if is_principal else 'agent and reports the net fee as revenue'}."
        ),
    )
    for label, present in indicators.items():
        r.step(label, "yes" if present else "no")
    r.step("Indicators supporting principal", f"{score} of 3")

    if gross_amount is not None and amount_paid_to_supplier is not None:
        net = gross_amount - amount_paid_to_supplier
        reported = gross_amount if is_principal else net
        r.step("Gross amount billed", gross_amount)
        r.step("Paid to supplier", amount_paid_to_supplier)
        r.step("Revenue reported", reported,
               note="gross" if is_principal else "net commission")
        r.value = {"role": "principal" if is_principal else "agent", "revenue": reported}

    r.check(
        "Indicators are not evenly split",
        score != 2 or is_principal,
        detail="Indicators are supportive, not a checklist; document the control analysis.",
        severity=Severity.WARNING,
        citation=ASC.REV_PRINCIPAL_AGENT,
    )
    return r


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


@subskill(
    SKILL,
    summary="Run the complete five-step model and produce a revenue schedule by performance obligation.",
    citations=[ASC.REV_STEP1_CONTRACT, ASC.REV_STEP2_PO, ASC.REV_STEP3_PRICE,
               ASC.REV_STEP4_ALLOCATE, ASC.REV_STEP5_RECOGNIZE],
    triggers=["five step", "5 step", "recognize revenue", "revenue for the contract",
              "how much revenue", "revenue recognition", "asc 606"],
    inputs={
        "transaction_price": "Total consideration, after variable consideration and financing adjustments.",
        "obligations": "List of PerformanceObligation, each with SSP and satisfaction status.",
        "discount_to": "Optional obligations receiving the entire discount.",
    },
)
def five_step_revenue(
    transaction_price: Money,
    obligations: Sequence[PerformanceObligation],
    discount_to: Optional[Sequence[str]] = None,
) -> GaapResult:
    """Allocate the price, then recognise each obligation according to its progress.

    Composes the individual subskills rather than reimplementing them, so the
    end-to-end answer and the step-by-step answers cannot disagree.
    """
    alloc = allocate_transaction_price(transaction_price, obligations, discount_to)
    allocated: Dict[str, Money] = alloc.value

    r = GaapResult(
        skill=f"{SKILL}.five_step_revenue",
        inputs=alloc.inputs,
        value=None,
    )
    r.assumptions.extend(alloc.assumptions)
    r.checks.extend(alloc.checks)
    r.step("Transaction price", transaction_price)

    recognised = Money.zero(transaction_price.currency)
    deferred = Money.zero(transaction_price.currency)
    schedule = []

    for po in obligations:
        amt = allocated[po.name]
        if po.satisfied_over_time:
            earned = amt * po.progress
            basis = f"over time, {quantize(po.progress * 100, 2)}% complete ({po.method})"
        else:
            earned = amt if po.progress >= 1 else Money.zero(transaction_price.currency)
            basis = "point in time -- " + ("control transferred" if po.progress >= 1
                                           else "control not yet transferred")
        defer = amt - earned
        recognised = recognised + earned
        deferred = deferred + defer
        schedule.append({
            "obligation": po.name,
            "allocated": amt,
            "recognised": earned,
            "deferred": defer,
            "basis": basis,
        })

    r.schedule = schedule
    r.step("Revenue recognised", recognised)
    r.step("Contract liability (deferred)", deferred)

    r.value = {"recognized": recognised, "deferred": deferred, "by_obligation": schedule}
    r.summary = (
        f"Of the {transaction_price} transaction price, {recognised} is recognised "
        f"as revenue and {deferred} is deferred as a contract liability."
    )
    r.check(
        "Recognised plus deferred ties to the transaction price",
        (recognised + deferred) == transaction_price,
        detail=f"{recognised} + {deferred} vs {transaction_price}",
        citation=ASC.REV_STEP4_ALLOCATE,
    )
    return r
