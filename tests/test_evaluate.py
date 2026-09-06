"""Row-rule evaluation, citation validation, and the entity profile."""

from __future__ import annotations

from decimal import Decimal

import pytest

from gaapai import evaluate, semantics
from gaapai.core import asc
from gaapai.entity import EntityProfile, OPEN_QUESTIONS


# ---------------------------------------------------------------------------
# Blank handling -- the bug that made every permissive rule match every row
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [None, float("nan"), "", "  ", "NaN", "nat",
                                   "None", "null", "<NA>"])
def test_blank_cells_are_recognised_however_spelled(value):
    assert evaluate.is_blank(value)


@pytest.mark.parametrize("value", ["0", 0, "false", "x", "2026-01-01"])
def test_real_values_are_not_blank(value):
    assert not evaluate.is_blank(value)


def test_permissive_rule_does_not_match_empty_cells():
    """A /.+/ rule over an all-empty column must match nothing.

    pandas yields float('nan') for a blank cell and str(nan) is "nan", which a
    permissive pattern happily matches. Before the guard, the cancelled-order
    rule reported every row of a file with no cancellations as excluded.
    """
    rows = [{"Cancelled at": float("nan"), "Lineitem price": "10.00",
             "Lineitem quantity": 1} for _ in range(5)]
    plan = semantics.plan_aggregation(list(rows[0]), industry="retail")
    impacts = evaluate.evaluate_row_rules(rows, plan, include_silent=True)
    cancelled = [i for i in impacts if i.rule.name == "cancelled_orders"]
    assert cancelled, "the cancelled_orders rule should be applicable here"
    assert cancelled[0].row_count == 0


# ---------------------------------------------------------------------------
# Amount parsing and basis
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("1,234.56", Decimal("1234.56")), ("$99.00", Decimal("99.00")),
    ("(50.00)", Decimal("-50.00")), (7, Decimal(7)), ("", None),
    ("abc", None), (True, None),
])
def test_amounts_parse_exactly_or_not_at_all(raw, expected):
    got = evaluate.to_decimal(raw)
    assert got == expected
    if got is not None:
        assert isinstance(got, Decimal)


def test_line_level_basis_beats_order_totals():
    """Order totals repeat across every line; summing them multiplies impact."""
    cols = ["Subtotal", "Lineitem price", "Lineitem quantity"]
    basis = evaluate.choose_amount_basis(cols)
    assert basis.kind == "product"
    assert basis.columns == ["Lineitem price"]
    assert basis.factor_column == "Lineitem quantity"


def test_basis_falls_back_to_bound_revenue_columns():
    cols = ["fiscal_year", "net_revenue"]
    plan = semantics.plan_aggregation(cols)
    basis = evaluate.choose_amount_basis(cols, plan)
    assert basis.kind == "columns"
    assert "net_revenue" in basis.columns


# ---------------------------------------------------------------------------
# Impact and the fail-closed contract
# ---------------------------------------------------------------------------


def _gift_card_rows():
    return [
        {"Lineitem name": "Snowboard", "Lineitem price": "100.00",
         "Lineitem quantity": 1, "Lineitem sku": "SB-1"},
        {"Lineitem name": "Gift Card", "Lineitem price": "50.00",
         "Lineitem quantity": 2, "Lineitem sku": "GC-50"},
    ]


def test_candidate_rules_are_measured_but_not_applied():
    rows = _gift_card_rows()
    plan = semantics.plan_aggregation(list(rows[0]), industry="retail")
    impacts = evaluate.evaluate_row_rules(rows, plan)
    gift = next(i for i in impacts if i.rule.name == "gift_card_sales")
    assert gift.row_count == 1
    assert gift.amount == Decimal("100.00")   # 50.00 x 2
    assert gift.status == evaluate.CANDIDATE
    assert not gift.applied, "an unratified rule must never change a figure"


