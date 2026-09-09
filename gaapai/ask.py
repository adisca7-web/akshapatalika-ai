"""Answer plain-English accounting questions against a data set.

This is the layer that was missing. Routing a question to a subskill tells you
which *computation* is relevant; it does not read the data, apply the row rules,
or produce a number. So "what is my revenue for the period" reached a router,
found no exact subskill, and returned nothing useful -- while the gift-card and
test-order rules sat unapplied in a different tab.

Everything here is deterministic. No language model is involved: intents are
matched by pattern and answered by the same code path the rest of the layer
uses, so a question cannot produce a figure that disagrees with the Revenue
screen. That is a deliberate trade -- narrower coverage in exchange for an
answer that is reproducible and carries its authority.

An unrecognised question says so plainly and offers what it *can* answer,
rather than guessing at intent. Same fail-closed rule as everywhere else.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, List, Optional, Tuple

from . import charts
from .assumptions import Assumptions, is_assumption_statement, parse_assumptions
from .evaluate import (
    RuleImpact,
    choose_amount_basis,
    evaluate_row_rules,
    rows_from_frame,
)
from .semantics import AggregationPlan, Concept

__all__ = [
    "CHART_KINDS",
    "EXAMPLE_QUESTIONS",
    "Answer",
    "Assumptions",
    "RevenueResult",
    "answer",
    "chart_only",
    "column_profile",
    "compute_revenue",
    "detect_chart",
    "friendly_rule_name",
    "important_columns",
    "profitability",
    "sum_without_double_counting",
]


EXAMPLE_QUESTIONS = [
    "What is my revenue?",
    "Show revenue by month",
    "What did you exclude and why?",
    "How much was refunded?",
    "How much sales tax did I collect?",
    "What are my top products?",
    "How many orders did I have?",
    "What is my average order value?",
    "Cost of goods is 50% of revenue",
    "Show profitability by month",
]


def friendly_rule_name(name: str) -> str:
    """`gift_card_sales` -> `Gift card sales`. Accountants do not read snake_case."""
    return name.replace("_", " ").capitalize()


# ---------------------------------------------------------------------------
# Chart type
# ---------------------------------------------------------------------------

# Chart kinds live in gaapai.charts so the parser, the planner prompt, the
# validator and the renderer all read one declaration. They used to be spelled
# out separately in each, and adding a kind meant finding all four.
CHART_KINDS = tuple(charts.chart_names())


def detect_chart(question: str) -> str:
    """The chart type named in a question, or "" when none is."""
    return charts.detect(question)


# Words that make a message a *data* question rather than a request to redraw
# what is already on screen.
#
# Plurals matter here. Written as \\bproduct\\b this failed to match "products",
# so "top products as a line chart" was classified as a bare redraw request and
# answered by re-plotting whatever came before it.
_DATA_WORDS = re.compile(
    r"\b(revenues?|sales|turnover|income|refunds?|returns?|tax(es)?|vat|gst|"
    r"gift|orders?|products?|items?|customers?|excludes?|excluded|adjusts?|"
    r"months?|quarters?|years?|weeks?|totals?|averages?|aov|profits?|margins?|"
    r"how much|how many|what is|what are)\b"
)


def chart_only(question: str) -> bool:
    """True for "make it a line graph" -- a redraw of the previous answer.

    A chart type on its own is a follow-up, not a new question. Without this it
    matched no intent and was refused, which is why "I want a line graph" came
    back as "I can't answer that one from this data."
    """
    q = (question or "").lower()
    if not detect_chart(q):
        return False
    # "show revenue by month as a line chart" is a data question that happens to
    # name a chart type; "as a line chart" on its own is not.
    stripped = q
    for kind in charts.CHARTS.values():
        stripped = re.sub(kind.pattern, " ", stripped)
    return not _DATA_WORDS.search(stripped)


# ---------------------------------------------------------------------------
# Shared revenue computation
# ---------------------------------------------------------------------------


@dataclass
class RevenueResult:
    """One revenue figure, its adjustments, and everything needed to defend it."""

    unadjusted: Decimal
    adjusted: Decimal
    by_period: Any                      # DataFrame indexed by period label
    applied: List[RuleImpact] = field(default_factory=list)
    candidates: List[RuleImpact] = field(default_factory=list)
    revenue_column: str = ""
    period_column: str = ""
    order_column: str = ""
    basis_note: str = ""
    tax_columns: List[str] = field(default_factory=list)
    contra_columns: List[str] = field(default_factory=list)

    @property
    def deducted(self) -> Decimal:
        return self.unadjusted - self.adjusted

    @property
    def pending(self) -> Decimal:
        """Money that candidate rules would move if they were accepted."""
        total = Decimal(0)
        for im in self.candidates:
            if im.amount is not None:
                total += im.amount
        return total


_ORDER_PAT = re.compile(r"(?i)^(name|order[ _]?(id|name|number)|order|invoice[ _]?(no|number))$")


def _order_column(columns) -> str:
    for c in columns:
        if _ORDER_PAT.match(str(c)):
            return str(c)
    return ""


_GRAIN = {"month": "M", "quarter": "Q", "year": "Y", "week": "W", "day": "D"}


def compute_revenue(
    df: Any,
    plan: AggregationPlan,
    *,
    ratified: List[str] = (),
    rejected: List[str] = (),
    revenue_column: Optional[str] = None,
    period_column: Optional[str] = None,
    granularity: str = "month",
) -> RevenueResult:
    """Revenue with ratified row rules applied, and candidates reported separately.

    The one place revenue is computed. Every screen and every answer calls this,
    so two parts of the app cannot show different totals for the same question.
    """
    import pandas as pd

    gross = plan.columns_for(Concept.GROSS_REVENUE) or \
        plan.columns_for(Concept.NET_REVENUE)
    if not gross:
        raise ValueError("no column is bound to revenue in this schema")

    rev_col = revenue_column or gross[0]
    periods = plan.columns_for(Concept.PERIOD)
    per_col = period_column or (periods[0] if periods else "")

    rows = rows_from_frame(df)
    basis = choose_amount_basis(list(df.columns), plan)
    impacts = evaluate_row_rules(rows, plan, ratified=ratified, rejected=rejected)
    applied = [im for im in impacts if im.applied]
    candidates = [im for im in impacts if im.status == "candidate" and im.fires]

    work = df.copy()
    work["_amount"] = pd.to_numeric(work[rev_col], errors="coerce")

    order_col = _order_column(df.columns)
    if per_col:
        dt = pd.to_datetime(work[per_col], errors="coerce", utc=True)
        # An order's date sits on its first line only; continuation lines are
        # blank. Without this the deduction for a gift-card line lands outside
        # every period instead of in the month the order belongs to.
        if order_col:
            dt = dt.groupby(work[order_col]).transform(lambda s: s.ffill().bfill())
        code = _GRAIN.get(granularity, "M")
        work["_period"] = dt.dt.tz_localize(None).dt.to_period(code).astype(str)
    else:
        work["_period"] = "all"

    # A ratified rule deducts the LINE amount it measured, not the whole row:
    # the revenue column is order-level and dropping the row would remove the
    # order's entire total.
    excluded = set()
    for im in applied:
        excluded.update(im.row_indices)
    deduction = pd.Series(0.0, index=work.index)
    for i in excluded:
        amt = basis.amount_for(rows[i])
        if amt is not None:
            deduction.iloc[i] = float(amt)
    work["_deduction"] = deduction

    grouped = pd.DataFrame({
        "revenue": work.groupby("_period")["_amount"].sum(min_count=1)
    }).fillna(0.0)
    grouped["excluded"] = work.groupby("_period")["_deduction"].sum(
        min_count=1).reindex(grouped.index).fillna(0.0)
    grouped["reported"] = grouped["revenue"] - grouped["excluded"]

    unadj = Decimal(str(round(float(grouped["revenue"].sum()), 2)))
    adj = Decimal(str(round(float(grouped["reported"].sum()), 2)))

    return RevenueResult(
        unadjusted=unadj, adjusted=adj, by_period=grouped,
        applied=applied, candidates=candidates,
        revenue_column=rev_col, period_column=per_col, order_column=order_col,
        basis_note=basis.describe(),
        tax_columns=plan.columns_for(Concept.TAX_COLLECTED),
        contra_columns=plan.columns_for(Concept.CONTRA_REVENUE),
    )


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------


@dataclass
class Answer:
    """A reply: the number, the plain explanation, and the evidence behind it."""

    headline: str = ""
    detail: str = ""
    table: Any = None
    chart: str = ""                     # "bar" | "line" | ""
    chart_data: Any = None
    citations: List[str] = field(default_factory=list)
    caveats: List[str] = field(default_factory=list)
    understood: bool = True
    suggestions: List[str] = field(default_factory=list)
    # Assumptions in force for this answer, so the caller can carry them into
    # the next turn instead of losing them the moment the message is handled.
    assumptions: Optional[Assumptions] = None
    assumption_changes: List[str] = field(default_factory=list)


def _money(d) -> str:
    return f"{Decimal(str(d)):,.2f}"


_AMOUNT_CONCEPTS = (
    Concept.GROSS_REVENUE, Concept.NET_REVENUE, Concept.CONTRA_REVENUE,
    Concept.TAX_COLLECTED, Concept.SHIPPING_REVENUE, Concept.DEFERRED_REVENUE,
    Concept.COST_OF_REVENUE, Concept.OPERATING_EXPENSE, Concept.RECEIVABLE,
    Concept.FORBIDDEN,
)

# Read order: money first, then the columns that slice it, then everything the
# layer could not place. A reviewer checking whether the file was understood
# looks at the amounts first.
_PROFILE_ORDER = _AMOUNT_CONCEPTS + (
    Concept.PERIOD, Concept.ENTITY, Concept.SEGMENT, Concept.CURRENCY,
    Concept.LABEL, Concept.UNKNOWN,
)


def column_profile(df: Any, plan: AggregationPlan) -> Any:
    """What each meaningful column was read as, with its actual total.

    Naming a column without showing what is in it proves nothing. A schema
    listing "Taxes -> tax_collected" looks right whether the column holds
    1,961.54 or nothing at all, so the total and the fill rate are the part
    worth showing.
    """
    import pandas as pd

    by_col = {b.column: b for b in plan.bindings}
    rank = {c: i for i, c in enumerate(_PROFILE_ORDER)}
    out = []
    for col, b in by_col.items():
        series = df[col]
        filled = int(series.notna().sum())
        total, sample = None, ""
        if b.concept in _AMOUNT_CONCEPTS:
            num = pd.to_numeric(series, errors="coerce")
            if num.notna().any():
                total = round(float(num.sum()), 2)
                filled = int(num.notna().sum())
        if not filled:
            sample = ""
        else:
            vals = series.dropna()
            sample = str(vals.iloc[0])[:40] if len(vals) else ""
        out.append({
            "column": col,
            "read as": b.concept,
            "total": total,
            "filled": filled,
            "of rows": len(df),
            "example": sample,
            "_rank": rank.get(b.concept, 99),
        })
    prof = pd.DataFrame(out).sort_values(
        ["_rank", "column"]).drop(columns="_rank").reset_index(drop=True)
    return prof


def important_columns(df: Any, plan: AggregationPlan) -> Any:
    """The profile trimmed to columns that carry accounting meaning and data."""
    prof = column_profile(df, plan)
    keep = prof["read as"].isin(_AMOUNT_CONCEPTS + (Concept.PERIOD,))
    return prof[keep & (prof["filled"] > 0)].reset_index(drop=True)


def sum_without_double_counting(df: Any, cols: List[str]) -> Tuple[Decimal, str]:
    """Sum columns, using the aggregate alone when one is the total of the rest.

    Exports frequently carry both a total and its components -- ``Taxes``
    alongside ``Tax 1 Value``..``Tax 5 Value``. Summing every column bound to
    the concept then doubles the figure: the sales tax on this file came out at
    3,923.08 against a true 1,961.54, and nothing about the number looked wrong.

    Detected rather than hard-coded: a column whose per-row value equals the sum
    of the others *is* the total, whatever it happens to be named.
    """
    import pandas as pd

    if not cols:
        return Decimal(0), "no columns"
    num = df[cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    use, note = list(cols), ""
    if len(cols) > 1:
        for c in cols:
            others = [x for x in cols if x != c]
            if (num[c] - num[others].sum(axis=1)).abs().max() < 0.01:
                use = [c]
                note = (f"{c} is the total of {', '.join(others)}; "
                        "the components are not added again")
                break
    total = float(num[use].sum().sum())
    return Decimal(str(round(total, 2))), note


def _period_filter(question: str, grouped) -> Tuple[Any, str]:
    """Narrow a per-period table to a month or year named in the question."""
    months = {"january": "01", "february": "02", "march": "03", "april": "04",
              "may": "05", "june": "06", "july": "07", "august": "08",
              "september": "09", "october": "10", "november": "11",
              "december": "12"}
    q = question.lower()
    year = None
    m = re.search(r"\b(20\d{2})\b", q)
    if m:
        year = m.group(1)
    month = next((v for k, v in months.items() if k in q), None)

    if month:
        pat = f"{year}-{month}" if year else f"-{month}"
        hit = grouped[grouped.index.astype(str).str.contains(pat, regex=False)]
        if len(hit):
            label = str(hit.index[0])
            return hit, label
    if year:
        hit = grouped[grouped.index.astype(str).str.startswith(year)]
        if len(hit):
            return hit, year
    return grouped, ""


def _adjustment_lines(result: RevenueResult) -> List[str]:
    out = []
    for im in result.applied:
        out.append(
            f"- **{friendly_rule_name(im.rule.name)}** -- removed "
            f"{_money(im.amount or 0)} across {im.row_count} line(s). "
            f"{im.rule.requirement} (ASC {im.rule.citation})"
        )
    return out


def answer(
    question: str,
    df: Any,
    plan: AggregationPlan,
    *,
    ratified: List[str] = (),
    rejected: List[str] = (),
    revenue_column: Optional[str] = None,
    period_column: Optional[str] = None,
    previous_question: Optional[str] = None,
    assume: Optional[Assumptions] = None,
) -> Answer:
    """Answer a plain-English question deterministically, or say it cannot.

    ``previous_question`` lets a bare "as a line chart" redraw the last answer
    instead of being refused for matching no intent. ``assume`` carries the
    working hypotheses the user has stated earlier in the conversation.
    """
    import pandas as pd

    q = (question or "").strip().lower()
    if not q:
        return Answer(understood=False, headline="Ask me something.",
                      suggestions=EXAMPLE_QUESTIONS)

    # Assumptions stated in *this* message apply to it, not just to later ones.
    assume, stated_now = parse_assumptions(question, assume or Assumptions())

    # -- a bare statement supplies an assumption and asks nothing --------
    if is_assumption_statement(question):
        return Answer(
            headline="Noted.",
            detail="I have recorded: " + "; ".join(stated_now) + ".\n\n"
                   "This is your assumption, not something in your books — I "
                   "will say so on any figure derived from it. Ask for "
                   "**profitability by month** and I will apply it.",
            assumptions=assume, assumption_changes=stated_now,
            suggestions=["Show profitability by month",
                         "Gross profit by month as a line chart"],
        )

    # -- a chart type on its own redraws the previous answer -------------
    wanted_chart = detect_chart(q)
    if chart_only(q):
        if not previous_question:
            return Answer(
                understood=False,
                headline="Which figures should I chart?",
                detail="Ask for the numbers first and I will draw them however "
                       "you like — for example:",
                suggestions=["Show revenue by month",
                             "Revenue by month as a line chart",
                             "What are my top products?"],
            )
        # Carry the assumptions into the replay. Without them a profitability
        # question re-run for a redraw loses its cost rate and reports that it
        # has nothing to chart.
        prior = answer(previous_question, df, plan, ratified=ratified,
                       rejected=rejected, revenue_column=revenue_column,
                       period_column=period_column, assume=assume)
        if prior.chart_data is None:
            return Answer(
                understood=False,
                headline="There is nothing on screen to redraw.",
                detail="The previous answer had no chartable figures.",
                suggestions=EXAMPLE_QUESTIONS)
        prior.chart = wanted_chart
        prior.detail = (prior.detail + "\n\n_Redrawn as a "
                        f"{wanted_chart} chart._").strip()
        prior.caveats = list(prior.caveats) + _chart_caveats(wanted_chart)
        return prior

    def revenue():
        return compute_revenue(
            df, plan, ratified=list(ratified), rejected=list(rejected),
            revenue_column=revenue_column, period_column=period_column,
            granularity=("quarter" if "quarter" in q else
                         "year" if ("year" in q and "by year" in q) else "month"),
        )

    has = lambda *words: any(w in q for w in words)  # noqa: E731

    # -- forecasts are refused outright ---------------------------------
    #
    # "What will revenue be next quarter" was being answered with the historical
    # total -- a real number attached to the wrong question, which is worse than
    # no answer. Nothing here projects, and the layer does not pretend to.
    if re.search(r"\b(will|next|forecast|predict|projection|projected|"
                 r"estimate for|going to)\b", q) and not has("what did", "why"):
        return Answer(
            understood=False,
            headline="I don't forecast.",
            detail="I report what your data says under the accounting rules, "
                   "with the paragraph each figure relies on. Projecting future "
                   "periods is a different exercise and I would only be "
                   "guessing. Ask about a period you have data for:",
            suggestions=EXAMPLE_QUESTIONS,
        )

    # -- what was excluded, and why -------------------------------------
    if has("exclude", "excluded", "adjust", "adjustment", "why is", "why are",
           "what did you remove", "removed", "difference"):
        r = revenue()
        lines = _adjustment_lines(r)
        if not lines and not r.candidates:
            return Answer(
                headline="Nothing has been excluded.",
                detail="No accounting rules are currently applied to this data. "
                       "Check the Review screen -- there may be items waiting "
                       "for your decision.",
            )
        detail = ""
        if lines:
            detail += "**Applied:**\n" + "\n".join(lines) + "\n\n"
        if r.candidates:
            detail += "**Waiting for your decision** (not applied):\n" + "\n".join(
                f"- **{friendly_rule_name(im.rule.name)}** -- would remove "
                f"{_money(im.amount or 0)} across {im.row_count} line(s). "
                f"{im.rule.requirement} (ASC {im.rule.citation})"
                for im in r.candidates)
        return Answer(
            headline=f"{_money(r.deducted)} excluded from "
                     f"{_money(r.unadjusted)}.",
            detail=detail,
            citations=[im.rule.citation for im in r.applied + r.candidates],
        )

    # -- profitability --------------------------------------------------
    if has("profit", "profitability", "margin", "gross profit", "bottom line",
           "how much do i make", "earnings"):
        r = revenue()
        if assume.cogs_rate is None:
            return Answer(
                understood=False,
                headline="I need a cost figure before I can show profit.",
                detail="Your file has revenue but no cost of sales column, so "
                       "profit cannot be computed from it. Tell me the cost "
                       "assumption and I will apply it — for example *cost of "
                       "goods is 50% of revenue*, or *gross margin is 40%*.\n\n"
                       "A real cost of sales comes from inventory records under "
                       "ASC 330; anything derived from a percentage is an "
                       "estimate and I will label it as one.",
                assumptions=assume,
                suggestions=["Cost of goods is 50% of revenue",
                             "Gross margin is 40%",
                             "Show revenue by month"],
            )
        table = profitability(r, assume)
        total_rev = Decimal(str(round(float(table["revenue"].sum()), 2)))
        total_profit = Decimal(str(round(float(table["gross profit"].sum()), 2)))
        margin = (total_profit / total_rev * 100) if total_rev else Decimal(0)
        cols = ["revenue", "cost of goods", "gross profit"]
        if "operating profit" in table.columns:
            cols.append("operating profit")
        return Answer(
            headline=f"{_money(total_profit)} gross profit "
                     f"({margin:.1f}% margin)",
            detail=(f"On {_money(total_rev)} of reported revenue, with "
                    + "; ".join(assume.describe()) + "."
                    + (f" {_money(r.deducted)} was excluded from revenue by "
                       f"{len(r.applied)} accounting rule(s) before this "
                       "calculation." if r.applied else "")),
            table=table,
            chart=wanted_chart or "bar",
            chart_data=table[cols],
            citations=[im.rule.citation for im in r.applied],
            caveats=[assume.caveat()] + _caveats(r) + _chart_caveats(wanted_chart),
            assumptions=assume, assumption_changes=stated_now,
        )

    # -- revenue by period ----------------------------------------------
    #
    # Guarded against more specific intents that share a word. "How much sales
    # tax did I collect" contains "sales" and was answering with total revenue
    # -- a wrong answer delivered confidently, which is the failure this whole
    # layer exists to avoid.
    _more_specific = (
        re.search(r"\b(sales\s+tax|vat|gst)\b", q)
        or has("refund", "return", "chargeback", "gift card", "gift cards",
               "voucher", "breakage")
    )
    if has("revenue", "sales", "turnover", "income", "made", "earn") \
            and not _more_specific:
        r = revenue()
        by_period = r.by_period

        if has("by month", "each month", "monthly", "per month", "by quarter",
               "quarterly", "by year", "trend", "over time", "chart", "graph",
               "breakdown", "compare"):
            return Answer(
                headline=f"{_money(r.adjusted)} total",
                detail=(f"Measured on **{r.revenue_column}**"
                        + (f", dated by **{r.period_column}**" if r.period_column else "")
                        + (f". {_money(r.deducted)} was excluded by "
                           f"{len(r.applied)} accounting rule(s)."
                           if r.applied else ".")),
                table=by_period,
                chart=wanted_chart or "bar",
                chart_data=by_period[["reported"]],
                citations=[im.rule.citation for im in r.applied],
                caveats=_caveats(r) + _chart_caveats(wanted_chart),
            )

        subset, label = _period_filter(question, by_period)
        if label:
            total = Decimal(str(round(float(subset["reported"].sum()), 2)))
            removed = Decimal(str(round(float(subset["excluded"].sum()), 2)))
            return Answer(
                headline=f"{_money(total)} for {label}",
                detail=(f"Before adjustments: {_money(subset['revenue'].sum())}. "
                        f"Excluded by accounting rules: {_money(removed)}."),
                table=subset, chart=wanted_chart,
                chart_data=subset[["reported"]] if wanted_chart else None,
                citations=[im.rule.citation for im in r.applied],
                caveats=_caveats(r),
            )

        return Answer(
            headline=f"{_money(r.adjusted)}",
            detail=(f"Total revenue across the whole file, measured on "
                    f"**{r.revenue_column}**."
                    + (f" {_money(r.deducted)} was excluded by "
                       f"{len(r.applied)} accounting rule(s); ask *what did you "
                       f"exclude* for the detail." if r.applied else "")),
            table=by_period, chart=wanted_chart or "bar",
            chart_data=by_period[["reported"]],
            citations=[im.rule.citation for im in r.applied],
            caveats=_caveats(r), assumptions=assume,
        )

    # -- refunds and returns --------------------------------------------
    if has("refund", "return", "chargeback", "credit note"):
        cols = plan.columns_for(Concept.CONTRA_REVENUE)
        refund_cols = [c for c in cols if re.search(r"(?i)refund|return", str(c))]
        use = refund_cols or cols
        if not use:
            return Answer(headline="No refund or return column found.",
                          detail="Nothing in this file is bound to contra-revenue.")
        total, note = sum_without_double_counting(df, use)
        return Answer(
            headline=f"{_money(total)} refunded",
            detail=f"Summed from {', '.join(use)}. Refunds reduce the "
                   f"transaction price; they are not an expense."
                   + (f"\n\n_{note}._" if note else ""),
            citations=["606-10-32-2"],
            caveats=["This counts refunds already taken. ASC 606-10-32-10 also "
                     "requires a liability for returns you EXPECT but have not "
                     "yet received -- that needs your return policy, which is "
                     "not in this file."],
        )

    # -- sales tax -------------------------------------------------------
    if has("tax", "vat", "gst"):
        cols = plan.columns_for(Concept.TAX_COLLECTED)
        if not cols:
            return Answer(headline="No tax column found in this file.")
        total, note = sum_without_double_counting(df, cols)
        # Show what each column actually holds. Listing the names alone said
        # nothing about where the figure came from.
        num = df[cols].apply(pd.to_numeric, errors="coerce")
        counted = ([c for c in cols if note.startswith(c + " ")] if note else cols)
        breakdown = pd.DataFrame({
            "tax column": cols,
            "amount": [round(float(num[c].sum()), 2) for c in cols],
            "rows with a value": [int(num[c].notna().sum()) for c in cols],
            "counted": ["yes" if c in counted else "no (part of the total above)"
                        for c in cols],
        })
        return Answer(
            headline=f"{_money(total)} collected",
            detail="Sales tax is collected on behalf of the taxing authority. "
                   "It is a liability you owe them, not revenue, and it is "
                   "excluded from the figures above."
                   + (f"\n\n_{note}._" if note else ""),
            citations=["606-10-32-2A"],
            table=breakdown,
        )

    # -- gift cards ------------------------------------------------------
    if has("gift card", "gift cards", "voucher", "breakage"):
        r = revenue()
        gift = [im for im in r.applied + r.candidates if "gift" in im.rule.name]
        if not gift:
            return Answer(headline="No gift card activity detected.")
        im = gift[0]
        state = "excluded" if im.applied else "NOT yet excluded (awaiting your decision)"
        return Answer(
            headline=f"{_money(im.amount or 0)} of gift cards -- {state}",
            detail="A gift card sale is not revenue. You have taken cash but "
                   "owe the customer goods, so it is a contract liability until "
                   "redeemed. Revenue arises on redemption; unredeemed value "
                   "becomes breakage income under ASC 606-10-55-46.",
            citations=[im.rule.citation],
        )

    # -- order counts and average order value ----------------------------
    if has("how many order", "order count", "number of order", "orders did",
           "average order", "aov", "order value"):
        order_col = _order_column(df.columns)
        if not order_col:
            return Answer(headline="No order identifier column found.")
        n = int(df[order_col].nunique())
        r = revenue()
        aov = r.adjusted / Decimal(n) if n else Decimal(0)
        if has("average order", "aov", "order value"):
            return Answer(
                headline=f"{_money(round(aov, 2))} average order value",
                detail=f"{_money(r.adjusted)} of revenue across {n:,} orders, "
                       f"counted on **{order_col}**.")
        return Answer(headline=f"{n:,} orders",
                      detail=f"Distinct values of **{order_col}**. The file has "
                             f"{len(df):,} rows, because an order with several "
                             f"line items uses one row per line.")

    # -- top products / customers ----------------------------------------
    if has("top product", "best selling", "best-selling", "top item",
           "top customer", "best customer", "who bought"):
        by_customer = has("customer", "who bought")
        pat = (r"(?i)(email|customer|billing[ _]?name)" if by_customer
               else r"(?i)(lineitem[ _]?name|item[ _]?name|product|sku)")
        key = next((c for c in df.columns if re.search(pat, str(c))), None)
        if key is None:
            return Answer(headline="No suitable grouping column found.")
        basis = choose_amount_basis(list(df.columns), plan)
        rows = rows_from_frame(df)
        amounts = [float(basis.amount_for(r_) or 0) for r_ in rows]
        tmp = pd.DataFrame({"key": df[key].astype(str), "amount": amounts})
        top = (tmp[tmp["key"].str.lower() != "nan"]
               .groupby("key")["amount"].sum().sort_values(ascending=False).head(10))
        return Answer(
            headline=f"Top {'customers' if by_customer else 'products'} "
                     f"by {'spend' if by_customer else 'line value'}",
            detail=f"Grouped on **{key}**, measured on `{basis.describe()}`. "
                   "Note this is line-level value before the accounting "
                   "adjustments applied to total revenue.",
            table=top.to_frame("amount"), chart=wanted_chart or "bar",
            chart_data=top.to_frame("amount"),
        )

    # -- unrecognised -----------------------------------------------------
    return Answer(
        understood=False,
        headline="I can't answer that one from this data.",
        detail="I only answer questions I can compute deterministically and "
               "cite. Rather than guess at what you meant, here is what I can "
               "do with this file:",
        suggestions=EXAMPLE_QUESTIONS,
    )


def profitability(result: "RevenueResult", assume: Assumptions) -> Any:
    """Revenue, cost, gross profit and margin by period, from a stated cost rate.

    Deliberately computed here rather than by the model. The rate is the user's
    judgement; the arithmetic on top of it is not, and a figure a model produced
    by multiplying in prose cannot be tied back to anything.
    """
    import pandas as pd

    if assume.cogs_rate is None:
        raise ValueError("no cost rate has been supplied")
    rate = float(assume.cogs_rate)
    out = pd.DataFrame({"revenue": result.by_period["reported"]})
    out["cost of goods"] = (out["revenue"] * rate).round(2)
    out["gross profit"] = (out["revenue"] - out["cost of goods"]).round(2)
    if assume.opex_rate is not None:
        out["operating expenses"] = (out["revenue"] * float(assume.opex_rate)).round(2)
        out["operating profit"] = (
            out["gross profit"] - out["operating expenses"]).round(2)
    out["margin %"] = (
        (out["gross profit"] / out["revenue"].where(out["revenue"] != 0)) * 100
    ).round(1)
    return out


def _chart_caveats(kind: str, series_count: int = 1) -> List[str]:
    """Say when a requested chart misrepresents the data. Draw it anyway."""
    return charts.caveat_for(kind, series_count, over_time=True)


def _caveats(r: RevenueResult) -> List[str]:
    out = []
    if r.candidates:
        out.append(
            f"{len(r.candidates)} accounting item(s) worth {_money(r.pending)} "
            "are waiting for your decision on the Review screen and are NOT "
            "reflected above."
        )
    if r.tax_columns:
        out.append(
            f"Sales tax ({', '.join(r.tax_columns[:3])}"
            f"{'...' if len(r.tax_columns) > 3 else ''}) is excluded from "
            "revenue -- it is money owed to the tax authority (ASC 606-10-32-2A)."
        )
    return out
