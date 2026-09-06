"""The plain-English question layer."""

from __future__ import annotations

from decimal import Decimal

import pytest

pd = pytest.importorskip("pandas")

from gaapai import ask, semantics  # noqa: E402


def _frame():
    """Two orders: one real snowboard, one gift card, plus a test item.

    Shaped like a real storefront export -- order-level totals on the first
    line of each order, line-level price and quantity on every line.
    """
    return pd.DataFrame({
        "Name": ["#1001", "#1001", "#1002", "#1003"],
        "Paid at": ["2026-06-01 10:00:00 -0400", None,
                    "2026-07-02 11:00:00 -0400", "2026-07-03 09:00:00 -0400"],
        "Subtotal": [300.00, None, 50.00, 10.00],
        "Taxes": [24.00, None, 0.00, 0.00],
        "Tax 1 Value": [24.00, None, 0.00, 0.00],
        "Refunded Amount": [0.00, None, 0.00, 0.00],
        "Lineitem name": ["Snowboard", "Gift Card", "Gift Card", "Test item"],
        "Lineitem sku": ["SB-1", "GC-50", "GC-50", "TEST"],
        "Lineitem price": [250.00, 50.00, 50.00, 10.00],
        "Lineitem quantity": [1, 1, 1, 1],
    })


def _plan(df):
    return semantics.plan_aggregation(list(df.columns), industry="retail")


# ---------------------------------------------------------------------------
# Revenue
# ---------------------------------------------------------------------------


def test_revenue_is_unadjusted_until_rules_are_ratified():
    df = _frame()
    r = ask.compute_revenue(df, _plan(df))
    assert r.unadjusted == Decimal("360.00")
    assert r.adjusted == Decimal("360.00"), "candidates must not change the figure"
    assert r.pending > 0


def test_ratified_rules_deduct_line_amounts_not_whole_orders():
    """Order totals sit on one line; dropping the row would remove the order."""
    df = _frame()
    r = ask.compute_revenue(df, _plan(df),
                            ratified=["gift_card_sales", "test_orders"])
    # 50 (gift card in #1001) + 50 (#1002) + 10 (test) = 110
    assert r.deducted == Decimal("110.00")
    assert r.adjusted == Decimal("250.00")


def test_line_rows_inherit_their_order_period():
    """A continuation line has no date; its deduction must not fall outside time."""
    df = _frame()
    r = ask.compute_revenue(df, _plan(df), ratified=["gift_card_sales"])
    assert "NaT" not in " ".join(map(str, r.by_period.index))
    # The gift card on order #1001 belongs to June, with the order.
    assert float(r.by_period.loc["2026-06", "excluded"]) == 50.0


def test_totals_reconcile():
    df = _frame()
    r = ask.compute_revenue(df, _plan(df), ratified=["gift_card_sales"])
    assert r.unadjusted - r.deducted == r.adjusted
    assert abs(float(r.by_period["reported"].sum()) - float(r.adjusted)) < 0.01


# ---------------------------------------------------------------------------
# Double counting
# ---------------------------------------------------------------------------


def test_an_aggregate_column_is_not_added_to_its_components():
    """`Taxes` + `Tax 1..5 Value` doubled sales tax to 3,923.08 from 1,961.54."""
    df = _frame()
    total, note = ask.sum_without_double_counting(df, ["Taxes", "Tax 1 Value"])
    assert total == Decimal("24.00")
    assert "total of" in note


def test_unrelated_columns_are_still_summed():
    df = _frame()
    total, note = ask.sum_without_double_counting(df, ["Subtotal", "Lineitem price"])
    assert total == Decimal("720.00")
    assert note == ""


# ---------------------------------------------------------------------------
# Question intents
# ---------------------------------------------------------------------------


def test_sales_tax_question_is_not_answered_with_revenue():
    """"How much SALES tax" contains "sales" and returned total revenue."""
    df = _frame()
    a = ask.answer("how much sales tax did I collect", df, _plan(df))
    assert "24.00" in a.headline
    assert "collected" in a.headline


@pytest.mark.parametrize("q,expect", [
    ("what is my revenue", "250.00"),
    ("show revenue by month", "250.00"),
    ("what did you exclude and why", "110.00"),
    ("how many orders did I have", "3 orders"),
])
def test_common_questions_answer_with_the_right_figure(q, expect):
    df = _frame()
    a = ask.answer(q, df, _plan(df), ratified=["gift_card_sales", "test_orders"])
    assert a.understood
    assert expect in a.headline


def test_gift_card_question_explains_the_liability():
    df = _frame()
    a = ask.answer("tell me about gift cards", df, _plan(df))
    assert "100.00" in a.headline
    assert "liability" in a.detail.lower()
    assert "606-10-45-1" in a.citations


def test_an_unrecognised_question_refuses_and_offers_alternatives():
    df = _frame()
    a = ask.answer("what will revenue be next quarter", df, _plan(df))
    assert not a.understood
    assert a.suggestions


def test_an_empty_question_does_not_crash():
    df = _frame()
    assert not ask.answer("   ", df, _plan(df)).understood