def test_ratifying_a_rule_makes_it_apply():
    rows = _gift_card_rows()
    plan = semantics.plan_aggregation(list(rows[0]), industry="retail")
    impacts = evaluate.evaluate_row_rules(rows, plan, ratified=["gift_card_sales"])
    gift = next(i for i in impacts if i.rule.name == "gift_card_sales")
    assert gift.status == evaluate.RATIFIED
    assert gift.applied


def test_rejected_rules_stay_unapplied():
    rows = _gift_card_rows()
    plan = semantics.plan_aggregation(list(rows[0]), industry="retail")
    impacts = evaluate.evaluate_row_rules(rows, plan, rejected=["gift_card_sales"])
    gift = next(i for i in impacts if i.rule.name == "gift_card_sales")
    assert gift.status == evaluate.REJECTED
    assert not gift.applied


# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------


def test_every_row_rule_cites_a_catalogued_paragraph():
    """The guard that existed for subskills and was never wired to row rules.

    22 of the shipped rules cited paragraphs that resolved nowhere.
    """
    missing = []
    for code in semantics.industries():
        for rule in semantics.profile_for(code).row_rules:
            ok, detail = evaluate.citation_status(rule.citation)
            if not ok:
                missing.append((code, rule.name, detail))
    assert not missing, missing


def test_unverified_citations_announce_themselves():
    """An unchecked reference must be visibly unchecked, not merely present."""
    unverified = [c for c in asc.all_citations() if not c.verified]
    assert unverified, "the industry references are carried as unverified"
    for c in unverified:
        assert "UNVERIFIED" in str(c)


def test_subskill_citations_are_all_verified():
    """Nothing unverified may back a computation, only a row rule."""
    for sub in __import__("gaapai").REGISTRY.subskills():
        for c in sub.citations:
            assert c.verified, f"{sub.qualified_name} cites unverified {c.key}"


# ---------------------------------------------------------------------------
# Dead rules -- the silent-drop bug
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("code,expected", [
    ("912", {"no_cost_settlements", "termination_claims"}),
    ("960", {"participant_loans"}),
])
def test_reference_only_industries_keep_their_row_rules(code, expected):
    """These three rules were silently dropped and never fired on any query."""
    names = {r.name for r in semantics.profile_for(code).row_rules}
    assert expected <= names


def test_no_row_rule_is_keyed_to_an_unknown_industry():
    orphans = (set(semantics._ROW_RULES)
               - set(semantics.PROFILES) - set(semantics._REFERENCE_ONLY))
    assert not orphans, f"rules keyed to {orphans} can never fire"


# ---------------------------------------------------------------------------
# Entity profile
# ---------------------------------------------------------------------------


def test_profile_round_trips(tmp_path):
    p = EntityProfile(name="Acme Snowboards", industry="retail")
    p.decide("gift_card_sales", "ratified", rows=6, amount="500.00")
    p.save(tmp_path)

    from gaapai import entity as entity_mod
    back = entity_mod.load("Acme Snowboards", tmp_path)
    assert back.industry == "retail"
    assert back.ratified_rules == ["gift_card_sales"]
    assert back.decisions[0].rows_at_decision == 6


def test_a_decision_replaces_the_previous_one():
    p = EntityProfile(name="x")
    p.decide("r", "ratified")
    p.decide("r", "rejected")
    assert p.ratified_rules == []
    assert p.rejected_rules == ["r"]


def test_clearing_returns_a_rule_to_candidate():
    p = EntityProfile(name="x")
    p.decide("r", "ratified")
    p.clear("r")
    assert not p.ratified_rules and not p.rejected_rules


def test_unanswered_questions_are_surfaced_not_defaulted():
    p = EntityProfile(name="x")
    gaps = p.unanswered()
    assert set(gaps) == set(OPEN_QUESTIONS)
    p.control_transfer_column = "Fulfilled at"
    assert "control_transfer_column" not in p.unanswered()


def test_invalid_decision_is_refused():
    with pytest.raises(ValueError):
        EntityProfile(name="x").decide("r", "maybe")
