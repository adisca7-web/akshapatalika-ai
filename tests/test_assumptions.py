"""Assumptions stated in conversation, and the profit they make computable."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gaapai.assumptions import (Assumptions, is_assumption_statement,
                                parse_assumptions)

pd = pytest.importorskip("pandas")

from gaapai import ask, semantics  # noqa: E402


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text,rate", [
    ("cost of goods is 50% of product revenue", "0.50"),
    ("COGS = 60%", "0.60"),
    ("the products cost 45% of the sale price", "0.45"),
    ("if the cost of the products is 50% of the sale price", "0.50"),
    ("assume a 30% cost", "0.30"),
])
def test_a_cost_rate_is_understood_however_phrased(text, rate):
    a, changes = parse_assumptions(text)
    assert a.cogs_rate == Decimal(rate), changes


@pytest.mark.parametrize("text,cogs", [
    ("gross margin is 40%", "0.60"),
    ("we run a 25% margin", "0.75"),
])
def test_a_margin_is_converted_to_a_cost_rate(text, cogs):
    a, _ = parse_assumptions(text)
    assert a.cogs_rate == Decimal(cogs)


def test_operating_expenses_are_captured_separately():
    a, _ = parse_assumptions("operating expenses are 20%")
    assert a.opex_rate == Decimal("0.20")
    assert a.cogs_rate is None


def test_an_impossible_rate_is_rejected_rather_than_used():
    a, changes = parse_assumptions("cost of goods is 500%")
    assert a.cogs_rate is None
    assert not changes


def test_assumptions_accumulate_across_turns():
    a, _ = parse_assumptions("cost of goods is 50%")
    a, changes = parse_assumptions("operating expenses are 20%", a)
    assert a.cogs_rate == Decimal("0.50")
    assert a.opex_rate == Decimal("0.20")
    assert len(changes) == 1, "only the new fact is reported as a change"


def test_a_restated_rate_replaces_the_old_one():
    a, _ = parse_assumptions("cost of goods is 50%")
    a, changes = parse_assumptions("actually gross margin is 40%", a)
    assert a.cogs_rate == Decimal("0.60")
    assert changes


@pytest.mark.parametrize("text,statement", [
    ("Cost of goods is 50% of product revenue", True),
    ("cogs = 60%", True),
    ("if cost of goods is 50%, show profitability by month", False),
    ("what is my revenue", False),
])
def test_a_bare_statement_is_told_apart_from_a_question(text, statement):
    """"Cost of goods is 50% of product revenue" was answered with total revenue."""
    assert is_assumption_statement(text) is statement


def test_assumptions_describe_themselves_for_a_caveat():
    a, _ = parse_assumptions("cost of goods is 50%")
    assert "50%" in a.caveat()
    assert "not on your books" in a.caveat()
    assert "ASC 330" in a.caveat()


# ---------------------------------------------------------------------------
# Profitability
# ---------------------------------------------------------------------------


def _frame():
    return pd.DataFrame({
        "Name": ["#1", "#2"],
        "Paid at": ["2026-06-01 10:00:00 -0400", "2026-07-02 11:00:00 -0400"],
        "Subtotal": [300.00, 100.00],
        "Lineitem name": ["Snowboard", "Boots"],
        "Lineitem price": [300.00, 100.00],
        "Lineitem quantity": [1, 1],
    })


def _plan(df):
    return semantics.plan_aggregation(list(df.columns), industry="retail")


def test_profit_is_computed_by_the_engine_not_described_in_prose():
    df = _frame()
    a = ask.answer("show profitability by month", df, _plan(df),
                   assume=Assumptions(cogs_rate=Decimal("0.5")))
    assert a.understood
    assert "200.00" in a.headline          # 400 revenue, 50% cost
    assert "50.0% margin" in a.headline
    assert a.chart_data is not None
    assert list(a.table.columns)[:3] == ["revenue", "cost of goods", "gross profit"]


def test_a_cost_rate_in_the_question_itself_is_applied_immediately():
    """The user's actual message: assumption and request in one sentence."""
    df = _frame()
    a = ask.answer(
        "If the cost of the products is 50% of the sale price, can you create "
        "a profitability chart by month?", df, _plan(df))
    assert a.understood
    assert "gross profit" in a.headline
    assert a.chart_data is not None
    assert a.assumptions.cogs_rate == Decimal("0.5")


def test_profit_without_a_cost_rate_asks_for_one_rather_than_guessing():
    df = _frame()
    a = ask.answer("show profitability by month", df, _plan(df))
    assert not a.understood
    assert "cost" in a.headline.lower()
    assert any("50%" in s for s in a.suggestions)


def test_a_bare_statement_is_acknowledged_not_answered_with_revenue():
    df = _frame()
    a = ask.answer("Cost of goods is 50% of product revenue", df, _plan(df))
    assert a.headline == "Noted."
    assert a.assumptions.cogs_rate == Decimal("0.5")
    assert "29" not in a.headline and "400" not in a.headline


def test_derived_figures_always_carry_the_estimate_caveat():
    df = _frame()
    a = ask.answer("profitability by month", df, _plan(df),
                   assume=Assumptions(cogs_rate=Decimal("0.5")))
    assert any("not on your books" in c for c in a.caveats)


def test_operating_profit_appears_once_an_opex_rate_is_given():
    df = _frame()
    a = ask.answer("profit by month", df, _plan(df),
                   assume=Assumptions(cogs_rate=Decimal("0.5"),
                                      opex_rate=Decimal("0.2")))
    assert "operating profit" in a.table.columns


def test_profit_ties_to_revenue():
    df = _frame()
    plan = _plan(df)
    rev = ask.compute_revenue(df, plan)
    a = ask.answer("profitability by month", df, plan,
                   assume=Assumptions(cogs_rate=Decimal("0.4")))
    assert abs(float(a.table["revenue"].sum()) - float(rev.adjusted)) < 0.01
    total = a.table["cost of goods"].sum() + a.table["gross profit"].sum()
    assert abs(float(total) - float(rev.adjusted)) < 0.02


def test_a_redraw_keeps_the_assumptions():
    """Replaying the previous question without them lost the cost rate."""
    df = _frame()
    a = ask.answer("make it a line chart", df, _plan(df),
                   previous_question="show profitability by month",
                   assume=Assumptions(cogs_rate=Decimal("0.5")))
    assert a.understood
    assert a.chart == "line"
    assert a.chart_data is not None
