"""Akshapatalika AI -- books you can question.

Organised around what a preparer actually does, not around the layers of the
system underneath:

    Overview   the number, what changed it, what is still unanswered
    Ask        plain-English questions, answered with a figure and a chart
    Review     decisions only a person can make, in plain language
    Details    the technical view -- bindings, contract, catalog, routing

Every figure is computed by :func:`gaapai.ask.compute_revenue`, so no two
screens can disagree about the same number. No language model is involved:
questions are matched deterministically, which means narrower coverage in
exchange for answers that reproduce and cite their authority.

Run, from the repository root::

    python -m streamlit run devapp/app.py --server.address localhost

On Windows PowerShell chain commands with ``;`` rather than ``&&``,
which is not a valid statement separator there.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gaapai  # noqa: E402
from gaapai import ask as ask_mod  # noqa: E402
from gaapai import charts as charts_mod  # noqa: E402
from gaapai import entity as entity_mod  # noqa: E402
from gaapai import evaluate, semantics  # noqa: E402
from gaapai import llm as llm_mod  # noqa: E402
from gaapai import plan as plan_mod  # noqa: E402
from gaapai.assumptions import Assumptions  # noqa: E402
from gaapai.core import asc  # noqa: E402
from gaapai.diagrams import mermaid  # noqa: E402
from gaapai.router import route  # noqa: E402
from gaapai.semantics import Concept  # noqa: E402

APP = "Akshapatalika AI"

st.set_page_config(page_title=APP, layout="wide", page_icon="\U0001F4D8")

st.markdown("""
<style>
  .block-container {padding-top: 2.2rem; max-width: 1250px;}
  [data-testid="stMetricValue"] {font-size: 2.0rem;}
  .ak-card {border:1px solid rgba(128,128,128,.25); border-radius:10px;
            padding:1rem 1.15rem; margin-bottom:.85rem;}
  .ak-why {font-size:.86rem; opacity:.75; margin-top:.35rem;}
  .ak-quiet {font-size:.86rem; opacity:.7;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def money(v) -> str:
    try:
        return f"{Decimal(str(v)):,.2f}"
    except Exception:
        return str(v)


@st.cache_data(show_spinner=False)
def read_table(raw: bytes, name: str) -> pd.DataFrame:
    from io import BytesIO
    if name.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(BytesIO(raw))
    return pd.read_csv(BytesIO(raw))


def render_mermaid(code: str, height: int = 420) -> None:
    import streamlit.components.v1 as components
    components.html(
        f'<div class="mermaid">{code}</div>'
        '<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js">'
        '</script><script>mermaid.initialize({startOnLoad:true,theme:"neutral"});'
        '</script>',
        height=height, scrolling=True)


def render_chart(kind: str, data) -> None:
    """Draw the chart that was asked for.

    The app previously called ``st.bar_chart`` unconditionally and ignored the
    ``chart`` field entirely, so every request -- line, pie, area -- came back
    as bars.
    """
    if data is None or kind == "table":
        return
    if not charts_mod.is_known(kind):
        st.warning(f"I do not know how to draw a '{kind}' chart. Available: "
                   + ", ".join(charts_mod.chart_names()))
        return
    if kind == "scatter":
        st.scatter_chart(data)
    elif kind == "line":
        st.line_chart(data)
    elif kind == "area":
        st.area_chart(data)
    elif kind == "pie":
        # Streamlit has no pie primitive; matplotlib is already a dependency of
        # the data extra.
        import matplotlib.pyplot as plt
        series = data.iloc[:, 0] if hasattr(data, "iloc") else data
        series = series[series > 0]
        if not len(series):
            st.info("Nothing positive to plot as a pie.")
            return
        fig, ax = plt.subplots(figsize=(5, 5))
        ax.pie(series.values, labels=[str(i) for i in series.index],
               autopct="%1.1f%%", startangle=90,
               textprops={"fontsize": 8})
        ax.axis("equal")
        fig.patch.set_alpha(0)
        st.pyplot(fig, use_container_width=False)
        plt.close(fig)
    else:
        st.bar_chart(data)


def cite_line(key: str) -> str:
    try:
        c = asc.cite(key)
    except KeyError:
        return f"ASC {key} (not in catalog)"
    mark = "" if c.verified else "  \u2014 unverified, confirm before filing"
    return f"ASC {c.key} \u2014 {c.requirement}{mark}"


# ---------------------------------------------------------------------------
# sidebar -- kept to the three things a user must supply
# ---------------------------------------------------------------------------

st.sidebar.markdown(f"### {APP}")
st.sidebar.caption("Books you can question.")

NEW = "\uFF0B  New business\u2026"
saved = entity_mod.list_profiles()
picked = st.sidebar.selectbox("Business", saved + [NEW],
                              index=0 if saved else len(saved))
if picked == NEW:
    business = st.sidebar.text_input("Business name", value="",
                                     placeholder="Acme Snowboards")
else:
    business = picked
business = (business or "").strip() or "My business"

if st.session_state.get("_biz") != business:
    st.session_state.profile = entity_mod.load(business)
    st.session_state._biz = business
profile: entity_mod.EntityProfile = st.session_state.profile

codes = semantics.industries()
names = {c: semantics.profile_for(c).name for c in codes}
cur = profile.industry if profile.industry in codes else "606"
industry = st.sidebar.selectbox(
    "What kind of business?", codes, index=codes.index(cur),
    format_func=lambda c: names[c],
    help="This selects the accounting rules that apply to your revenue.")
profile.industry = industry

st.sidebar.divider()
upload = st.sidebar.file_uploader("Your data", type=["csv", "xlsx", "xls"],
                                  help="A sales, orders, or transactions export.")
path_input = st.sidebar.text_input(
    "\u2026or a file path", value=st.session_state.get("last_path", ""),
    placeholder=r"C:\Users\...\orders.csv",
    help="Press Enter or click away to apply.")

df = None
if upload is not None:
    try:
        df = read_table(upload.getvalue(), upload.name)
    except Exception as exc:
        st.sidebar.error(f"Could not read that file: {exc}")
elif path_input.strip():
    p = Path(path_input.strip().strip('"'))
    if not p.exists():
        st.sidebar.error(f"No such file: {p}")
    else:
        try:
            df = read_table(p.read_bytes(), p.name)
            st.session_state.last_path = str(p)
        except Exception as exc:
            st.sidebar.error(f"Could not read that file: {exc}")

if df is not None:
    st.sidebar.success(f"{len(df):,} rows loaded")

# -- optional AI assistant --------------------------------------------------
#
# The key is held in session memory only. It is deliberately never written to
# the entity profile: profiles are JSON meant to be reviewed and shared, and a
# credential in one would leak the first time somebody committed it.
st.sidebar.divider()
if "llm" not in st.session_state:
    st.session_state.llm = llm_mod.LLMConfig()
cfg: llm_mod.LLMConfig = st.session_state.llm

with st.sidebar.expander(
    "AI assistant" + ("  ✓" if cfg.ready else ""), expanded=False
):
    st.caption(
        "Optional. Without one, questions are answered by the deterministic "
        "engine only — exact, but it understands a fixed set of questions. "
        "A model lets it also explain, compare, and take follow-ups."
    )

    keys = [p.key for p in llm_mod.PROVIDERS]
    labels = {p.key: p.label for p in llm_mod.PROVIDERS}
    cfg.provider = st.selectbox(
        "Provider", keys,
        index=keys.index(cfg.provider) if cfg.provider in keys else 0,
        format_func=lambda k: labels[k])
    spec = cfg.spec
    # Switching provider must drop a model name belonging to the old one --
    # "claude-sonnet-5" left sitting in the box after choosing Ollama would fail
    # at call time with a confusing error rather than at the moment of change.
    if st.session_state.get("_llm_provider") != cfg.provider:
        st.session_state._llm_provider = cfg.provider
        cfg.model = ""
        cfg.base_url = ""
        st.session_state.pop("llm_models", None)
    if spec.hint:
        st.caption(spec.hint)

    cfg.base_url = st.text_input(
        "Endpoint", value=cfg.base_url or spec.base_url,
        placeholder="https://…",
        help="Editable — vendors move paths, and local runners use your own "
             "host and port.")
    if cfg.base_url.rstrip("/") == spec.base_url.rstrip("/"):
        cfg.base_url = ""          # keep following the preset if unchanged

    cfg.api_key = st.text_input(
        "API key" + ("" if spec.needs_key else " (not needed)"),
        value=cfg.api_key, type="password",
        help="Held in memory for this session only. Never written to disk.")

    mcol, bcol = st.columns([3, 1])
    cfg.model = mcol.text_input(
        "Model", value=cfg.model or (spec.suggested_models[0]
                                     if spec.suggested_models else ""),
        placeholder="model name")
    if bcol.button("List", use_container_width=True,
                   help="Ask the endpoint which models it has. Works on "
                        "OpenAI-compatible servers, including local ones."):
        try:
            found = llm_mod.list_models(cfg)
            st.session_state.llm_models = found
            st.success(f"{len(found)} model(s) found.")
        except Exception as exc:
            st.error(str(exc))
    if st.session_state.get("llm_models"):
        picked = st.selectbox("Models reported by the endpoint",
                              [""] + st.session_state.llm_models)
        if picked:
            cfg.model = picked
    if spec.suggested_models:
        st.caption("Suggestions: " + ", ".join(spec.suggested_models))

    if st.button("Test connection", use_container_width=True):
        try:
            with st.spinner("Contacting the model…"):
                st.success(f"Replied: {llm_mod.test_connection(cfg)[:120]}")
        except Exception as exc:
            st.error(str(exc))

    st.caption(":green[Ready.]" if cfg.ready
               else f":orange[{cfg.why_not_ready()}]")
    st.session_state.llm_always = st.checkbox(
        "Use AI even for questions I can answer exactly",
        value=st.session_state.get("llm_always", False),
        help="Off is recommended: exact answers stay reproducible, and the "
             "model is used only for questions the engine would refuse.")


# ---------------------------------------------------------------------------
# no data yet
# ---------------------------------------------------------------------------

if df is None:
    st.title(APP)
    st.subheader("Accounting answers you can defend.")
    st.write(
        "Load a sales or transactions export. Every figure is computed by "
        "deterministic code against US GAAP, with the paragraph it relies on "
        "attached \u2014 and anything requiring your judgement is asked, "
        "never assumed."
    )
    a, b, c = st.columns(3)
    a.markdown("**1. Load your data**\n\nCSV or Excel. Column meanings are "
               "recognised automatically.")
    b.markdown("**2. Review what we found**\n\nGift cards, test orders, "
               "cancellations \u2014 flagged in plain English for your decision.")
    c.markdown("**3. Ask questions**\n\nRevenue by month, what was excluded "
               "and why, refunds, tax.")
    st.divider()
    st.caption(f"Covering {len(semantics.industries())} industry regimes and "
               f"{len(gaapai.REGISTRY.subskills())} deterministic computations.")
    st.stop()


# ---------------------------------------------------------------------------
# shared state
# ---------------------------------------------------------------------------

plan = semantics.plan_aggregation(list(df.columns), industry=industry)
prof = semantics.profile_for(industry)
rows = evaluate.rows_from_frame(df)

impacts_all = evaluate.evaluate_row_rules(
    rows, plan, ratified=profile.ratified_rules,
    rejected=profile.rejected_rules, include_silent=True)
pending = [i for i in impacts_all if i.fires and i.status == "candidate"]

result = None
if not plan.blocked:
    try:
        result = ask_mod.compute_revenue(
            df, plan, ratified=profile.ratified_rules,
            rejected=profile.rejected_rules,
            revenue_column=st.session_state.get("rev_col"),
            period_column=st.session_state.get("per_col"))
    except Exception as exc:                      # pragma: no cover - UI guard
        st.error(f"Could not compute revenue: {exc}")

badge = f"Review ({len(pending)})" if pending else "Review"
tabs = st.tabs(["Overview", "Ask", badge, "Details"])


# -- Overview ---------------------------------------------------------------
with tabs[0]:
    st.header(business)
    st.caption(f"{names[industry]} \u00b7 {len(df):,} rows")

    if plan.blocked:
        st.error(
            "**No revenue column found.** Nothing in this file matched a "
            "revenue concept, and guessing would be worse than stopping. "
            "Open **Details** to see how each column was read."
        )
    elif result is not None:
        c1, c2, c3 = st.columns(3)
        c1.metric("Revenue", money(result.adjusted),
                  help="After the accounting adjustments you have approved.")
        c2.metric("Excluded by rules", money(result.deducted),
                  help="Amounts removed because GAAP does not treat them as revenue.")
        c3.metric("Awaiting your review", money(result.pending),
                  delta=f"{len(pending)} item(s)" if pending else "nothing pending",
                  delta_color="inverse" if pending else "off")

        if pending:
            st.warning(
                f"**{len(pending)} item(s) worth {money(result.pending)} are not "
                "included above.** Nothing is adjusted without your approval. "
                "Open the **Review** tab to decide."
            )

        chart_kind = st.radio(
            "Chart", ["bar", "line", "area"], horizontal=True,
            label_visibility="collapsed", key="overview_chart")
        render_chart(chart_kind, result.by_period[["reported"]].rename(
            columns={"reported": "Revenue"}))

        left, right = st.columns([3, 2])
        with left:
            st.markdown("**By period**")
            show = result.by_period.rename(columns={
                "revenue": "Before adjustments", "excluded": "Excluded",
                "reported": "Revenue"})
            st.dataframe(show.style.format("{:,.2f}"), use_container_width=True)
        with right:
            st.markdown("**How this was calculated**")
            st.markdown(
                f"- Revenue read from **{result.revenue_column}**\n"
                f"- Dated by **{result.period_column or 'n/a'}**"
                + (f", inherited across order **{result.order_column}**"
                   if result.order_column else "")
                + "\n"
                + (f"- Sales tax excluded: {', '.join(result.tax_columns[:3])}\n"
                   if result.tax_columns else "")
                + (f"- Contra-revenue present: {', '.join(result.contra_columns[:3])}\n"
                   if result.contra_columns else "")
            )
            if result.applied:
                st.markdown("**Adjustments applied**")
                for im in result.applied:
                    st.markdown(
                        f"- {ask_mod.friendly_rule_name(im.rule.name)}: "
                        f"\u2212{money(im.amount or 0)}")
                    st.caption(cite_line(im.rule.citation))

        st.divider()
        st.markdown("**What we found in your file**")
        st.caption(
            "The columns carrying accounting meaning, with what is actually in "
            "them. Check these read correctly before trusting the figures above."
        )
        imp = ask_mod.important_columns(df, plan)
        st.dataframe(
            imp.style.format({"total": "{:,.2f}"}, na_rep="—"),
            use_container_width=True, hide_index=True)

        thin = imp[(imp["filled"] > 0) & (imp["filled"] < len(df) * 0.25)]
        for _, row in thin.iterrows():
            st.caption(
                f":orange[**{row['column']}** has a value in only "
                f"{row['filled']} of {len(df)} rows] — too sparse to date or "
                "total the whole file with."
            )

        gaps = profile.unanswered()
        if gaps:
            with st.expander(
                f"\u26A0 {len(gaps)} things we need from you before these figures "
                "are complete", expanded=False
            ):
                st.caption(
                    "These are facts no data file contains. Until they are "
                    "answered, the figures above are correct only to the extent "
                    "these do not matter. Set them on the **Details** tab."
                )
                for k, q in gaps.items():
                    st.markdown(f"- **{k.replace('_', ' ').capitalize()}** \u2014 {q}")


# -- Ask --------------------------------------------------------------------
with tabs[1]:
    st.header("Ask about your books")
    st.caption(
        "Answers are computed from your data with the accounting rules you have "
        "approved. Nothing here is generated by a language model, so the same "
        "question always gives the same answer."
    )

    if "chat" not in st.session_state:
        st.session_state.chat = []
    if "assume" not in st.session_state:
        st.session_state.assume = Assumptions()
    assume: Assumptions = st.session_state.assume

    if assume.any:
        cols = st.columns([5, 1])
        cols[0].info("**Assumptions in force:** " + "; ".join(assume.describe())
                     + ". Figures derived from these are estimates, not your books.")
        if cols[1].button("Clear", use_container_width=True):
            st.session_state.assume = Assumptions()
            st.rerun()

    if not st.session_state.chat:
        st.markdown("**Try one of these**")
        cols = st.columns(2)
        for i, ex in enumerate(ask_mod.EXAMPLE_QUESTIONS):
            if cols[i % 2].button(ex, key=f"ex{i}", use_container_width=True):
                st.session_state.pending_q = ex
                st.rerun()

    for role, content in st.session_state.chat:
        with st.chat_message(role):
            if role == "user":
                st.write(content)
            else:
                st.markdown(content.get("headline", ""))
                if content.get("detail"):
                    st.markdown(content["detail"])
                if content.get("table") is not None:
                    st.dataframe(content["table"], use_container_width=True)
                if content.get("chart_data") is not None:
                    render_chart(content.get("chart") or "bar",
                                 content["chart_data"])
                for cav in content.get("caveats", []):
                    st.warning(cav)
                for key in content.get("citations", []):
                    st.caption(cite_line(key))
                for s in content.get("suggestions", []):
                    st.markdown(f"- {s}")
                if content.get("formulas"):
                    with st.expander("How this was calculated"):
                        for line in content["formulas"]:
                            st.markdown(f"- `{line}`")
                        st.caption(
                            "The assistant chose these formulas; the "
                            "deterministic engine computed every figure from "
                            "your data. Revenue still has your approved "
                            "accounting rules applied.")
                        st.json(content.get("plan", {}), expanded=False)
                if content.get("source") == "planned":
                    st.caption(
                        ":orange[The assistant chose the calculation]; the "
                        "figures were computed by the deterministic engine, "
                        "not written by the model.")
                if content.get("llm"):
                    src = content.get("source")
                    st.markdown("---" if src == "engine+ai" else "")
                    st.markdown(content["llm"])
                    st.caption(
                        ":orange[Written by the AI assistant.] Figures above "
                        "come from the deterministic engine; anything the "
                        "assistant adds beyond them is not independently "
                        "verified — check it before relying on it."
                        if src == "engine+ai" else
                        ":orange[Written by the AI assistant, not the "
                        "deterministic engine.] It was given the computed "
                        "figures and told not to invent numbers or citations, "
                        "but this answer is not reproducible the way an exact "
                        "one is. Verify before relying on it."
                    )

    typed = st.chat_input("e.g. show revenue by month") \
        or st.session_state.pop("pending_q", None)

    if typed:
        a = ask_mod.answer(
            typed, df, plan, ratified=profile.ratified_rules,
            rejected=profile.rejected_rules,
            revenue_column=st.session_state.get("rev_col"),
            period_column=st.session_state.get("per_col"),
            previous_question=st.session_state.get("last_data_question"),
            assume=assume)

        # Assumptions stated in this turn must survive into the next one.
        if a.assumptions is not None:
            st.session_state.assume = a.assumptions
            assume = a.assumptions

        # Remember the last question that produced figures, so a bare "as a
        # line chart" has something to redraw.
        if (a.understood and a.chart_data is not None
                and not ask_mod.chart_only(typed)):
            st.session_state.last_data_question = typed

        # Deterministic first. The model is reached only when the engine
        # refuses, or when the user has explicitly opted into using it
        # everywhere -- so an exactly-answerable question stays reproducible.
        use_llm = cfg.ready and (
            not a.understood or st.session_state.get("llm_always"))
        payload = {
            "headline": f"### {a.headline}" if a.headline else "",
            "detail": a.detail, "table": a.table, "chart_data": a.chart_data,
            "chart": a.chart,
            "citations": a.citations, "caveats": a.caveats,
            "suggestions": a.suggestions, "source": "engine",
        }
        if use_llm:
            try:
                with st.spinner("Thinking…"):
                    ctx = llm_mod.build_context(
                        business=business, industry_name=names[industry],
                        industry_asc=prof.asc, df=df, plan=plan, result=result,
                        impacts=[i for i in impacts_all if i.fires],
                        unanswered=profile.unanswered(),
                        assumptions=assume.describe() if assume.any else None,
                        citations={c.key: c.requirement
                                   for c in asc.all_citations()
                                   if c.topic_number in ("606", "810", "330",
                                                         "842", "230")},
                    )
                    history = []
                    for role, content in st.session_state.chat[-8:]:
                        text = (content if role == "user"
                                else (content.get("llm")
                                      or content.get("headline", "")))
                        if text:
                            history.append({"role": role,
                                            "content": str(text)[:2000]})
                    if a.understood:
                        reply = llm_mod.ask_llm(typed, ctx, cfg, history=history)
                        emitted = None
                    else:
                        emitted, reply = llm_mod.ask_planner(
                            typed, ctx, cfg, history=history)
                if emitted is not None:
                    # The model chose the calculation; the engine performs it,
                    # so the figures are as reproducible as any other answer.
                    pr = plan_mod.execute(
                        emitted, df, plan,
                        ratified=profile.ratified_rules,
                        rejected=profile.rejected_rules,
                        revenue_column=st.session_state.get("rev_col"),
                        period_column=st.session_state.get("per_col"))
                    head = emitted.title or "Result"
                    if pr.scalar is not None:
                        head = f"{money(pr.scalar)} — {head}"
                    payload = {
                        "headline": f"### {head}",
                        "detail": emitted.notes,
                        "table": pr.table, "chart_data": pr.chart_data,
                        "chart": pr.chart, "citations": pr.citations,
                        "caveats": pr.caveats, "suggestions": [],
                        "plan": emitted.to_dict(),
                        "formulas": pr.steps_shown, "source": "planned",
                    }
                elif a.understood:
                    # Keep the exact answer; add the explanation beneath it.
                    payload["llm"] = reply
                    payload["source"] = "engine+ai"
                else:
                    payload = {"headline": "", "detail": "", "table": None,
                               "chart_data": None, "chart": "", "citations": [],
                               "caveats": [], "suggestions": [],
                               "llm": reply, "source": "ai"}
            except Exception as exc:
                payload["caveats"] = list(payload["caveats"]) + [
                    f"The AI assistant could not be reached: {exc}"]

        st.session_state.chat.append(("user", typed))
        st.session_state.chat.append(("assistant", payload))
        st.rerun()

    if st.session_state.chat and st.button("Clear conversation"):
        st.session_state.chat = []
        st.rerun()


# -- Review -----------------------------------------------------------------
with tabs[2]:
    st.header("Items needing your decision")
    st.caption(
        "We can spot these in your data, but whether they belong in revenue is "
        "your call as the preparer. Nothing is changed until you decide."
    )

    firing = [i for i in impacts_all if i.fires]
    if not firing:
        st.success("Nothing in this file needs a decision.")
    for im in firing:
        with st.container(border=True):
            top, side = st.columns([3, 1])
            with top:
                state = {"candidate": ":orange[Needs your decision]",
                         "ratified": ":green[Excluded from revenue]",
                         "rejected": ":gray[Kept in revenue]"}[im.status]
                st.markdown(
                    f"**{ask_mod.friendly_rule_name(im.rule.name)}** \u00b7 {state}")
                st.write(im.rule.requirement)
                st.caption("Why: " + cite_line(im.rule.citation))
                st.caption(
                    f"Found by looking in *{', '.join(im.trigger_columns)}*."
                )
            with side:
                st.metric("Amount", money(im.amount or 0))
                st.caption(f"{im.row_count} line(s)")

            b1, b2, b3 = st.columns(3)
            if b1.button("Exclude from revenue", key=f"r{im.rule.name}",
                         disabled=im.status == "ratified",
                         use_container_width=True, type="primary"):
                profile.decide(im.rule.name, "ratified", rows=im.row_count,
                               amount=str(im.amount))
                entity_mod.save(profile)
                st.rerun()
            if b2.button("Keep in revenue", key=f"x{im.rule.name}",
                         disabled=im.status == "rejected",
                         use_container_width=True):
                profile.decide(im.rule.name, "rejected", rows=im.row_count,
                               amount=str(im.amount))
                entity_mod.save(profile)
                st.rerun()
            if b3.button("Undo", key=f"c{im.rule.name}",
                         disabled=im.status == "candidate",
                         use_container_width=True):
                profile.clear(im.rule.name)
                entity_mod.save(profile)
                st.rerun()

            with st.expander("Show the lines this affects"):
                if im.samples:
                    st.dataframe(pd.DataFrame(im.samples),
                                 use_container_width=True)
                st.caption(f"Matching rule: `/{im.rule.match_value}/`")

    silent = [i for i in impacts_all if not i.fires]
    if silent:
        with st.expander(f"{len(silent)} check(s) that found nothing"):
            st.caption("These rules apply to your industry but matched no rows "
                       "in this file.")
            for im in silent:
                st.markdown(f"- {ask_mod.friendly_rule_name(im.rule.name)}")


# -- Details ----------------------------------------------------------------
with tabs[3]:
    st.header("Details")

    sub = st.tabs(["Your settings", "How columns were read", "Check a question",
                   "What this system knows"])

    with sub[0]:
        st.caption(
            "Facts no data file contains. Set once; they carry into every answer."
        )
        cols = list(df.columns)
        c1, c2 = st.columns(2)
        with c1:
            opts = [""] + cols
            profile.control_transfer_column = st.selectbox(
                "Which date should count as the sale?", opts,
                index=opts.index(profile.control_transfer_column)
                if profile.control_transfer_column in cols else 0,
                help=entity_mod.OPEN_QUESTIONS["control_transfer_column"])
            fc = ["", "calendar", "4-5-4", "52-53 week", "other"]
            profile.fiscal_calendar = st.selectbox(
                "Financial calendar", fc,
                index=fc.index(profile.fiscal_calendar)
                if profile.fiscal_calendar in fc else 0,
                help=entity_mod.OPEN_QUESTIONS["fiscal_calendar"])
            stp = ["", "excluded (net)", "included (gross)"]
            profile.sales_tax_presentation = st.selectbox(
                "Sales tax treatment", stp,
                index=stp.index(profile.sales_tax_presentation)
                if profile.sales_tax_presentation in stp else 0,
                help=entity_mod.OPEN_QUESTIONS["sales_tax_presentation"])
        with c2:
            ror = st.selectbox(
                "Can customers return goods?", ["not answered", "yes", "no"],
                index=0 if profile.right_of_return is None
                else (1 if profile.right_of_return else 2),
                help=entity_mod.OPEN_QUESTIONS["right_of_return"])
            profile.right_of_return = None if ror == "not answered" else (ror == "yes")
            w = st.number_input("Return window (days)", 0, 365,
                                value=profile.return_window_days or 0,
                                help=entity_mod.OPEN_QUESTIONS["return_window_days"])
            profile.return_window_days = int(w) or None
            profile.intercompany_flag = st.selectbox(
                "Column marking intercompany sales", [""] + cols,
                index=([""] + cols).index(profile.intercompany_flag)
                if profile.intercompany_flag in cols else 0,
                help=entity_mod.OPEN_QUESTIONS["intercompany_flag"])

        st.divider()
        r1, r2 = st.columns(2)
        gross = (plan.columns_for(Concept.GROSS_REVENUE)
                 or plan.columns_for(Concept.NET_REVENUE))
        if gross:
            st.session_state.rev_col = r1.selectbox(
                "Revenue column", gross,
                index=gross.index(st.session_state.get("rev_col"))
                if st.session_state.get("rev_col") in gross else 0)
        periods = plan.columns_for(Concept.PERIOD) or cols
        st.session_state.per_col = r2.selectbox(
            "Date column", periods,
            index=periods.index(st.session_state.get("per_col"))
            if st.session_state.get("per_col") in periods else 0)

        profile.notes = st.text_area("Notes", value=profile.notes)
        if st.button("Save settings", type="primary"):
            st.success(f"Saved to {entity_mod.save(profile)}")

        if profile.decisions:
            st.markdown("**Decision history**")
            st.dataframe(pd.DataFrame([{
                "item": ask_mod.friendly_rule_name(d.rule_name),
                "decision": d.decision, "lines": d.rows_at_decision,
                "amount": d.amount_at_decision, "when": d.decided_at,
            } for d in profile.decisions]), use_container_width=True)

    with sub[1]:
        st.caption("Each column matched to an accounting meaning. Columns marked "
                   "*forbidden* are never summed as revenue in this industry.")
        st.dataframe(pd.DataFrame([{
            "column": b.column, "read as": b.concept,
            "confidence": b.confidence, "why": b.rationale}
            for b in plan.bindings]), use_container_width=True, height=430)
        m1, m2, m3 = st.columns(3)
        m1.metric("Revenue columns", len(plan.columns_for(Concept.GROSS_REVENUE))
                  + len(plan.columns_for(Concept.NET_REVENUE)))
        m2.metric("Never revenue", len(plan.columns_for(Concept.FORBIDDEN)))
        m3.metric("Unrecognised", len(plan.unknown_columns))
        with st.expander("The instructions given to the query layer"):
            st.code(plan.render(), language="text")
        with st.expander("Preview the data"):
            st.dataframe(df.head(50), use_container_width=True)

    with sub[2]:
        st.caption("Check which deterministic computation a question reaches. "
                   "A weak match refuses rather than guessing.")
        rq = st.text_input("Question", placeholder="is this a finance or operating lease?")
        if rq:
            r = route(rq)
            if r.confident and r.best is not None:
                st.success(f"Routed to **{r.best.qualified_name}**")
            elif r.best is not None:
                st.warning(f"Closest match **{r.best.qualified_name}**, but "
                           "confidence is low \u2014 refusing to claim it.")
            else:
                st.error("No deterministic computation matched.")
            st.code(r.explain(), language="text")
            if r.best is not None and r.best.judgement:
                st.warning("This computation depends on your judgement; it will "
                           "ask for your determination rather than infer it.")

    with sub[3]:
        c1, c2, c3, c4 = st.columns(4)
        cits = asc.all_citations()
        unver = [c for c in cits if not c.verified]
        c1.metric("Topics", len(gaapai.REGISTRY.skills))
        c2.metric("Computations", len(gaapai.REGISTRY.subskills()))
        c3.metric("Citations", len(cits))
        c4.metric("Unverified", len(unver), delta="confirm before filing",
                  delta_color="inverse")
        if unver:
            with st.expander(f"{len(unver)} citations not yet checked against "
                             "the Codification"):
                st.dataframe(pd.DataFrame([c.to_dict() for c in unver]),
                             use_container_width=True)
        render_mermaid(mermaid.skill_map(), height=500)
        with st.expander("Full catalog"):
            st.code(gaapai.REGISTRY.catalog(), language="text")
