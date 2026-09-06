"""Semantic mapping verification.

The claim under test: given a warehouse schema and an industry, the layer picks
the accounting-correct revenue column and refuses the trap column -- the one
that looks like revenue lexically but is a volume or bookings metric.
"""

from __future__ import annotations

import pytest

from gaapai.adapters import aggregation_contract
from gaapai.semantics import (
    Concept,
    PROFILES,
    bind_columns,
    industries,
    plan_aggregation,
    profile_for,
)


# ---------------------------------------------------------------------------
# Column binding
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "column,concept",
    [
        ("net_revenue", Concept.NET_REVENUE),
        ("gross_sales", Concept.GROSS_REVENUE),
        ("sales_returns", Concept.CONTRA_REVENUE),
        ("promotional_allowances", Concept.CONTRA_REVENUE),
        ("customer_rebates", Concept.CONTRA_REVENUE),
        ("deferred_revenue", Concept.DEFERRED_REVENUE),
        ("unearned_premium", Concept.DEFERRED_REVENUE),
        ("cogs", Concept.COST_OF_REVENUE),
        ("fiscal_year", Concept.PERIOD),
        ("business_unit", Concept.SEGMENT),
        ("curr_code", Concept.CURRENCY),
        ("widget_flag", Concept.UNKNOWN),
        ("Discount Code", Concept.LABEL),
        ("Tax 1 Name", Concept.LABEL),
        ("Financial Status", Concept.LABEL),
        ("Subtotal", Concept.GROSS_REVENUE),
        ("Taxes", Concept.TAX_COLLECTED),
        ("Shipping", Concept.SHIPPING_REVENUE),
        ("Created at", Concept.PERIOD),
    ],
)
def test_column_binds_to_expected_concept(column, concept):
    assert bind_columns([column])[0].concept == concept


def test_contra_patterns_beat_revenue_patterns():
    """"sales_returns" contains "sales"; binding it as revenue would flip a
    deduction into an addition."""
    assert bind_columns(["sales_returns"])[0].concept == Concept.CONTRA_REVENUE
    assert bind_columns(["revenue_discounts"])[0].concept == Concept.CONTRA_REVENUE


def test_binding_is_case_and_separator_insensitive():
    for variant in ["Net Revenue", "NET_REVENUE", "net-revenue", "NetRevenue"]:
        b = bind_columns([variant])[0]
        assert b.concept in (Concept.NET_REVENUE, Concept.GROSS_REVENUE), variant


def test_unknown_columns_are_flagged_not_guessed():
    plan = plan_aggregation(["fiscal_year", "revenue", "widget_flag"])
    assert "widget_flag" in plan.unknown_columns


def test_text_columns_never_enter_the_aggregation():
    """"Discount Code" matches the contra pattern but holds text.

    Binding it as contra-revenue put it into a SUM() that would raise at
    runtime -- found on a real Shopify export.
    """
    plan = plan_aggregation(
        ["Created at", "Subtotal", "Discount Code", "Discount Amount", "Tax 1 Name"],
        industry="retail",
    )
    shape = plan.render()
    assert "SUM(Discount Code)" not in shape
    assert "SUM(Tax 1 Name)" not in shape
    assert "SUM(Discount Amount)" in shape


# ---------------------------------------------------------------------------
# Industry resolution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "given,expected_asc",
    [
        ("926", "926"), ("film", "926"), ("ASC 926", "926"),
        ("insurance", "944"), ("944", "944"),
        ("casinos", "924"), ("software", "985"),
        ("not-for-profit", "958"), ("franchisors", "952"),
        (None, "606"), ("", "606"), ("nonexistent industry", "606"),
    ],
)
def test_industry_resolves(given, expected_asc):
    assert profile_for(given).asc == expected_asc


def test_reference_only_industries_still_resolve():
    """Industries without a distinctive revenue divergence still reach their file."""
    prof = profile_for("922")
    assert prof.asc == "922"
    assert "asc922" in prof.skill_file


