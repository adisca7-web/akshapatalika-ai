"""Walk the exact flow for: "find me a trend of revenue for the last 5 years".

Run: python examples/warehouse_question.py

Shows every step, and which system does it. The point of the walkthrough is that
the interesting failure is not in the SQL -- it is in choosing the column and
knowing whether five years of it are comparable.
"""

from __future__ import annotations

from gaapai.adapters import pandasai_bridge as bridge
from gaapai.router import Router, route
from gaapai.semantics import Concept, plan_aggregation

RULE = "=" * 78

# A plausible warehouse fact table for a studio. Every column here exists in
# real film-industry schemas, and three of them are traps.
WAREHOUSE_COLUMNS = [
    "fiscal_year",
    "title_id",
    "territory",
    "market",
    "ultimate_revenue",        # forecast denominator -- NOT revenue
    "theatrical_revenue",
    "home_video_revenue",
    "licensing_revenue",
    "participation_cost",      # cost, not contra-revenue
    "distributor_discounts",   # contra-revenue -- must be deducted
    "deferred_revenue",        # billed, not earned -- must be excluded
    "release_status",
    "src_batch_id",
]


def banner(n: int, title: str, who: str) -> None:
    print()
    print(RULE)
    print(f"STEP {n} -- {title}")
    print(f"          [{who}]")
    print(RULE)


def main() -> int:
    print(RULE)
    print('QUESTION:  "find me a trend of revenue for the last 5 years"')
    print('ENTITY:    a film studio (ASC 926)')
    print(RULE)

    # ------------------------------------------------------------------
    banner(1, "Route the question", "gaapai")
    r = route("find me a trend of revenue for the last 5 years")
    print(r.explain())
    print()
    print("  -> No computation is claimed. A trend is retrieval, not an")
    print("     accounting judgement. The router does not invent one.")

    # ------------------------------------------------------------------
    banner(2, "Bind the schema to accounting concepts", "gaapai.semantics")
    plan = plan_aggregation(WAREHOUSE_COLUMNS, industry="film")
    for b in plan.bindings:
        if b.concept != Concept.UNKNOWN:
            print(f"    {b.column:<24} -> {b.concept}")
    print()
    print("  Unbound (not aggregated without confirmation):")
    print("    " + ", ".join(plan.unknown_columns))

    # ------------------------------------------------------------------
    banner(3, "Produce the aggregation contract", "gaapai.semantics")
    print(plan.render())

    # ------------------------------------------------------------------
    banner(4, "Inject it into the code-generation prompt", "bridge -> PandasAI")
    contract = bridge.aggregation_contract(columns=WAREHOUSE_COLUMNS, industry="film")
    tools = bridge.tool_descriptions(["revenue"])
    print(f"  GAAP policy .............. {len(bridge.GAAP_POLICY):>6,} chars")
    print(f"  Aggregation contract ..... {len(contract):>6,} chars")
    print(f"  Vetted tool signatures ... {len(tools):>6,} chars")
    print()
    print("  All three go into Agent(description=...) and the skills manager.")
    print(f"  PandasAI importable here: {bridge.available()}")
    if not bridge.available():
        print("    -> PandasAI 3.0 pins python <3.12; steps 5-6 need a 3.11 env.")

    # ------------------------------------------------------------------
    banner(5, "Generate and execute SQL", "PandasAI")
    print("  Without the contract, the model writes:")
    print()
    print("      SELECT fiscal_year, SUM(ultimate_revenue)")
    print("      FROM fact_film_revenue GROUP BY fiscal_year")
    print()
    print("  Syntactically fine. Accounting-wise meaningless -- it sums a")
    print("  forecast denominator and reports it as earned revenue.")
    print()
    print("  With the contract, the model is constrained to:")
    print()
    summable = plan.columns_for(Concept.GROSS_REVENUE) + plan.columns_for(Concept.NET_REVENUE)
    contra = plan.columns_for(Concept.CONTRA_REVENUE)
    expr = " + ".join(f"SUM({c})" for c in summable)
    if contra:
        expr += " - " + " - ".join(f"SUM({c})" for c in contra)
    print(f"      SELECT fiscal_year, {expr}")
    print("      FROM fact_film_revenue")
    print("      WHERE release_status = 'released'      -- ASC 926-20-35-1")
    print("      GROUP BY fiscal_year")

    # ------------------------------------------------------------------
    banner(6, "Comparability -- what a chart hides", "gaapai reference pack")
    print("  A five-year window may straddle ASC 606 adoption. Under the")
    print("  modified retrospective approach the book states:")
    print()
    print("      \"If the entity issues comparative statements, then it reports")
    print("       revenue for prior years under the guidance in effect before")
    print("       adoption.\"")
    print()
    print("  So the early years are ASC 605 numbers and the later years are")
    print("  ASC 606 numbers -- two measurement bases on one trend line.")
    print()
    print("  Other breaks in a five-year window:")
    print("    - discontinued operations restate priors      (ASC 205-20)")
    print("    - acquisitions change the entity              (ASC 805)")
    print("    - foreign currency translation                (ASC 830)")
    print("    - principal/agent reassessment flips gross/net (ASC 606-10-55-36)")

    router = Router()
    if router.pack_path:
        print()
        print("  Reference files for this question:")
        for ref in router.route("film revenue recognition").references[:3]:
            print(f"    {ref['file']}")

    print()
    print(RULE)
    print("The SQL was never the hard part.")
    print(RULE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
