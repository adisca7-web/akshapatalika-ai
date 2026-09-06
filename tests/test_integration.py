"""Router, diagram, and PandasAI-bridge verification."""

from __future__ import annotations

from decimal import Decimal

import pytest

import gaapai
from gaapai import money
from gaapai.adapters import pandasai_bridge as bridge
from gaapai.diagrams import mermaid
from gaapai.router import Router, route
from gaapai.skills import cashflow, leases, ppe, revenue


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "query,expected",
    [
        ("allocate the transaction price across performance obligations",
         "revenue.allocate_transaction_price"),
        ("is this a finance or operating lease?", "leases.classify_lease"),
        ("build the lease amortization schedule", "leases.amortization_schedule"),
        ("compute diluted EPS with our options", "eps.diluted_eps"),
        ("what is our current ratio", "ratios.liquidity"),
        ("run the impairment test on the asset group", "ppe.impairment_test"),
        ("FIFO cost of goods sold", "inventory.cost_flow"),
        ("effective tax rate reconciliation", "tax.effective_tax_rate"),
        ("build the statement of cash flows", "cashflow.indirect_method"),
    ],
)
def test_router_reaches_the_right_subskill(query, expected):
    r = route(query)
    assert r.best is not None, query
    assert r.best.qualified_name == expected, (
        f"{query!r} routed to {r.best.qualified_name}, expected {expected}"
    )


def test_routing_is_stable():
    """The same question must always reach the same subskill."""
    a = route("allocate the transaction price")
    b = route("allocate the transaction price")
    assert [s.qualified_name for s in a.subskills] == \
           [s.qualified_name for s in b.subskills]


def test_router_reports_low_confidence_rather_than_guessing():
    r = route("what do you think about our numbers generally")
    assert not r.confident
    assert "no deterministic subskill" in r.rationale or "weak" in r.rationale


def test_router_detects_asc_topic_numbers():
    r = route("how does ASC 842 classification work")
    assert "842" in r.asc_topics


def test_router_finds_industry_reference_material():
    r = route("how do we amortise film costs")
    files = [ref.get("file", "") for ref in r.references]
    assert any("926" in f for f in files), files


def test_router_finds_industry_by_asc_number():
    router = Router()
    if router.pack_path is None:
        pytest.skip("reference pack not present")
    hits = router.by_asc("985")
    assert any("software" in h.get("file", "").lower() for h in hits)


def test_reference_pack_covers_twenty_industries():
    router = Router()
    if router.pack_path is None:
        pytest.skip("reference pack not present")
    assert len(router.industries()) == 20
    assert len(router.chapters()) == 64


def test_route_explains_itself():
    text = route("classify this lease").explain()
    assert "Deterministic subskills" in text
    assert "842" in text


@pytest.mark.parametrize(
    "query,expected_file",
    [
        ("how do we amortise film costs", "asc926"),
        ("how do not-for-profits report joint activity costs", "asc958"),
        ("when can software development costs be capitalised", "asc985"),
        ("oil and gas successful efforts method", "asc932"),
        ("what is the prematurity period for a cable system", "asc922"),
        ("how does a casino account for chips", "asc924"),
    ],
)
def test_industry_questions_reach_their_industry_file(query, expected_file):
    router = Router()
    if router.pack_path is None:
        pytest.skip("reference pack not present")
    r = router.route(query)
    top = r.references[0]["file"] if r.references else ""
    assert expected_file in top, f"{query!r} -> {top}"


@pytest.mark.parametrize(
    "query",
    [
        "how do we amortise film costs",
        "how do not-for-profits report joint activity costs",
        "when can software development costs be capitalised",
    ],
)
def test_industry_questions_do_not_claim_a_computation(query):
    """A shared token like "cost" must not select an unrelated subskill.

    Before the score floor these routed to inventory.cost_flow, which would have
    answered a film question with an inventory computation.
    """
    r = route(query)
    assert not r.confident, f"{query!r} wrongly confident in {r.best}"


def test_confident_match_pulls_the_matching_chapter():
    """A lease question must reach the leases chapter, not merely a title match."""
    router = Router()
    if router.pack_path is None:
        pytest.skip("reference pack not present")
    r = router.route("is our warehouse lease finance or operating")
    assert r.best.qualified_name == "leases.classify_lease"
    assert "ch57" in r.references[0]["file"]


def test_plural_titles_still_match():
    """The query says "lease"; the chapter is titled "Leases"."""
    router = Router()
    if router.pack_path is None:
        pytest.skip("reference pack not present")
    r = router.route("lease accounting")
    assert any("leases" in ref["file"] for ref in r.references)


def test_trigger_outranks_a_partial_name_match():
    """"statement of cash flows" is a declared trigger; build_statements only
    shares two words with the query."""
    r = route("build the statement of cash flows")
    assert r.best.qualified_name == "cashflow.indirect_method"


# ---------------------------------------------------------------------------
# Diagrams
# ---------------------------------------------------------------------------


def _lease_result(classification="operating"):
    terms = leases.LeaseTerms(
        payment=money("10000"), periods=12,
        annual_discount_rate=Decimal("0.06"), periods_per_year=12,
    )
    return leases.classify_lease(terms), terms


def test_five_step_diagram_renders():
    d = mermaid.five_step_diagram()
    assert d.startswith("flowchart TD")
    assert "606-10-32-31" in d


def test_five_step_diagram_annotates_a_result():
    obligations = [
        revenue.PerformanceObligation("Delivered", money("600"), progress=Decimal(1)),
        revenue.PerformanceObligation("Undelivered", money("400")),
    ]
    r = revenue.five_step_revenue(money("1000"), obligations)
    d = mermaid.five_step_diagram(r)
    assert "Recognised" in d
    assert "600" in d