def test_every_industry_is_reachable():
    for code in industries():
        prof = profile_for(code)
        assert prof is PROFILES.get(code) or prof.asc == code, code


def test_every_profile_cites_authority():
    for code, prof in PROFILES.items():
        assert prof.rules, code
        for rule in prof.rules:
            assert rule.citation, f"{code}: {rule.requirement}"


# ---------------------------------------------------------------------------
# The trap columns -- the whole point of the layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "industry,trap,correct,others",
    [
        # Gaming handle is the amount wagered, not revenue.
        ("casinos", "handle", "net_win", ["promotional_allowances"]),
        # Written premium is a billing metric; earned premium is revenue.
        ("insurance", "written_premium", "earned_premium", []),
        # Ultimate revenue is a forecast denominator, not actual revenue.
        ("film", "ultimate_revenue", "theatrical_revenue", []),
        # ARR is a bookings metric.
        ("software", "arr", "licence_revenue", []),
        # Franchisee system-wide sales belong to the franchisee.
        ("franchisors", "system_wide_sales", "royalty_revenue", []),
        # Origination volume is a volume metric.
        ("mortgage banking", "loan_volume", "servicing_fee_revenue", []),
        # Gross wellhead value includes the royalty owners' share.
        ("oil and gas", "gross_wellhead_value", "oil_revenue", []),
        # An agent's GMV is not its revenue.
        (None, "gross_bookings", "commission_revenue", []),
    ],
)
def test_trap_column_is_forbidden_not_merely_warned(industry, trap, correct, others):
    plan = plan_aggregation(["fiscal_year", trap, correct] + others, industry=industry)

    assert trap in plan.columns_for(Concept.FORBIDDEN), (
        f"{trap} should be forbidden under {industry}"
    )
    summable = plan.columns_for(Concept.GROSS_REVENUE) + plan.columns_for(Concept.NET_REVENUE)
    assert trap not in summable, f"{trap} must not be summable"
    assert correct in summable, f"{correct} should be the revenue column"

    # And it must be absent from the rendered aggregation expression, not just
    # mentioned in a warning the model may ignore.
    shape = plan.render().split("REQUIRED AGGREGATION SHAPE:")[1].split("\n\n")[0]
    assert trap not in shape, f"{trap} leaked into the aggregation shape"


def test_ceded_premium_is_a_deduction_not_an_addition():
    plan = plan_aggregation(
        ["fy", "earned_premium", "ceded_premium"], industry="insurance"
    )
    assert "ceded_premium" in plan.columns_for(Concept.CONTRA_REVENUE)
    assert "ceded_premium" not in plan.columns_for(Concept.GROSS_REVENUE)


# ---------------------------------------------------------------------------
# The rendered contract
# ---------------------------------------------------------------------------


def test_contract_nets_contra_revenue():
    plan = plan_aggregation(["fiscal_year", "gross_sales", "sales_returns"])
    shape = plan.render()
    assert "SUM(gross_sales) - SUM(sales_returns)" in shape


def test_contract_excludes_deferred_revenue():
    plan = plan_aggregation(["fiscal_year", "revenue", "deferred_revenue"])
    assert "EXCLUDE deferred/unearned columns" in plan.render()


def test_contract_stops_when_no_revenue_column_exists():
    plan = plan_aggregation(["fiscal_year", "widget_count", "region"])
    assert plan.blocked
    rendered = plan.render()
    assert "NO revenue column identified" in rendered
    assert "Do not select one by position" in rendered


def test_contract_flags_gross_and_net_together():
    plan = plan_aggregation(["fy", "gross_sales", "net_revenue"])
    assert any("double-count" in w for w in plan.warnings)


def test_contract_flags_missing_period_column():
    plan = plan_aggregation(["revenue", "region"])
    assert any("period column" in w for w in plan.warnings)


def test_contract_carries_industry_rules_and_citations():
    rendered = plan_aggregation(
        ["fiscal_year", "earned_premium"], industry="insurance"
    ).render()
    assert "ASC 944" in rendered
    assert "944-605-25-1" in rendered
    assert "EARNED premium" in rendered