def test_pending_items_are_surfaced_as_a_caveat():
    """An unapproved rule must be visible in the answer, not silently omitted."""
    df = _frame()
    a = ask.answer("what is my revenue", df, _plan(df))
    assert any("waiting for your decision" in c for c in a.caveats)


def test_answers_carry_their_authority():
    df = _frame()
    a = ask.answer("how much sales tax", df, _plan(df))
    assert "606-10-32-2A" in a.citations


def test_friendly_names_are_readable():
    assert ask.friendly_rule_name("gift_card_sales") == "Gift card sales"


# ---------------------------------------------------------------------------
# Column profile
# ---------------------------------------------------------------------------


def test_profile_shows_amounts_not_just_column_names():
    """Naming a column proves nothing; the total is the part worth showing."""
    df = _frame()
    imp = ask.important_columns(df, _plan(df))
    row = imp[imp["column"] == "Taxes"].iloc[0]
    assert row["total"] == 24.00
    assert row["read as"] == "tax_collected"
    assert row["filled"] == 3


def test_profile_puts_money_columns_first():
    df = _frame()
    prof = ask.column_profile(df, _plan(df))
    concepts = list(prof["read as"])
    assert concepts.index("gross_revenue") < concepts.index("period")


def test_profile_excludes_empty_columns_from_the_important_list():
    df = _frame()
    df["Never Used"] = None
    imp = ask.important_columns(df, _plan(df))
    assert "Never Used" not in list(imp["column"])


def test_tax_answer_breaks_down_every_column():
    """The table listed column names with no amounts against them."""
    df = _frame()
    a = ask.answer("how much sales tax", df, _plan(df))
    assert "amount" in a.table.columns
    assert "counted" in a.table.columns
    total_row = a.table[a.table["tax column"] == "Taxes"].iloc[0]
    comp_row = a.table[a.table["tax column"] == "Tax 1 Value"].iloc[0]
    assert total_row["counted"] == "yes"
    assert comp_row["counted"].startswith("no")
    assert comp_row["amount"] == 24.00


# ---------------------------------------------------------------------------
# Citations the app actually renders
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("key", ["606-10-32-2A", "606-10-32-10",
                                 "606-10-55-46", "810-10-45-1"])
def test_citations_referenced_by_the_app_resolve(key):
    """These rendered as "(not in catalog)" on screen."""
    from gaapai.core import asc
    assert asc.cite(key)


def test_every_citation_an_answer_returns_is_in_the_catalog():
    from gaapai.core import asc
    df = _frame()
    plan = _plan(df)
    for q in ["what is my revenue", "how much sales tax", "how much was refunded",
              "gift cards", "what did you exclude"]:
        for key in ask.answer(q, df, plan).citations:
            asc.cite(key)


# ---------------------------------------------------------------------------
# Chart type -- every request came back as a bar chart
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("q,kind", [
    ("I want a line graph", "line"),
    ("can you show that as a line chart", "line"),
    ("a pie chart for sales by month", "pie"),
    ("revenue by month as an area chart", "area"),
    ("make it a bar chart", "bar"),
    ("just the numbers", "table"),
    ("show revenue by month", ""),
])
def test_chart_type_is_detected(q, kind):
    assert ask.detect_chart(q) == kind


@pytest.mark.parametrize("q,only", [
    ("I want a line graph", True),
    ("make it a pie chart", True),
    ("show revenue by month as a line chart", False),
    ("what are my top products", False),
])
def test_a_bare_chart_request_is_a_redraw_not_a_new_question(q, only):
    assert ask.chart_only(q) is only


def test_a_data_question_honours_the_chart_type_it_names():
    """chart was hard-coded to "bar", so line and pie requests were ignored."""
    df = _frame()
    a = ask.answer("show revenue by month as a line chart", df, _plan(df))
    assert a.chart == "line"
    assert a.chart_data is not None


def test_a_bare_chart_request_redraws_the_previous_answer():
    """"I want a line graph" matched no intent and was refused outright."""
    df = _frame()
    plan = _plan(df)
    a = ask.answer("I want a line graph", df, plan,
                   previous_question="show revenue by month")
    assert a.understood
    assert a.chart == "line"
    assert a.chart_data is not None


def test_a_bare_chart_request_with_no_history_asks_what_to_chart():
    df = _frame()
    a = ask.answer("I want a line graph", df, _plan(df))
    assert not a.understood
    assert a.suggestions


def test_a_pie_of_a_time_series_is_drawn_but_flagged():
    """Honour the request; say why it reads poorly."""
    df = _frame()
    a = ask.answer("pie chart of revenue by month", df, _plan(df))
    assert a.chart == "pie"
    assert any("parts of a single whole" in c for c in a.caveats)


def test_top_products_also_honours_the_chart_type():
    df = _frame()
    a = ask.answer("top products as a line chart", df, _plan(df))
    assert a.chart == "line"


def test_every_chart_kind_returned_is_renderable():
    df = _frame()
    plan = _plan(df)
    for q in ["show revenue by month", "revenue by month as a line chart",
              "revenue by month as an area chart", "pie chart of revenue by month"]:
        a = ask.answer(q, df, plan)
        assert a.chart in ask.CHART_KINDS or a.chart == "", a.chart