def test_lease_diagram_highlights_the_outcome():
    terms = leases.LeaseTerms(
        payment=money("10000"), periods=12,
        annual_discount_rate=Decimal("0.06"), transfers_ownership=True,
    )
    r = leases.classify_lease(terms)
    d = mermaid.lease_classification_diagram(r)
    assert "class FIN result" in d


def test_impairment_diagram_shows_the_branch_taken():
    r = ppe.impairment_test(money("1000"), money("1100"), money("800"))
    d = mermaid.impairment_diagram(r)
    assert "class OK result" in d   # recoverable, so no loss

    r2 = ppe.impairment_test(money("1000"), money("900"), money("750"))
    d2 = mermaid.impairment_diagram(r2)
    assert "Loss" in d2


def test_allocation_diagram_lists_every_obligation():
    r = revenue.allocate_transaction_price(
        money("900"),
        [revenue.PerformanceObligation("Licence", money("600")),
         revenue.PerformanceObligation("Support", money("400"))],
    )
    d = mermaid.allocation_diagram(r)
    assert "Licence" in d and "Support" in d
    assert d.startswith("flowchart LR")


def test_cash_flow_diagram_renders():
    r = cashflow.indirect_method(
        net_income=money("100000"),
        adjustments=[cashflow.Adjustment("Depreciation", money("20000"))],
        beginning_cash=money("40000"),
    )
    d = mermaid.cash_flow_diagram(r)
    assert "Operating" in d and "Net change in cash" in d


def test_skill_map_covers_the_registry():
    d = mermaid.skill_map()
    for skill in gaapai.REGISTRY.skills:
        assert skill.title[:12] in d


def test_diagram_labels_are_escaped():
    """Quotes and brackets would break Mermaid parsing."""
    d = mermaid.skill_map()
    for line in d.splitlines():
        if '["' in line:
            label = line.split('["', 1)[1].rsplit('"]', 1)[0]
            assert '"' not in label, line


# ---------------------------------------------------------------------------
# PandasAI bridge
# ---------------------------------------------------------------------------


def test_tool_descriptions_render_without_pandasai():
    """The tool block must be inspectable on any interpreter."""
    block = bridge.tool_descriptions()
    assert "<function>" in block
    assert "allocate_transaction_price" in block
    assert "Authority: ASC 606-10-32-31" in block
    assert "GaapResult" in block


def test_every_subskill_appears_as_a_tool():
    block = bridge.tool_descriptions()
    for sub in gaapai.REGISTRY.subskills():
        assert sub.name in block, sub.qualified_name


def test_wrapped_functions_stay_callable_and_record_evidence():
    fns = bridge.gaap_skill_functions(["ppe"])
    fn = fns["ppe.impairment_test"]
    result = fn(money("1000"), money("900"), money("750"))
    assert result.value["loss"] == money("250")
    assert fn.last_result is result
    assert len(fn.results) == 1


def test_policy_states_the_hard_rules():
    p = bridge.GAAP_POLICY
    assert "NEVER compute" in p
    assert "floating point" in p
    assert "verify_trial_balance" in p


def test_build_agent_fails_clearly_without_pandasai():
    if bridge.available():
        pytest.skip("PandasAI is importable here")
    with pytest.raises(RuntimeError, match=r"3\.12"):
        bridge.build_agent(None)


# ---------------------------------------------------------------------------
# Live PandasAI integration (skipped where PandasAI cannot be installed)
# ---------------------------------------------------------------------------

pandasai_only = pytest.mark.skipif(
    not bridge.available(), reason="PandasAI not importable on this interpreter"
)


@pandasai_only
def test_kernel_skills_register_into_pandasai():
    from pandasai.ee.skills.manager import SkillsManager

    registered = bridge.register_skills()
    names = {s.name for s in SkillsManager.get_skills()}
    assert len(registered) == len(gaapai.REGISTRY.subskills())
    for sub in gaapai.REGISTRY.subskills():
        assert sub.name in names, sub.qualified_name


@pandasai_only
def test_preview_matches_pandasai_byte_for_byte():
    """tool_descriptions() must equal what PandasAI actually injects.

    The preview exists so the prompt can be inspected on an interpreter where
    PandasAI will not install. If the two drift, the preview is worse than
    useless -- it is confidently wrong about what the model sees.
    """
    from pandasai.ee.skills.manager import SkillsManager

    bridge.register_skills()
    real = {s.name: str(s) for s in SkillsManager.get_skills()}
    for sub in gaapai.REGISTRY.subskills():
        assert sub.as_function_block() == real[sub.name], sub.qualified_name


@pandasai_only
def test_agent_carries_policy_and_contract():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({
        "fiscal_year": [2021, 2022],
        "ultimate_revenue": [9, 9],
        "theatrical_revenue": [100, 120],
        "distributor_discounts": [5, 6],
    })
    agent = bridge.build_agent(df, industry="film")
    description = agent._state.memory.agent_description

    assert len(agent._state.skills) == len(gaapai.REGISTRY.subskills())
    for token in ["NEVER compute", "ASC 926", "ultimate_revenue", "FORBIDDEN"]:
        assert token in description, token


@pandasai_only
def test_agent_industry_changes_the_contract():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"fiscal_year": [2021], "written_premium": [1],
                       "earned_premium": [1]})
    film = bridge.build_agent(df, industry="film")._state.memory.agent_description
    ins = bridge.build_agent(df, industry="insurance")._state.memory.agent_description
    assert "ASC 944" in ins and "ASC 944" not in film
    assert "written_premium" in ins