def test_plan_is_deterministic():
    cols = ["fiscal_year", "handle", "net_win", "promotional_allowances"]
    a = plan_aggregation(cols, industry="casinos").to_dict()
    b = plan_aggregation(cols, industry="casinos").to_dict()
    assert a == b


# ---------------------------------------------------------------------------
# Bridge integration
# ---------------------------------------------------------------------------


def test_bridge_renders_contract_from_columns():
    contract = aggregation_contract(
        columns=["fiscal_year", "handle", "net_win"], industry="924"
    )
    assert "GAAP AGGREGATION CONTRACT" in contract
    assert "FORBIDDEN AS REVENUE" in contract
    assert "handle" in contract


def test_bridge_reads_columns_off_a_dataframe():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"fiscal_year": [2024], "written_premium": [1],
                       "earned_premium": [1]})
    contract = aggregation_contract(df, industry="insurance")
    assert "earned_premium" in contract
    assert "written_premium" in contract


def test_bridge_returns_empty_when_no_columns_available():
    assert aggregation_contract(columns=[]) == ""


def test_contract_now_reaches_the_prompt():
    """The gap this layer closed: the prompt previously had no industry
    awareness, no column bindings, and no aggregation guidance at all."""
    contract = aggregation_contract(
        columns=["fiscal_year", "ultimate_revenue", "theatrical_revenue"],
        industry="film",
    )
    for token in ["926", "film", "ultimate_revenue", "theatrical_revenue",
                  "FORBIDDEN", "MUST"]:
        assert token.lower() in contract.lower(), token


# ---------------------------------------------------------------------------
# Row-level rules
# ---------------------------------------------------------------------------

SHOPIFY_COLUMNS = [
    "Name", "Financial Status", "Paid at", "Currency", "Subtotal", "Shipping",
    "Taxes", "Total", "Discount Code", "Discount Amount", "Created at",
    "Lineitem quantity", "Lineitem name", "Lineitem price", "Lineitem sku",
    "Lineitem requires shipping", "Lineitem taxable", "Cancelled at",
    "Refunded Amount",
]


def test_gift_cards_are_flagged_as_a_contract_liability():
    """A gift card sale is deferred revenue, not revenue (ASC 606-10-45-1).

    No column says "gift card" -- the signal is row-level, in the line item
    name. Column binding alone missed this on a real Shopify export.
    """
    rendered = plan_aggregation(SHOPIFY_COLUMNS, industry="retail").render()
    assert "ROW-LEVEL RULES" in rendered
    assert "CONTRACT LIABILITY" in rendered
    assert "606-10-45-1" in rendered
    assert "606-10-55-46" in rendered      # breakage


def test_row_rules_only_appear_when_their_column_exists():
    """A gift-card rule is noise on a schema with no line-item column."""
    plan = plan_aggregation(["fiscal_year", "revenue"], industry="retail")
    names = {r.name for r, _ in plan.applicable_row_rules()}
    assert "gift_card_sales" not in names

    plan2 = plan_aggregation(SHOPIFY_COLUMNS, industry="retail")
    names2 = {r.name for r, _ in plan2.applicable_row_rules()}
    assert {"gift_card_sales", "cancelled_orders", "test_orders"} <= names2


def test_cancelled_orders_are_excluded():
    plan = plan_aggregation(SHOPIFY_COLUMNS, industry="retail")
    rule = next(r for r, _ in plan.applicable_row_rules() if r.name == "cancelled_orders")
    assert rule.becomes == Concept.FORBIDDEN
    assert rule.citation == "606-10-25-1"


