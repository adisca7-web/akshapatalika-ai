"""Verification of the deterministic GAAP kernel.

Every expected value here was computed by hand from the standard, not read back
off the implementation. That distinction matters: a test that asserts whatever
the code happens to produce verifies nothing.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

import gaapai
from gaapai import Money, money
from gaapai.core.money import allocate, quantize
from gaapai.skills import (
    cashflow,
    eps,
    inventory,
    leases,
    ppe,
    ratios,
    revenue,
    statements,
    tax,
)


# ---------------------------------------------------------------------------
# Exact money
# ---------------------------------------------------------------------------


def test_decimal_addition_is_exact():
    """The float trap: 0.1 + 0.2 != 0.3 in binary floating point."""
    assert money("0.1") + money("0.2") == money("0.3")
    assert (money("0.1") + money("0.2")).amount == Decimal("0.3")


def test_large_ledger_does_not_drift():
    """A hundred thousand cent-level entries must still tie exactly."""
    total = Money.zero()
    for _ in range(100_000):
        total = total + money("0.01")
    assert total == money("1000.00")


def test_currency_mismatch_raises():
    with pytest.raises(ValueError, match="currency mismatch"):
        money("100", "USD") + money("100", "EUR")


def test_allocate_parts_sum_to_whole():
    """ASC 606-10-32-31 requires the entire price to be allocated."""
    parts = allocate(money("100.00"), [1, 1, 1])
    assert sum((p.amount for p in parts), Decimal(0)) == Decimal("100.00")
    # Largest-remainder distributes the stray cent, it does not drop it.
    assert sorted(str(p.amount) for p in parts) == ["33.33", "33.33", "33.34"]


def test_allocate_is_deterministic():
    a = allocate(money("1000.00"), [7, 11, 13])
    b = allocate(money("1000.00"), [7, 11, 13])
    assert [x.amount for x in a] == [x.amount for x in b]


# ---------------------------------------------------------------------------
# ASC 606 revenue
# ---------------------------------------------------------------------------


def test_allocation_ties_to_transaction_price():
    obligations = [
        revenue.PerformanceObligation("Licence", money("600")),
        revenue.PerformanceObligation("Support", money("400")),
    ]
    r = revenue.allocate_transaction_price(money("900"), obligations)
    assert r.ok
    assert r.value["Licence"] == money("540")   # 900 x 600/1000
    assert r.value["Support"] == money("360")   # 900 x 400/1000
    assert (r.value["Licence"] + r.value["Support"]) == money("900")


def test_allocation_handles_rounding_residual():
    obligations = [
        revenue.PerformanceObligation(f"PO{i}", money("100")) for i in range(3)
    ]
    r = revenue.allocate_transaction_price(money("100.00"), obligations)
    total = Money.zero()
    for v in r.value.values():
        total = total + v
    assert total == money("100.00")
    assert r.ok


def test_discount_allocated_to_named_obligations():
    obligations = [
        revenue.PerformanceObligation("Hardware", money("800")),
        revenue.PerformanceObligation("Service", money("200")),
    ]
    r = revenue.allocate_transaction_price(money("900"), obligations,
                                           discount_to=["Service"])
    # Hardware keeps its SSP; the whole 100 discount lands on Service.
    assert r.value["Hardware"] == money("800")
    assert r.value["Service"] == money("100")


def test_variable_consideration_expected_value_and_constraint():
    outcomes = [
        revenue.Outcome("bonus earned", money("1000"), Decimal("0.6")),
        revenue.Outcome("no bonus", money("0"), Decimal("0.4")),
    ]
    r = revenue.variable_consideration(outcomes, "expected_value")
    assert r.value == money("600")          # 1000 x 0.6
    r2 = revenue.variable_consideration(outcomes, "expected_value",
                                        constraint_pct="0.5")
    assert r2.value == money("300")


def test_cost_to_cost_progress():
    """50% complete on cost-to-cost gives 50% of the transaction price."""
    r = revenue.cost_to_cost_progress(
        transaction_price=money("1000"),
        costs_incurred_to_date=money("400"),
        estimated_total_costs=money("800"),
    )
    assert r.value["progress"] == Decimal("0.5")
    assert r.value["cumulative_revenue"] == money("500")
    assert r.value["current_period_revenue"] == money("500")


def test_cost_to_cost_flags_loss_contract():
    r = revenue.cost_to_cost_progress(
        transaction_price=money("1000"),
        costs_incurred_to_date=money("600"),
        estimated_total_costs=money("1200"),  # loss of 200
    )
    assert any("loss position" in c.name for c in r.failures)


def test_five_step_recognised_plus_deferred_ties():
    obligations = [
        revenue.PerformanceObligation("Delivered", money("600"), progress=Decimal(1)),
        revenue.PerformanceObligation("Undelivered", money("400"), progress=Decimal(0)),
    ]
    r = revenue.five_step_revenue(money("1000"), obligations)
    assert r.value["recognized"] == money("600")
    assert r.value["deferred"] == money("400")
    assert r.ok


# ---------------------------------------------------------------------------
# ASC 842 leases
# ---------------------------------------------------------------------------


def _terms(**kw):
    base = dict(payment=money("10000"), periods=12,
                annual_discount_rate=Decimal("0.06"), periods_per_year=12,
                payments_in_advance=True)
    base.update(kw)
    return leases.LeaseTerms(**base)


def test_lease_liability_amortises_to_zero():
    r = leases.amortization_schedule(_terms(), "operating")
    assert r.ok, [c.detail for c in r.failures]
    assert r.schedule[-1]["liab close"].is_zero("0.02")


def test_operating_lease_cost_is_straight_line():
    r = leases.amortization_schedule(_terms(), "operating")
    costs = {row["expense"].amount for row in r.schedule}
    assert len(costs) <= 2  # allows a rounding cent in the final period


def test_finance_lease_expense_is_front_loaded():
    r = leases.amortization_schedule(_terms(), "finance")
    first = r.schedule[0]["expense"]
    last = r.schedule[-1]["expense"]
    assert first > last


def test_total_lease_expense_equals_cash_paid():
    """Both models expense the same total; only the pattern differs."""
    total_cash = money("10000") * 12
    for classification in ("operating", "finance"):
        r = leases.amortization_schedule(_terms(), classification)
        assert (r.value["total_expense"] - total_cash).is_zero("0.05")


def test_annuity_due_is_smaller_liability_than_ordinary():
    """Paying at the start of each period costs less in present value."""
    due = leases.initial_measurement(_terms(payments_in_advance=True))
    ordinary = leases.initial_measurement(_terms(payments_in_advance=False))
    assert due.value["lease_liability"] > ordinary.value["lease_liability"]


def test_lease_classification_transfers_ownership_is_finance():
    r = leases.classify_lease(_terms(transfers_ownership=True))
    assert r.value == "finance"


def test_short_term_lease_is_flagged():
    r = leases.classify_lease(_terms(periods=12, periods_per_year=12))
    assert any("short-term" in c.name for c in r.failures)


# ---------------------------------------------------------------------------
# ASC 330 inventory
# ---------------------------------------------------------------------------


def _layers():
    opening = inventory.Layer(Decimal(100), money("10"), "opening")
    purchase = inventory.Layer(Decimal(200), money("12"), "purchase")
    return opening, [purchase]


def test_fifo_cost_flow():
    """100 @ 10 then 150 @ 12 = 2,800 COGS; 50 @ 12 = 600 ending."""
    opening, purchases = _layers()
    r = inventory.cost_flow(opening, purchases, 250, "fifo")
    assert r.value["cogs"] == money("2800")
    assert r.value["ending_inventory"] == money("600")
    assert r.ok


def test_lifo_cost_flow():
    """200 @ 12 then 50 @ 10 = 2,900 COGS; 50 @ 10 = 500 ending."""
    opening, purchases = _layers()
    r = inventory.cost_flow(opening, purchases, 250, "lifo")
    assert r.value["cogs"] == money("2900")
    assert r.value["ending_inventory"] == money("500")


def test_weighted_average_cost_flow():
    """3,400 / 300 units = 11.3333 per unit."""
    opening, purchases = _layers()
    r = inventory.cost_flow(opening, purchases, 250, "weighted_average")
    assert r.value["cogs"].round(2) == money("2833.33")
    assert r.value["ending_inventory"].round(2) == money("566.67")


def test_cogs_plus_ending_ties_to_goods_available():
    opening, purchases = _layers()
    for method in ("fifo", "lifo", "weighted_average"):
        r = inventory.cost_flow(opening, purchases, 250, method)
        assert r.ok, method


def test_lcnrv_writes_down_to_nrv():
    r = inventory.lower_of_cost(
        cost=money("100"), selling_price=money("90"),
        cost_to_complete_and_sell=money("10"), method="fifo",
    )
    assert r.value["carrying_amount"] == money("80")   # NRV 90 - 10
    assert r.value["writedown"] == money("20")


def test_lifo_requires_market_inputs():
    """LIFO uses lower of cost or market, which needs replacement cost."""
    with pytest.raises(ValueError, match="replacement_cost"):
        inventory.lower_of_cost(
            cost=money("100"), selling_price=money("120"),
            cost_to_complete_and_sell=money("10"), method="lifo",
        )


def test_lcm_floors_at_nrv_less_normal_profit():
    """Replacement cost below the floor is raised to the floor."""
    r = inventory.lower_of_cost(
        cost=money("100"), selling_price=money("120"),
        cost_to_complete_and_sell=money("10"), method="lifo",
        replacement_cost=money("50"), normal_profit_margin=money("20"),
    )
    # ceiling NRV = 110, floor = 90, replacement 50 -> market = 90
    # carrying = min(cost 100, market 90) = 90
    assert r.value["carrying_amount"] == money("90")


# ---------------------------------------------------------------------------
# ASC 360 PP&E
# ---------------------------------------------------------------------------


def test_straight_line_depreciation():
    r = ppe.depreciation_schedule(money("100000"), money("10000"), 5, "straight_line")
    assert r.schedule[0]["depreciation"] == money("18000")
    assert r.value["total_depreciation"] == money("90000")
    assert r.value["final_carrying_amount"] == money("10000")
    assert r.ok


def test_double_declining_stops_at_salvage():
    """40%, 24%, 14.4%, 8.64%, then truncated to reach exactly salvage."""
    r = ppe.depreciation_schedule(money("100000"), money("10000"), 5,
                                  "declining_balance", rate_factor=2)
    charges = [row["depreciation"] for row in r.schedule]
    assert charges[0] == money("40000")
    assert charges[1] == money("24000")
    assert charges[4] == money("2960")   # floored so book value lands on 10,000
    assert r.value["final_carrying_amount"] == money("10000")
    assert r.ok


def test_sum_of_years_digits():
    """n=5 gives SYD 15; first year is 5/15 of the 90,000 base."""
    r = ppe.depreciation_schedule(money("100000"), money("10000"), 5,
                                  "sum_of_years_digits")
    assert r.schedule[0]["depreciation"] == money("30000")
    assert r.schedule[4]["depreciation"] == money("6000")
    assert r.ok


def test_impairment_not_recognised_when_recoverable():
    """Step 1 uses UNDISCOUNTED flows; passing it stops the test."""
    r = ppe.impairment_test(
        carrying_amount=money("1000"),
        undiscounted_cash_flows=money("1100"),
        fair_value=money("800"),        # below carrying, but irrelevant
    )
    assert r.value["impaired"] is False
    assert r.value["loss"] == money("0")


def test_impairment_measured_against_fair_value():
    r = ppe.impairment_test(
        carrying_amount=money("1000"),
        undiscounted_cash_flows=money("900"),
        fair_value=money("750"),
    )
    assert r.value["impaired"] is True
    assert r.value["loss"] == money("250")
    assert r.value["new_carrying_amount"] == money("750")


# ---------------------------------------------------------------------------
# ASC 260 EPS
# ---------------------------------------------------------------------------


def test_weighted_average_shares():
    changes = [
        eps.ShareChange(Decimal(100000), Decimal(12), "opening"),
        eps.ShareChange(Decimal(120000), Decimal(6), "June issue"),
    ]
    r = eps.weighted_average_shares(changes, 12)
    assert r.value == Decimal(160000)   # 100,000 + 120,000 x 6/12


def test_basic_eps_deducts_preferred():
    r = eps.basic_eps(money("1000000"), 400000, money("50000"))
    assert r.value == Decimal("2.38")   # 950,000 / 400,000 = 2.375


def test_diluted_eps_treasury_stock_method():
    """100k options at 10 with market 20: 50k incremental shares."""
    options = [eps.OptionGrant("ESO", Decimal(100000), money("10"))]
    r = eps.diluted_eps(
        net_income=money("1000000"), weighted_shares=400000,
        average_market_price=money("20"), options=options,
    )
    assert r.value["basic_eps"] == Decimal("2.50")
    assert r.value["diluted_shares"] == Decimal(450000)
    assert r.value["diluted_eps"] == Decimal("2.22")
    assert r.ok


def test_out_of_the_money_options_excluded():
    options = [eps.OptionGrant("ESO", Decimal(100000), money("30"))]
    r = eps.diluted_eps(
        net_income=money("1000000"), weighted_shares=400000,
        average_market_price=money("20"), options=options,
    )
    assert r.value["diluted_shares"] == Decimal(400000)


def test_antidilutive_convertible_is_excluded():
    """A convertible with incremental EPS above basic must be dropped."""
    conv = eps.Convertible("Rich note", Decimal(10000), money("100000"))
    r = eps.diluted_eps(
        net_income=money("1000000"), weighted_shares=400000,
        average_market_price=money("20"), convertibles=[conv],
    )
    assert "Rich note" in r.value["excluded_antidilutive"]
    assert r.value["diluted_eps"] == r.value["basic_eps"]


def test_diluted_never_exceeds_basic():
    conv = eps.Convertible("Cheap note", Decimal(200000), money("10000"))
    r = eps.diluted_eps(
        net_income=money("1000000"), weighted_shares=400000,
        average_market_price=money("20"), convertibles=[conv],
    )
    assert r.value["diluted_eps"] <= r.value["basic_eps"]
    assert r.ok


# ---------------------------------------------------------------------------
# ASC 230 cash flows
# ---------------------------------------------------------------------------


def test_indirect_method_ties_to_change_in_cash():
    adjustments = [
        cashflow.Adjustment("Depreciation", money("20000"), "noncash"),
        cashflow.Adjustment("Increase in receivables", money("-15000"), "working_capital"),
        cashflow.Adjustment("Increase in payables", money("5000"), "working_capital"),
    ]
    r = cashflow.indirect_method(
        net_income=money("100000"),
        adjustments=adjustments,
        investing={"Purchase of equipment": money("-50000")},
        financing={"Dividends paid": money("-30000")},
        beginning_cash=money("40000"),
        ending_cash=money("70000"),
    )
    assert r.value["operating"] == money("110000")
    assert r.value["net_change"] == money("30000")
    assert r.value["ending_cash"] == money("70000")
    assert r.ok, [c.detail for c in r.failures]


def test_cash_flow_mismatch_is_caught():
    r = cashflow.indirect_method(
        net_income=money("100000"), adjustments=[],
        beginning_cash=money("40000"),
        ending_cash=money("999999"),   # deliberately wrong
    )
    assert not r.ok
    assert any("ties to the change in cash" in c.name for c in r.failures)


def test_interest_paid_is_operating_under_gaap():
    assert cashflow.classify("interest paid").value == "operating"
    assert cashflow.classify("dividends paid").value == "financing"
    assert cashflow.classify("dividends received").value == "operating"


# ---------------------------------------------------------------------------
# ASC 205/210 statements
# ---------------------------------------------------------------------------


def _trial_balance():
    A = statements.Account
    return [
        A("Cash", statements.CURRENT_ASSET, money("70000")),
        A("Accounts receivable", statements.CURRENT_ASSET, money("30000")),
        A("Inventory", statements.CURRENT_ASSET, money("50000")),
        A("Equipment", statements.NONCURRENT_ASSET, money("200000")),
        A("Accumulated depreciation", statements.NONCURRENT_ASSET,
          money("40000"), contra=True),
        A("Accounts payable", statements.CURRENT_LIABILITY, money("35000")),
        A("Notes payable", statements.NONCURRENT_LIABILITY, money("100000")),
        A("Common stock", statements.EQUITY, money("120000")),
        A("Revenue", statements.REVENUE, money("300000")),
        A("Cost of goods sold", statements.EXPENSE, money("180000")),
        A("Operating expenses", statements.EXPENSE, money("65000")),
    ]


def test_trial_balance_is_in_balance():
    r = statements.verify_trial_balance(_trial_balance())
    assert r.value["balanced"] is True
    assert r.value["debits"] == money("595000")
    assert r.value["credits"] == money("595000")


def test_unbalanced_trial_balance_fails_loudly():
    accounts = _trial_balance()
    accounts[0] = statements.Account("Cash", statements.CURRENT_ASSET, money("71000"))
    r = statements.verify_trial_balance(accounts)
    assert r.value["balanced"] is False
    assert not r.ok


def test_statements_articulate():
    r = statements.build_statements(_trial_balance())
    v = r.value
    assert v["total_assets"] == money("310000")
    assert v["total_liabilities"] == money("135000")
    assert v["net_income"] == money("55000")
    assert v["total_equity"] == money("175000")
    assert v["working_capital"] == money("115000")
    # assets = liabilities + equity
    assert v["total_assets"] == v["total_liabilities"] + v["total_equity"]
    assert r.ok, [c.detail for c in r.failures]


def test_retained_earnings_rolls_forward():
    r = statements.build_statements(
        _trial_balance(),
        beginning_retained_earnings=money("10000"),
        dividends_declared=money("5000"),
    )
    # 10,000 + 55,000 - 5,000
    assert r.value["ending_retained_earnings"] == money("60000")


def test_loader_rejects_bad_rows():
    r = statements.load_trial_balance([
        {"name": "Cash", "section": "current_asset", "balance": "1,250.00"},
        {"name": "Mystery", "section": "not_a_section", "balance": "10"},
    ])
    assert len(r.value) == 1
    assert r.value[0].balance == money("1250.00")
    assert not r.ok


# ---------------------------------------------------------------------------
# ASC 740 income taxes
# ---------------------------------------------------------------------------


def test_deferred_tax_liability_from_book_over_tax_basis():
    diff = tax.TemporaryDifference("Equipment", money("100000"), money("70000"))
    r = tax.deferred_tax([diff], Decimal("0.21"))
    assert r.value["gross_dtl"] == money("6300")   # 30,000 x 21%
    assert r.value["gross_dta"] == money("0")


def _warranty_accrual():
    """A warranty accrued for books but deductible only when paid.

    Book basis of the liability is 50,000; tax basis is nil. Settling it
    produces a future deductible amount, so it is a deferred tax ASSET.
    """
    return tax.TemporaryDifference("Warranty accrual", money("50000"),
                                   money("0"), is_asset=False)


def test_warranty_accrual_creates_a_deferred_tax_asset():
    r = tax.deferred_tax([_warranty_accrual()], Decimal("0.21"))
    assert r.value["gross_dta"] == money("10500")   # 50,000 x 21%
    assert r.value["gross_dtl"] == money("0")


def test_valuation_allowance_is_a_threshold_not_a_weighting():
    """Below 50% the whole DTA is reserved; it is not scaled by probability."""
    r = tax.deferred_tax([_warranty_accrual()], Decimal("0.21"),
                         realization_probability=Decimal("0.40"))
    assert r.value["gross_dta"] == money("10500")
    # A probability weighting would have given 10,500 x 0.40 = 4,200.
    assert r.value["valuation_allowance"] == money("10500")
    assert r.value["net_deferred_tax"] == money("0")


def test_no_allowance_when_more_likely_than_not():
    r = tax.deferred_tax([_warranty_accrual()], Decimal("0.21"),
                         realization_probability=Decimal("0.80"))
    assert r.value["valuation_allowance"] == money("0")
    assert r.value["net_deferred_tax"] == money("10500")


def test_effective_tax_rate_reconciliation():
    perms = [tax.PermanentDifference("Meals and entertainment", money("10000"))]
    r = tax.effective_tax_rate(money("1000000"), Decimal("0.21"),
                               permanent_differences=perms)
    # 210,000 + (10,000 x 21%) = 212,100
    assert r.value["tax_expense"] == money("212100")
    assert quantize(r.value["effective_rate"], 6) == Decimal("0.212100")


# ---------------------------------------------------------------------------
# Ratios
# ---------------------------------------------------------------------------


def test_liquidity_ratios():
    r = ratios.liquidity(money("150000"), money("35000"),
                         inventory=money("50000"))
    assert r.value["working_capital"] == money("115000")
    assert quantize(r.value["current_ratio"], 4) == Decimal("4.2857")


def test_dupont_identity_holds():
    r = ratios.dupont(money("55000"), money("300000"),
                      money("310000"), money("175000"))
    assert r.ok, [c.detail for c in r.failures]
    # margin x turnover x multiplier must equal net income / equity
    assert quantize(r.value["return_on_equity"], 6) == quantize(
        Decimal("55000") / Decimal("175000"), 6
    )


# ---------------------------------------------------------------------------
# Registry and evidence
# ---------------------------------------------------------------------------


def test_every_subskill_returns_a_workpaper():
    for sub in gaapai.REGISTRY.subskills():
        assert sub.summary, sub.qualified_name
        assert sub.citations or sub.skill == "ratios", sub.qualified_name


def test_fingerprint_is_stable_across_runs():
    a = ppe.depreciation_schedule(money("100000"), money("10000"), 5)
    b = ppe.depreciation_schedule(money("100000"), money("10000"), 5)
    assert a.fingerprint == b.fingerprint


def test_fingerprint_changes_with_inputs():
    a = ppe.depreciation_schedule(money("100000"), money("10000"), 5)
    b = ppe.depreciation_schedule(money("100000"), money("10000"), 6)
    assert a.fingerprint != b.fingerprint


def test_workpaper_renders_with_authority():
    r = revenue.allocate_transaction_price(
        money("900"),
        [revenue.PerformanceObligation("A", money("600")),
         revenue.PerformanceObligation("B", money("400"))],
    )
    paper = r.workpaper()
    assert "WORKPAPER" in paper
    assert "606-10-32-31" in paper
    assert "TIES" in paper


def test_result_serialises_to_json():
    r = ppe.impairment_test(money("1000"), money("900"), money("750"))
    payload = r.to_json()
    assert '"skill": "ppe.impairment_test"' in payload
    assert '"asc": "360-10-35-17"' in payload


def test_citation_lookup_rejects_unknown_paragraph():
    with pytest.raises(KeyError, match="not in the catalog"):
        gaapai.cite("999-99-99-9")


def test_coverage_maps_paragraphs_to_implementations():
    cov = gaapai.coverage()
    assert "606-10-32-31" in cov
    assert any("allocate_transaction_price" in s
               for s in cov["606-10-32-31"])
