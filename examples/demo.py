"""End-to-end demonstration of the GAAP layer.

Run: python examples/demo.py

Shows the path a financial question actually takes:
    question -> deterministic route -> vetted computation -> workpaper -> diagram
and what happens when the data is bad.
"""

from __future__ import annotations

from decimal import Decimal

import gaapai
from gaapai import money
from gaapai.adapters import toolblock as bridge
from gaapai.diagrams import mermaid
from gaapai.router import Router, route
from gaapai.skills import leases, ppe, revenue, statements

RULE = "=" * 78


def banner(title: str) -> None:
    print()
    print(RULE)
    print(title)
    print(RULE)


def demo_routing() -> None:
    banner("1. ROUTING -- a question reaches one vetted function, deterministically")
    for q in [
        "How much of the $900 contract price goes to each performance obligation?",
        "Is our warehouse lease finance or operating?",
        "How do we amortise film costs?",
    ]:
        r = route(q)
        print()
        print(f"  Q: {q}")
        print(f"     -> {r.best.qualified_name if r.best else '(no computation)'}"
              f"   confident={r.confident}")
        if r.references:
            print(f"     -> reference: {r.references[0]['file']}")


def demo_revenue_allocation():
    banner("2. ASC 606 -- allocation, with the workpaper that makes it reviewable")
    obligations = [
        revenue.PerformanceObligation("Software licence", money("600000"),
                                      observable=True, progress=Decimal(1)),
        revenue.PerformanceObligation("Implementation", money("250000"),
                                      observable=False, satisfied_over_time=True,
                                      progress=Decimal("0.40"),
                                      method="cost-to-cost"),
        revenue.PerformanceObligation("Support (12 mo)", money("150000"),
                                      observable=True, satisfied_over_time=True,
                                      progress=Decimal("0.25")),
    ]
    result = revenue.five_step_revenue(money("900000"), obligations)
    print(result.workpaper())
    return result


def demo_lease():
    banner("3. ASC 842 -- classification and schedule, checked end to end")
    terms = leases.LeaseTerms(
        payment=money("25000"), periods=36,
        annual_discount_rate=Decimal("0.055"), periods_per_year=12,
        payments_in_advance=True,
        economic_life_periods=60, fair_value=money("900000"),
        initial_direct_costs=money("12000"),
    )
    classification = leases.classify_lease(terms)
    print(classification.workpaper())

    schedule = leases.amortization_schedule(terms, classification.value)
    print()
    print(f"  Opening liability : {schedule.value['opening_liability']}")
    print(f"  Opening ROU asset : {schedule.value['opening_rou']}")
    print(f"  Total interest    : {schedule.value['total_interest']}")
    print(f"  Total expense     : {schedule.value['total_expense']}")
    print(f"  Closing liability : {schedule.schedule[-1]['liab close']}")
    print(f"  Checks passed     : {schedule.ok}")
    return classification


def demo_bad_data():
    banner("4. BAD DATA -- the layer refuses rather than answering confidently")
    A = statements.Account
    accounts = [
        A("Cash", statements.CURRENT_ASSET, money("70000")),
        A("Accounts payable", statements.CURRENT_LIABILITY, money("35000")),
        A("Common stock", statements.EQUITY, money("20000")),
        # deliberately out of balance by 15,000
    ]
    tb = statements.verify_trial_balance(accounts)
    print(tb.workpaper())
    print()
    print("  An LLM asked 'what are total assets?' would answer 70,000 here,")
    print("  fluently and wrongly. The kernel reports the exception instead.")


def demo_impairment():
    banner("5. ASC 360 -- the undiscounted screen, where models usually slip")
    r = ppe.impairment_test(
        carrying_amount=money("5000000"),
        undiscounted_cash_flows=money("5200000"),
        fair_value=money("4100000"),
    )
    print(r.workpaper())
    print()
    print("  Fair value is 900,000 below carrying amount, yet NO loss is")
    print("  recognised: step 1 passed on UNDISCOUNTED flows (360-10-35-17).")
    return r


def demo_diagrams(alloc, lease_class, impair):
    banner("6. DIAGRAMS -- generated from the results, so they cannot disagree")
    print()
    print("--- ASC 842 classification (branch taken is highlighted) ---")
    print(mermaid.lease_classification_diagram(lease_class))
    print()
    print("--- ASC 360 impairment ---")
    print(mermaid.impairment_diagram(impair))


def demo_reference():
    banner("7. REFERENCE PACK -- what the standard requires, from Wiley GAAP 2020")
    router = Router()
    if router.pack_path is None:
        print("  reference pack not found")
        return
    print(f"  pack: {router.pack_path}")
    print(f"  {len(router.chapters())} ASC topic chapters, "
          f"{len(router.industries())} industry regimes")
    print()
    print("  Industries covered:")
    for ind in router.industries():
        print(f"    ASC {ind['primary']:<5} {ind['title']}")


def demo_toolblock():
    banner("8. TOOL BLOCK -- what a code-generating model is shown")
    block = bridge.tool_descriptions(["revenue"])
    print()
    print("  Tool block injected into the prompt (revenue skill only):")
    print()
    for line in block.splitlines()[:16]:
        print("    " + line)
    print("    ...")


def main() -> int:
    print(RULE)
    print("gaapai -- deterministic GAAP layer   v" + gaapai.__version__)
    print(f"{len(gaapai.REGISTRY.skills)} skills, "
          f"{len(gaapai.REGISTRY.subskills())} subskills, "
          f"{len(gaapai.coverage())} ASC paragraphs implemented")
    print(RULE)

    demo_routing()
    alloc = demo_revenue_allocation()
    lease_class = demo_lease()
    demo_bad_data()
    impair = demo_impairment()
    demo_diagrams(alloc, lease_class, impair)
    demo_reference()
    demo_toolblock()

    banner("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
