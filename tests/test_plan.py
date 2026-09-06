"""Query plans: the model writes the formula, the engine computes it."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gaapai import charts, plan as plan_mod
from gaapai.plan import PlanError

pd = pytest.importorskip("pandas")

from gaapai import semantics  # noqa: E402


def _frame():
    return pd.DataFrame({
        "Name": ["#1", "#2", "#3"],
        "Paid at": ["2026-06-01 10:00:00 -0400", "2026-06-20 10:00:00 -0400",
                    "2026-07-02 11:00:00 -0400"],
        "Subtotal": [300.00, 100.00, 200.00],
        "Taxes": [30.00, 10.00, 20.00],
        "Lineitem name": ["Snowboard", "Boots", "Bindings"],
        "Lineitem price": [300.00, 100.00, 200.00],
        "Lineitem quantity": [1, 1, 1],
    })


def _plan(df):
    return semantics.plan_aggregation(list(df.columns), industry="retail")


# ---------------------------------------------------------------------------
# Safety -- a plan is data the model wrote; it must not be able to escape
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("expr", [
    "__import__('os').system('echo hi')",
    "open('x')",
    "r.__class__",
    "r.values[0]",
    "eval('1+1')",
    "[x for x in range(3)]",
    "r + 'text'",
])
def test_a_formula_cannot_escape_arithmetic(expr):
    body = {"steps": [{"id": "r", "op": "revenue"},
                      {"id": "a", "op": "formula", "expr": expr}],
            "output": {"kind": "table"}}
    with pytest.raises(PlanError):
        plan_mod.parse_plan(body)


def test_a_formula_may_only_reference_earlier_steps():
    body = {"steps": [{"id": "a", "op": "formula", "expr": "b * 2"},
                      {"id": "b", "op": "revenue"}],
            "output": {"kind": "table"}}
    with pytest.raises(PlanError, match="not an earlier step"):
        plan_mod.parse_plan(body)


def test_division_by_zero_is_reported_not_raised_raw():
    with pytest.raises(PlanError, match="divides by zero"):
        plan_mod.eval_formula("a / 0", {"a": Decimal(1)})


@pytest.mark.parametrize("body,match", [
    ({"steps": [{"id": "a", "op": "sql"}], "output": {"kind": "table"}},
     "unknown operation"),
    ({"steps": [{"id": "a", "op": "metric", "concept": "profit"}],
      "output": {"kind": "table"}}, "unknown concept"),
    ({"steps": [{"id": "a", "op": "revenue", "by": "fortnight"}],
      "output": {"kind": "table"}}, "unknown grouping"),
    ({"steps": [{"id": "a", "op": "revenue"}],
      "output": {"kind": "chart", "chart": "sankey"}}, "unknown chart type"),
    ({"steps": [{"id": "a", "op": "revenue"}],
      "output": {"kind": "table", "table": ["zz"]}}, "does not exist"),
    ({"steps": [{"id": "a", "op": "revenue"}, {"id": "a", "op": "revenue"}],
      "output": {"kind": "table"}}, "used twice"),
    ({"steps": [], "output": {"kind": "table"}}, "no steps"),
])
def test_an_invalid_plan_is_rejected_before_anything_runs(body, match):
    with pytest.raises(PlanError, match=match):
        plan_mod.parse_plan(body)


def test_malformed_json_is_reported_clearly():
    with pytest.raises(PlanError, match="not valid JSON"):
        plan_mod.parse_plan("{not json")


# ---------------------------------------------------------------------------
# Extraction from a model reply
# ---------------------------------------------------------------------------


def test_a_plan_is_pulled_out_of_a_fenced_block():
    reply = ('Here is the calculation.\n\n```json\n'
             '{"steps":[{"id":"r","op":"revenue","by":"month"}],'
             '"output":{"kind":"table","table":["r"]}}\n```\n')
    p = plan_mod.extract_plan(reply)
    assert p is not None
    assert p.steps[0].op == "revenue"


def test_prose_without_a_plan_returns_none_rather_than_raising():
    """The planner is told to answer in prose when no calculation applies."""
    assert plan_mod.extract_plan("ASC 606 is the revenue standard.") is None


def test_an_invalid_embedded_plan_is_ignored_not_half_run():
    reply = '```json\n{"steps":[{"id":"a","op":"rm -rf"}],"output":{}}\n```'
    assert plan_mod.extract_plan(reply) is None


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def test_the_engine_computes_the_formula_the_model_wrote():
    df = _frame()
    p = plan_mod.parse_plan({
        "title": "Profitability",
        "steps": [{"id": "rev", "op": "revenue", "by": "month", "label": "Revenue"},
                  {"id": "cost", "op": "formula", "expr": "rev * 0.5",
                   "label": "Cost"},
                  {"id": "gp", "op": "formula", "expr": "rev - cost",
                   "label": "Gross profit"}],
        "output": {"kind": "chart", "chart": "line", "series": ["rev", "gp"],
                   "table": ["rev", "cost", "gp"]}})
    res = plan_mod.execute(p, df, _plan(df))
    assert list(res.table.columns) == ["Revenue", "Cost", "Gross profit"]
    assert float(res.table["Revenue"].sum()) == 600.0
    assert float(res.table["Gross profit"].sum()) == 300.0
    assert res.chart == "line"
    assert list(res.chart_data.columns) == ["Revenue", "Gross profit"]


def test_a_metric_lines_up_with_revenue_period_for_period():
    df = _frame()
    p = plan_mod.parse_plan({
        "steps": [{"id": "rev", "op": "revenue", "by": "month"},
                  {"id": "tax", "op": "metric", "concept": "tax_collected",
                   "by": "month"},
                  {"id": "pct", "op": "formula", "expr": "tax / rev * 100"}],
        "output": {"kind": "table", "table": ["rev", "tax", "pct"]}})
    res = plan_mod.execute(p, df, _plan(df))
    assert len(res.table) == 2                      # June and July
    assert float(res.table["tax"].sum()) == 60.0
    assert round(float(res.table["pct"].iloc[0]), 1) == 10.0


def test_a_scalar_only_plan_returns_a_number():
    df = _frame()
    p = plan_mod.parse_plan({
        "steps": [{"id": "n", "op": "count", "of": "orders"}],
        "output": {"kind": "number", "table": ["n"]}})
    res = plan_mod.execute(p, df, _plan(df))
    assert res.scalar == Decimal(3)


def test_revenue_in_a_plan_still_applies_approved_rules():
    """A plan must not be a way around the accounting layer."""
    df = _frame()
    df.loc[3] = ["#4", "2026-07-05 10:00:00 -0400", 50.0, 0.0,
                 "Gift Card", 50.0, 1]
    p = plan_mod.parse_plan({
        "steps": [{"id": "rev", "op": "revenue", "by": "none"}],
        "output": {"kind": "number", "table": ["rev"]}})
    plain = plan_mod.execute(p, df, _plan(df))
    ruled = plan_mod.execute(p, df, _plan(df), ratified=["gift_card_sales"])
    assert plain.scalar - ruled.scalar == Decimal("50.00")
    assert ruled.citations, "the rule's authority must travel with the figure"


def test_pending_items_are_reported_in_a_planned_answer_too():
    df = _frame()
    df.loc[3] = ["#4", "2026-07-05 10:00:00 -0400", 50.0, 0.0,
                 "Gift Card", 50.0, 1]
    p = plan_mod.parse_plan({
        "steps": [{"id": "rev", "op": "revenue", "by": "month"}],
        "output": {"kind": "table", "table": ["rev"]}})
    res = plan_mod.execute(p, df, _plan(df))
    assert any("waiting for your decision" in c for c in res.caveats)


def test_a_missing_column_is_refused_rather_than_zeroed():
    df = _frame().drop(columns=["Taxes"])
    p = plan_mod.parse_plan({
        "steps": [{"id": "t", "op": "metric", "concept": "tax_collected"}],
        "output": {"kind": "number", "table": ["t"]}})
    with pytest.raises(PlanError, match="no column bound to"):
        plan_mod.execute(p, df, _plan(df))


def test_a_pie_of_several_series_is_trimmed_and_flagged():
    df = _frame()
    p = plan_mod.parse_plan({
        "steps": [{"id": "rev", "op": "revenue", "by": "month"},
                  {"id": "half", "op": "formula", "expr": "rev * 0.5"}],
        "output": {"kind": "chart", "chart": "pie",
                   "series": ["rev", "half"], "table": ["rev", "half"]}})
    res = plan_mod.execute(p, df, _plan(df))
    assert res.chart_data.shape[1] == 1
    assert any("one series" in c for c in res.caveats)


# ---------------------------------------------------------------------------
# The chart registry -- how a new kind is added
# ---------------------------------------------------------------------------


def test_a_new_chart_kind_reaches_the_parser_and_the_prompt():
    """Adding one registry entry must be enough; nothing else hard-codes kinds."""
    from gaapai import ask
    kind = charts.ChartKind("waterfall", "Bridges one total to another.",
                            aliases=["waterfall", "bridge chart"])
    charts.CHARTS[kind.name] = kind
    try:
        assert ask.detect_chart("show me a waterfall chart") == "waterfall"
        assert charts.is_known("waterfall")
        assert "waterfall" in charts.describe_for_model()
        from gaapai import llm
        assert "waterfall" in llm.planner_prompt()
        p = plan_mod.parse_plan({
            "steps": [{"id": "r", "op": "revenue", "by": "month"}],
            "output": {"kind": "chart", "chart": "waterfall", "series": ["r"]}})
        assert p.output.chart == "waterfall"
    finally:
        del charts.CHARTS["waterfall"]


def test_an_unregistered_chart_is_rejected_not_drawn_as_bars():
    with pytest.raises(PlanError, match="unknown chart type"):
        plan_mod.parse_plan({
            "steps": [{"id": "r", "op": "revenue"}],
            "output": {"kind": "chart", "chart": "treemap", "series": ["r"]}})


def test_the_planner_prompt_lists_every_op_and_chart():
    from gaapai import llm
    prompt = llm.planner_prompt()
    for op in plan_mod.OPS:
        assert f'"{op}"' in prompt, op
    for name in charts.chart_names():
        assert f'"{name}"' in prompt, name