def test_shopify_export_binds_correctly_end_to_end():
    """The regression that started this: Shopify's real column names."""
    plan = plan_aggregation(SHOPIFY_COLUMNS, industry="retail")
    assert plan.columns_for(Concept.GROSS_REVENUE) == ["Subtotal"]
    assert "Total" in plan.columns_for(Concept.FORBIDDEN)
    assert "Taxes" in plan.columns_for(Concept.TAX_COLLECTED)
    assert "Shipping" in plan.columns_for(Concept.SHIPPING_REVENUE)
    assert "Refunded Amount" in plan.columns_for(Concept.CONTRA_REVENUE)
    assert not plan.blocked

    shape = plan.render()
    assert "SUM(Subtotal)" in shape
    assert "SUM(Total)" not in shape
    assert "liability, not revenue" in shape      # tax exclusion


def test_gift_card_regexes_match_real_line_item_names():
    import re
    plan = plan_aggregation(SHOPIFY_COLUMNS, industry="retail")
    rule = next(r for r, _ in plan.applicable_row_rules() if r.name == "gift_card_sales")
    pat = re.compile(rule.match_value)
    for name in ["Gift Card - $10", "Gift Card - $100", "eGift Card",
                 "Gift Certificate"]:
        assert pat.search(name), name
    for name in ["The Collection Snowboard: Liquid", "Selling Plans Ski Wax"]:
        assert not pat.search(name), name


# ---------------------------------------------------------------------------
# Row rules derived from the reference pack, across every industry
# ---------------------------------------------------------------------------


def test_every_profile_has_row_rules():
    """A rule that lives only in a document is not enforced.

    The gift-card miss happened because the rule existed in the reference pack
    as prose and nowhere in the pipeline. Every profile now carries executable
    row rules, not just column rules.
    """
    for code, prof in PROFILES.items():
        assert prof.row_rules, f"{code} has no row rules"


def test_row_rules_are_well_formed():
    import re
    for code, prof in PROFILES.items():
        for rule in prof.row_rules:
            re.compile(rule.match_column)      # must compile
            re.compile(rule.match_value)
            assert rule.citation, f"{code}/{rule.name} has no citation"
            assert rule.requirement, f"{code}/{rule.name} has no requirement"
            assert rule.severity in ("must", "should", "note")
            assert rule.becomes in vars(Concept).values(), rule.becomes


@pytest.mark.parametrize(
    "industry,rule_name,sample,should_match",
    [
        ("958", "conditional_contributions", "conditional", True),
        ("958", "agency_transactions", "agent", True),
        ("958", "conditional_contributions", "unconditional promise", False),
        ("926", "unreleased_films", "in production", True),
        ("926", "participation_costs", "Participation - lead actor", True),
        ("944", "ceded_reinsurance", "Ceded to reinsurer", True),
        ("924", "outstanding_chips", "Chips outstanding", True),
        ("932", "downstream_activities", "Refining margin", True),
        ("952", "system_wide_sales", "System-wide sales", True),
        ("970", "incidental_operations", "Incidental rental", True),
        ("985", "internal_use", "Internal-use ERP build", True),
        ("942", "nonaccrual_loans", "non-accrual", True),
    ],
)
def test_row_rule_patterns_match_realistic_values(industry, rule_name, sample, should_match):
    import re
    prof = PROFILES[industry]
    rule = next(r for r in prof.row_rules if r.name == rule_name)
    assert bool(re.search(rule.match_value, sample)) is should_match, (
        f"{rule_name}: {sample!r}"
    )


def test_conditional_contributions_are_excluded_entirely():
    """ASC 958-605-25-5A: a conditional transfer is not yet a contribution."""
    prof = PROFILES["958"]
    rule = next(r for r in prof.row_rules if r.name == "conditional_contributions")
    assert rule.becomes == Concept.FORBIDDEN
    assert rule.severity == "must"
    assert "958-605-25-5A" == rule.citation


def test_row_rules_reach_the_contract_for_their_industry():
    cols = ["fiscal_year", "revenue", "restriction_type", "condition_status", "role"]
    rendered = plan_aggregation(cols, industry="958").render()
    assert "ROW-LEVEL RULES" in rendered
    assert "NOT YET revenue" in rendered
    assert "958-605-25-5A" in rendered
