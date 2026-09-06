"""ASC 330 -- Inventory.

Cost flow assumptions and the lower-of-cost measurement rules. The measurement
ceiling depends on the cost flow method, which is a genuine trap: FIFO and
average cost use lower of cost and *net realisable value* (ASU 2015-11), while
LIFO and retail still use the older lower of cost or *market* with its ceiling
and floor. Applying NRV to a LIFO pool is a real misstatement, so the method
drives the rule here rather than the caller choosing.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from ..core.asc import ASC
from ..core.evidence import GaapResult, Severity
from ..core.money import D, Money, quantize
from ..core.registry import REGISTRY, subskill

SKILL = "inventory"

REGISTRY.declare(
    SKILL,
    title="Inventory",
    topic="330",
    description=(
        "Cost flow assumptions (FIFO, LIFO, weighted and moving average) and "
        "subsequent measurement at the lower of cost and net realisable value, "
        "or lower of cost or market for LIFO and retail."
    ),
)


@dataclass
class Layer:
    """A purchase layer: units acquired at a unit cost."""

    units: Decimal
    unit_cost: Money
    label: str = ""

    def __post_init__(self) -> None:
        self.units = D(self.units)
        if self.units < 0:
            raise ValueError("layer units cannot be negative")

    @property
    def total(self) -> Money:
        return self.unit_cost * self.units


@subskill(
    SKILL,
    summary="Compute cost of goods sold and ending inventory under a chosen cost flow assumption.",
    citations=[ASC.INVENTORY_COST, ASC.INVENTORY_FLOW],
    triggers=["fifo", "lifo", "weighted average", "cost flow", "cogs",
              "cost of goods sold", "ending inventory", "inventory valuation"],
    inputs={
        "opening": "Opening inventory Layer, or None.",
        "purchases": "Purchase layers in chronological order.",
        "units_sold": "Units sold during the period.",
        "method": "'fifo', 'lifo', or 'weighted_average'.",
    },
)
def cost_flow(
    opening: Optional[Layer],
    purchases: Sequence[Layer],
    units_sold: Decimal | int | str,
    method: str = "fifo",
) -> GaapResult:
    """Consume layers in the order the method prescribes and split cost between COGS and ending inventory."""
    method = method.lower().strip()
    if method not in ("fifo", "lifo", "weighted_average"):
        raise ValueError("method must be 'fifo', 'lifo', or 'weighted_average'")

    layers: List[Layer] = ([opening] if opening else []) + list(purchases)
    if not layers:
        raise ValueError("no inventory layers supplied")

    cur = layers[0].unit_cost.currency
    sold = D(units_sold)
    available_units = sum(l.units for l in layers)
    goods_available = Money.zero(cur)
    for l in layers:
        goods_available = goods_available + l.total

    if sold > available_units:
        raise ValueError(
            f"units sold ({sold}) exceeds units available ({available_units})"
        )

    r = GaapResult(
        skill=f"{SKILL}.cost_flow",
        inputs={
            "method": method,
            "units_sold": sold,
            "layers": [
                {"label": l.label or f"layer {i}", "units": l.units,
                 "unit_cost": l.unit_cost}
                for i, l in enumerate(layers)
            ],
        },
        value=None,
    )
    r.assume("Cost flow assumption", method, "entity policy", ASC.INVENTORY_FLOW)

    consumed: List[Dict] = []

    if method == "weighted_average":
        avg = goods_available / available_units
        cogs = avg * sold
        ending = goods_available - cogs
        ending_units = available_units - sold
        r.step("Goods available for sale", goods_available)
        r.step("Units available", available_units)
        r.step("Weighted average unit cost", avg,
               formula="goods available for sale / units available")
        r.step("Units sold", sold)
        r.step("Cost of goods sold", cogs, formula="average unit cost x units sold")
        r.step("Ending inventory", ending)
        consumed.append({
            "source": "weighted average pool",
            "units": sold,
            "unit cost": avg,
            "cost": cogs,
        })
    else:
        order = list(range(len(layers))) if method == "fifo" else list(reversed(range(len(layers))))
        remaining = sold
        cogs = Money.zero(cur)
        left = {i: layers[i].units for i in range(len(layers))}

        for i in order:
            if remaining <= 0:
                break
            take = min(left[i], remaining)
            if take <= 0:
                continue
            cost = layers[i].unit_cost * take
            cogs = cogs + cost
            left[i] -= take
            remaining -= take
            consumed.append({
                "source": layers[i].label or f"layer {i + 1}",
                "units": take,
                "unit cost": layers[i].unit_cost,
                "cost": cost,
            })

        ending = goods_available - cogs
        ending_units = available_units - sold
        r.step("Goods available for sale", goods_available)
        r.step("Units sold", sold)
        r.step(f"Cost of goods sold ({method.upper()})", cogs)
        r.step("Ending inventory", ending)

    r.schedule = consumed
    r.value = {
        "cogs": cogs,
        "ending_inventory": ending,
        "ending_units": ending_units,
        "goods_available": goods_available,
    }
    r.summary = (
        f"Under {method.replace('_', ' ').upper()}, cost of goods sold is {cogs} "
        f"and ending inventory is {ending} ({ending_units} units)."
    )
    r.check(
        "COGS plus ending inventory ties to goods available for sale",
        (cogs + ending) == goods_available,
        detail=f"{cogs} + {ending} vs {goods_available}",
        citation=ASC.INVENTORY_COST,
    )
    r.check(
        "Ending inventory is not negative",
        ending.amount >= 0,
        citation=ASC.INVENTORY_COST,
    )
    if method == "lifo":
        r.check(
            "LIFO conformity and reserve disclosure considered",
            True,
            detail=("LIFO used for tax must also be used for financial reporting. "
                    "Disclose the LIFO reserve to permit comparison with FIFO."),
            severity=Severity.INFO,
            citation=ASC.INVENTORY_FLOW,
        )
    return r


@subskill(
    SKILL,
    summary="Measure inventory at the lower of cost and net realisable value, or lower of cost or market for LIFO and retail.",
    citations=[ASC.INVENTORY_LCNRV, ASC.INVENTORY_LCM_LIFO, ASC.INVENTORY_NO_REVERSAL],
    triggers=["lower of cost", "lcnrv", "net realizable value", "nrv", "lcm",
              "market ceiling", "market floor", "write down", "write-down",
              "inventory impairment", "obsolete inventory"],
    inputs={
        "cost": "Carrying cost of the inventory item or pool.",
        "selling_price": "Estimated selling price in the ordinary course of business.",
        "cost_to_complete_and_sell": "Reasonably predictable costs of completion and disposal.",
        "method": "Cost flow method in use -- drives which measurement rule applies.",
        "replacement_cost": "Current replacement cost; required only for LIFO/retail.",
        "normal_profit_margin": "Normal profit margin; required only for LIFO/retail.",
    },
)
def lower_of_cost(
    cost: Money,
    selling_price: Money,
    cost_to_complete_and_sell: Money,
    method: str = "fifo",
    replacement_cost: Optional[Money] = None,
    normal_profit_margin: Optional[Money] = None,
) -> GaapResult:
    """Apply LCNRV or LCM depending on the cost flow method."""
    method = method.lower().strip()
    nrv = selling_price - cost_to_complete_and_sell
    uses_lcm = method in ("lifo", "retail")

    r = GaapResult(
        skill=f"{SKILL}.lower_of_cost",
        inputs={"cost": cost, "selling_price": selling_price,
                "cost_to_complete_and_sell": cost_to_complete_and_sell,
                "method": method, "replacement_cost": replacement_cost,
                "normal_profit_margin": normal_profit_margin},
        value=None,
    )
    r.step("Carrying cost", cost)
    r.step("Estimated selling price", selling_price)
    r.step("Less costs to complete and sell", -cost_to_complete_and_sell)
    r.step("Net realisable value (ceiling)", nrv, formula="selling price - completion and disposal costs")

    if uses_lcm:
        if replacement_cost is None or normal_profit_margin is None:
            raise ValueError(
                "LIFO and retail inventories are measured at lower of cost or market, "
                "which requires replacement_cost and normal_profit_margin"
            )
        floor = nrv - normal_profit_margin
        r.step("Normal profit margin", normal_profit_margin)
        r.step("NRV less normal profit (floor)", floor)
        r.step("Current replacement cost", replacement_cost)
        # Market is replacement cost bounded by ceiling and floor.
        market = replacement_cost
        bound = "replacement cost"
        if market > nrv:
            market, bound = nrv, "ceiling (NRV)"
        elif market < floor:
            market, bound = floor, "floor (NRV less normal profit)"
        r.step("Designated market", market, note=f"bounded to the {bound}")
        comparison, rule = market, "lower of cost or market"
        r.assume("Measurement rule", "lower of cost or market", "observed",
                 ASC.INVENTORY_LCM_LIFO)
    else:
        comparison, rule = nrv, "lower of cost and net realisable value"
        r.assume("Measurement rule", "lower of cost and net realisable value",
                 "observed", ASC.INVENTORY_LCNRV)

    carrying = min(cost, comparison, key=lambda m: m.amount)
    writedown = cost - carrying

    r.step("Reported inventory", carrying, formula=f"min(cost, {rule.split(' ')[-1]})")
    if writedown:
        r.step("Write-down charged to income", writedown)

    r.value = {"carrying_amount": carrying, "writedown": writedown,
               "nrv": nrv, "rule": rule}
    r.summary = (
        f"Inventory is carried at {carrying} under the {rule} rule."
        + (f" A write-down of {writedown} is charged to cost of goods sold."
           if writedown else " No write-down is required.")
    )
    r.check("Reported amount does not exceed cost", carrying <= cost,
            citation=ASC.INVENTORY_LCNRV)
    r.check(
        "Write-down establishes a new cost basis",
        True,
        detail=("A write-down is not reversed if value later recovers "
                "(ASC 330-10-35-14). This differs from IAS 2, which requires reversal."),
        severity=Severity.INFO,
        citation=ASC.INVENTORY_NO_REVERSAL,
    )
    r.check(
        "Net realisable value is positive",
        nrv.amount > 0,
        detail="Disposal costs exceed the selling price; the item may warrant scrapping.",
        severity=Severity.WARNING,
        citation=ASC.INVENTORY_LCNRV,
    )
    return r
