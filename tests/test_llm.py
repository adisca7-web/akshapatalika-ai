"""The optional model layer: provider neutral, and never trusted with a number."""

from __future__ import annotations

import pytest

from gaapai import llm

# ---------------------------------------------------------------------------
# Readiness
# ---------------------------------------------------------------------------


def test_a_hosted_provider_is_not_ready_without_a_key():
    cfg = llm.LLMConfig(provider="openai")
    assert not cfg.ready
    assert "API key" in cfg.why_not_ready()


def test_a_local_provider_is_ready_without_a_key():
    """Requiring a key would lock out exactly the setup that needs no account."""
    cfg = llm.LLMConfig(provider="ollama", model="llama3.1")
    assert cfg.ready, cfg.why_not_ready()


def test_readiness_needs_a_model_name():
    cfg = llm.LLMConfig(provider="lmstudio")     # no suggested models
    assert not cfg.ready
    assert "model" in cfg.why_not_ready().lower()


def test_a_custom_endpoint_must_be_supplied():
    cfg = llm.LLMConfig(provider="custom", model="whatever")
    assert not cfg.ready
    assert "endpoint" in cfg.why_not_ready().lower()
    cfg.base_url = "http://localhost:8000/v1"
    assert cfg.ready


def test_asking_when_not_configured_raises_rather_than_proceeding():
    with pytest.raises(RuntimeError):
        llm.ask_llm("hello", "context", llm.LLMConfig(provider="openai"))


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


def test_every_provider_declares_a_known_transport():
    for p in llm.PROVIDERS:
        assert p.transport in ("openai", "anthropic", "gemini"), p.key


@pytest.mark.parametrize("key", ["anthropic", "openai", "gemini", "deepseek",
                                 "ollama", "lmstudio", "custom"])
def test_the_providers_asked_for_are_present(key):
    assert llm.provider_for(key).key == key


def test_local_providers_need_no_key_and_point_at_localhost():
    for key in ("ollama", "lmstudio"):
        p = llm.provider_for(key)
        assert not p.needs_key
        assert "localhost" in p.base_url


def test_an_unknown_provider_falls_back_rather_than_raising():
    assert llm.provider_for("nonesuch") is llm.PROVIDERS[0]


def test_base_url_override_wins_over_the_preset():
    cfg = llm.LLMConfig(provider="openai", base_url="http://gateway.internal/v1")
    assert cfg.endpoint == "http://gateway.internal/v1"


def test_a_trailing_slash_does_not_double_up():
    cfg = llm.LLMConfig(provider="openai", base_url="http://x/v1/")
    assert cfg.endpoint == "http://x/v1"


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------


def test_the_system_prompt_forbids_inventing_figures_and_citations():
    p = llm.SYSTEM_PROMPT
    assert "NEVER compute" in p
    assert "NEVER invent an ASC citation" in p
    assert "Judgements belong to the preparer" in p


def test_context_carries_computed_figures_not_raw_rows():
    """The model explains a computed result; it must not redo the arithmetic."""
    pd = pytest.importorskip("pandas")
    from gaapai import ask, semantics

    df = pd.DataFrame({
        "Name": ["#1"], "Paid at": ["2026-06-01 10:00:00 -0400"],
        "Subtotal": [300.0], "Lineitem name": ["Snowboard"],
        "Lineitem price": [300.0], "Lineitem quantity": [1],
    })
    plan = semantics.plan_aggregation(list(df.columns), industry="retail")
    result = ask.compute_revenue(df, plan)
    ctx = llm.build_context(
        business="Acme", industry_name="Retail", industry_asc="606",
        df=df, plan=plan, result=result,
        citations={"606-10-32-2A": "Amounts collected for third parties are excluded."},
        unanswered={"right_of_return": "Do customers have a right of return?"})

    assert "300.00" in ctx
    assert "already computed" in ctx
    assert "cite no others" in ctx
    assert "do not assume these" in ctx
    assert "Snowboard" not in ctx, "raw row values must not be handed over"


def test_no_vendor_sdk_is_required():
    """Calls go over stdlib HTTP so a local model works with no dependencies."""
    import inspect
    src = inspect.getsource(llm)
    assert "urllib" in src
    for sdk in ("import anthropic", "import openai", "google.generativeai"):
        assert sdk not in src, f"{sdk} would add a dependency"
