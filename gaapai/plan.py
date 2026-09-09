"""Query plans: the model writes the formula, the engine computes it.

The division of labour this whole system rests on is that a language model is
good at working out *what* to calculate and untrustworthy at actually
calculating it. Prose asking it not to do arithmetic only gets you a refusal;
what it needs is somewhere to send the work.

A :class:`QueryPlan` is that somewhere. The model emits JSON describing steps:

    {"steps": [{"id": "rev",  "op": "revenue", "by": "month"},
               {"id": "cost", "op": "formula", "expr": "rev * 0.5"},
               {"id": "gp",   "op": "formula", "expr": "rev - cost"}],
     "output": {"kind": "chart", "chart": "line",
                "series": ["rev", "gp"], "table": ["rev", "cost", "gp"]}}

and this module executes it against the vetted primitives. The model never
sees a row, never emits a number, and never chooses a total; it chooses a
*shape*, and every figure still comes from the same ``compute_revenue`` the
rest of the app uses.

Two properties make that safe:

**Formulas are evaluated, not executed.** ``expr`` is parsed to an AST and
walked against a whitelist -- arithmetic, a handful of functions, and
references to earlier steps. There is no attribute access, no indexing, no
calls to anything unlisted, so a plan cannot reach the filesystem or the
interpreter regardless of what the model emits.

**Validation happens before execution.** An unknown op, an unknown concept, an
unknown chart kind, a forward reference -- each is rejected with a message
naming the problem, rather than being partially run and reported as a figure.
Same fail-closed rule as everywhere else.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from . import charts
from .semantics import Concept

__all__ = [
    "OPS",
    "Output",
    "PlanError",
    "PlanResult",
    "QueryPlan",
    "Step",
    "describe_for_model",
    "execute",
    "extract_plan",
    "parse_plan",
]


class PlanError(ValueError):
    """A plan that cannot be run, with a reason a person can act on."""


# ---------------------------------------------------------------------------
# The primitives a plan may call
# ---------------------------------------------------------------------------

# concept name accepted in a plan -> semantic concept it aggregates
METRIC_CONCEPTS = {
    "tax_collected": Concept.TAX_COLLECTED,
    "contra_revenue": Concept.CONTRA_REVENUE,
    "shipping_revenue": Concept.SHIPPING_REVENUE,
    "deferred_revenue": Concept.DEFERRED_REVENUE,
    "cost_of_revenue": Concept.COST_OF_REVENUE,
    "receivable": Concept.RECEIVABLE,
    "operating_expense": Concept.OPERATING_EXPENSE,
}

GRAINS = ("month", "quarter", "year", "none")

OPS = {
    "revenue": "Reported revenue with your approved accounting rules applied. "
               "Params: by (month|quarter|year|none).",
    "metric": "Total of a bound concept. Params: concept "
              f"({'|'.join(METRIC_CONCEPTS)}), by (month|quarter|year|none).",
    "count": "A count. Params: of (orders|rows), by (month|quarter|year|none).",
    "top": "Largest contributors. Params: dimension (product|customer), n (int).",
    "formula": "Arithmetic over earlier steps. Params: expr, e.g. "
               "\"rev - cost\" or \"gp / rev * 100\". Operators + - * / ** and "
               "the functions abs, min, max, round.",
    "constant": "A fixed number the user supplied. Params: value.",
}


def describe_for_model() -> str:
    """The op menu for the planning prompt, generated from :data:`OPS`."""
    return "\n".join(f'  "{name}" -- {text}' for name, text in OPS.items())


# ---------------------------------------------------------------------------
# Safe formula evaluation
# ---------------------------------------------------------------------------

_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Call,
    ast.Constant, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub,
    ast.UAdd, ast.Mod,
)
_ALLOWED_FUNCS = {"abs", "min", "max", "round"}
_ID = re.compile(r"^[a-z_][a-z0-9_]*$")


def _check_expr(node: ast.AST, known: set) -> None:
    """Walk the AST and reject anything outside the whitelist."""
    for child in ast.walk(node):
        if not isinstance(child, _ALLOWED_NODES):
            raise PlanError(
                f"formula uses {type(child).__name__}, which is not allowed. "
                "Only arithmetic over earlier steps is permitted.")
        if isinstance(child, ast.Call):
            if not isinstance(child.func, ast.Name) or \
                    child.func.id not in _ALLOWED_FUNCS:
                raise PlanError(
                    "formula calls a function that is not allowed. Permitted: "
                    + ", ".join(sorted(_ALLOWED_FUNCS)))
        if isinstance(child, ast.Name) and child.id not in known \
                and child.id not in _ALLOWED_FUNCS:
            raise PlanError(
                f"formula refers to '{child.id}', which is not an earlier "
                f"step. Available: {', '.join(sorted(known)) or '(none)'}")
        if isinstance(child, ast.Constant) and not isinstance(
                child.value, (int, float)):
            raise PlanError("formula may only contain numbers.")


def eval_formula(expr: str, values: Dict[str, Any]) -> Any:
    """Evaluate ``expr`` over previously computed steps."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise PlanError(f"formula {expr!r} is not valid arithmetic: {exc.msg}") from None
    _check_expr(tree, set(values))
    env = {name: values[name] for name in values}
    env.update({"abs": abs, "min": min, "max": max, "round": round})
    try:
        return eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}}, env)
    except ZeroDivisionError:
        raise PlanError("formula divides by zero.") from None
    except Exception as exc:
        raise PlanError(f"formula {expr!r} could not be computed: {exc}") from None


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass
class Step:
    id: str
    op: str
    params: Dict[str, Any] = field(default_factory=dict)
    label: str = ""

    @property
    def title(self) -> str:
        return self.label or self.id


@dataclass
class Output:
    kind: str = "table"                    # "number" | "table" | "chart"
    chart: str = ""
    series: List[str] = field(default_factory=list)
    table: List[str] = field(default_factory=list)
    format: str = "money"                  # "money" | "percent" | "number"


@dataclass
class QueryPlan:
    title: str = ""
    steps: List[Step] = field(default_factory=list)
    output: Output = field(default_factory=Output)
    notes: str = ""

    def validate(self) -> None:
        """Reject a plan that cannot run, naming the reason."""
        if not self.steps:
            raise PlanError("the plan has no steps.")
        seen: set = set()
        for step in self.steps:
            if not _ID.match(step.id or ""):
                raise PlanError(
                    f"step id {step.id!r} must be lower-case letters, digits "
                    "and underscores.")
            if step.id in seen:
                raise PlanError(f"step id {step.id!r} is used twice.")
            if step.op not in OPS:
                raise PlanError(
                    f"unknown operation {step.op!r}. Available: "
                    + ", ".join(OPS))
            if step.op == "metric":
                concept = step.params.get("concept")
                if concept not in METRIC_CONCEPTS:
                    raise PlanError(
                        f"unknown concept {concept!r}. Available: "
                        + ", ".join(METRIC_CONCEPTS))
            if step.op in ("revenue", "metric", "count"):
                by = step.params.get("by", "none")
                if by not in GRAINS:
                    raise PlanError(
                        f"unknown grouping {by!r}. Available: " + ", ".join(GRAINS))
            if step.op == "formula":
                expr = step.params.get("expr")
                if not expr:
                    raise PlanError(f"step {step.id!r} has no formula.")
                _check_expr(ast.parse(str(expr), mode="eval"), set(seen))
            if step.op == "constant" and step.params.get("value") is None:
                raise PlanError(f"step {step.id!r} has no value.")
            seen.add(step.id)

        if self.output.kind not in ("number", "table", "chart"):
            raise PlanError(f"unknown output kind {self.output.kind!r}.")
        if self.output.kind == "chart":
            if not charts.is_known(self.output.chart):
                raise PlanError(
                    f"unknown chart type {self.output.chart!r}. Available: "
                    + ", ".join(charts.chart_names()))
        for ref in list(self.output.series) + list(self.output.table):
            if ref not in seen:
                raise PlanError(
                    f"output refers to step {ref!r}, which does not exist.")

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "steps": [{"id": s.id, "op": s.op, "label": s.label, **s.params}
                      for s in self.steps],
            "output": {"kind": self.output.kind, "chart": self.output.chart,
                       "series": self.output.series, "table": self.output.table,
                       "format": self.output.format},
            "notes": self.notes,
        }


def parse_plan(data: Any) -> QueryPlan:
    """Build a plan from decoded JSON (or a JSON string), and validate it."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as exc:
            raise PlanError(f"the plan is not valid JSON: {exc.msg}") from None
    if not isinstance(data, dict):
        raise PlanError("the plan must be a JSON object.")

    steps = []
    for raw in data.get("steps") or []:
        if not isinstance(raw, dict):
            raise PlanError("each step must be a JSON object.")
        params = {k: v for k, v in raw.items()
                  if k not in ("id", "op", "label")}
        steps.append(Step(id=str(raw.get("id", "")), op=str(raw.get("op", "")),
                          params=params, label=str(raw.get("label", ""))))

    out_raw = data.get("output") or {}
    output = Output(
        kind=str(out_raw.get("kind", "table")),
        chart=str(out_raw.get("chart", "") or ""),
        series=[str(x) for x in (out_raw.get("series") or [])],
        table=[str(x) for x in (out_raw.get("table") or [])],
        format=str(out_raw.get("format", "money")),
    )
    plan = QueryPlan(title=str(data.get("title", "")), steps=steps,
                     output=output, notes=str(data.get("notes", "")))
    plan.validate()
    return plan


_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.S)


def extract_plan(text: str) -> Optional[QueryPlan]:
    """Pull a plan out of a model reply, or None when it did not emit one.

    Returning None rather than raising lets the caller fall back to treating
    the reply as prose, which is the right behaviour for a question that needs
    an explanation rather than a calculation.
    """
    if not text:
        return None
    candidates: List[str] = [m.group(1) for m in _FENCE.finditer(text)]
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        candidates.append(stripped)
    for blob in candidates:
        try:
            return parse_plan(blob)
        except PlanError:
            continue
    return None


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


@dataclass
class PlanResult:
    plan: QueryPlan
    table: Any = None                      # DataFrame, or None
    scalar: Optional[Decimal] = None
    chart: str = ""
    chart_data: Any = None
    caveats: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    steps_shown: List[str] = field(default_factory=list)


def _series_or_scalar(values: Any) -> Tuple[Any, bool]:
    import pandas as pd
    return values, isinstance(values, pd.Series)


def execute(
    plan: QueryPlan,
    df: Any,
    aggregation_plan: Any,
    *,
    ratified: List[str] = (),
    rejected: List[str] = (),
    revenue_column: Optional[str] = None,
    period_column: Optional[str] = None,
) -> PlanResult:
    """Run a validated plan against the data using the vetted primitives."""
    import pandas as pd

    from . import ask as ask_mod

    plan.validate()
    values: Dict[str, Any] = {}
    labels: Dict[str, str] = {}
    caveats: List[str] = []
    citations: List[str] = []
    index = None

    def revenue_for(by: str):
        nonlocal index, caveats, citations
        r = ask_mod.compute_revenue(
            df, aggregation_plan, ratified=list(ratified),
            rejected=list(rejected), revenue_column=revenue_column,
            period_column=period_column,
            granularity=("month" if by == "none" else by))
        for im in r.applied:
            if im.rule.citation not in citations:
                citations.append(im.rule.citation)
        if r.candidates and not any("waiting" in c for c in caveats):
            caveats.append(
                f"{len(r.candidates)} accounting item(s) are waiting for your "
                "decision on the Review screen and are NOT reflected here.")
        if by == "none":
            return r.adjusted
        series = r.by_period["reported"]
        if index is None:
            index = series.index
        return series

    for step in plan.steps:
        labels[step.id] = step.title
        by = str(step.params.get("by", "none"))

        if step.op == "revenue":
            values[step.id] = revenue_for(by)

        elif step.op == "metric":
            concept = METRIC_CONCEPTS[step.params["concept"]]
            cols = aggregation_plan.columns_for(concept)
            if not cols:
                raise PlanError(
                    f"this file has no column bound to {step.params['concept']}, "
                    f"so step {step.id!r} cannot be computed.")
            if by == "none":
                total, note = ask_mod.sum_without_double_counting(df, cols)
                if note:
                    caveats.append(note + ".")
                values[step.id] = total
            else:
                # Reuse the period assignment revenue uses, so a metric lines
                # up with revenue period-for-period rather than being bucketed
                # by its own reading of the dates.
                r = ask_mod.compute_revenue(
                    df, aggregation_plan, ratified=list(ratified),
                    rejected=list(rejected), revenue_column=revenue_column,
                    period_column=period_column, granularity=by)
                series = _metric_by_period(df, cols, r, by)
                if index is None:
                    index = series.index
                values[step.id] = series

        elif step.op == "count":
            what = str(step.params.get("of", "orders"))
            if what == "orders":
                col = ask_mod._order_column(df.columns)
                if not col:
                    raise PlanError("this file has no order identifier column.")
                values[step.id] = Decimal(int(df[col].nunique()))
            else:
                values[step.id] = Decimal(len(df))

        elif step.op == "top":
            dimension = str(step.params.get("dimension", "product"))
            n = int(step.params.get("n", 10))
            series = _top(df, aggregation_plan, dimension, n)
            index = series.index
            values[step.id] = series

        elif step.op == "constant":
            values[step.id] = Decimal(str(step.params["value"]))

        elif step.op == "formula":
            values[step.id] = eval_formula(str(step.params["expr"]), values)

    # -- assemble output -------------------------------------------------
    table = None
    scalar = None
    chart_data = None

    wanted = plan.output.table or [s.id for s in plan.steps]
    series_ids = [i for i in wanted if _is_series(values.get(i))]
    if series_ids:
        table = pd.DataFrame(
            {labels.get(i, i): values[i] for i in series_ids})
    scalars = {i: values[i] for i in wanted if not _is_series(values.get(i))}
    if scalars and table is None:
        last = wanted[-1]
        scalar = Decimal(str(scalars.get(last, list(scalars.values())[-1])))
    elif scalars and table is not None:
        for i, v in scalars.items():
            table[labels.get(i, i)] = float(v)

    chart = ""
    if plan.output.kind == "chart":
        chart = plan.output.chart
        picks = [i for i in (plan.output.series or series_ids)
                 if _is_series(values.get(i))]
        if picks:
            chart_data = pd.DataFrame(
                {labels.get(i, i): values[i] for i in picks})
            spec = charts.get(chart)
            if spec is not None and spec.single_series and len(picks) > 1:
                chart_data = chart_data.iloc[:, [0]]
            caveats += charts.caveat_for(chart, len(picks), over_time=True)

    return PlanResult(plan=plan, table=table, scalar=scalar, chart=chart,
                      chart_data=chart_data, caveats=caveats,
                      citations=citations,
                      steps_shown=[f"{s.title} = {s.params.get('expr')}"
                                   for s in plan.steps if s.op == "formula"])


def _is_series(v: Any) -> bool:
    import pandas as pd
    return isinstance(v, pd.Series)


def _metric_by_period(df: Any, columns: List[str], revenue_result: Any, by: str):
    """Total ``columns`` per period, using the same period assignment as revenue.

    Aggregate-and-component columns are collapsed first: a file carrying both
    ``Taxes`` and ``Tax 1..5 Value`` would otherwise report double the tax in
    every period, exactly as it once did for the whole-file total.
    """
    import pandas as pd

    from . import ask as ask_mod

    keep = list(columns)
    if len(keep) > 1:
        num = df[keep].apply(pd.to_numeric, errors="coerce").fillna(0.0)
        for c in keep:
            others = [x for x in keep if x != c]
            if (num[c] - num[others].sum(axis=1)).abs().max() < 0.01:
                keep = [c]
                break

    work = df.copy()
    work["_v"] = work[keep].apply(
        pd.to_numeric, errors="coerce").fillna(0.0).sum(axis=1)
    dt = pd.to_datetime(work[revenue_result.period_column],
                        errors="coerce", utc=True)
    if revenue_result.order_column:
        dt = dt.groupby(work[revenue_result.order_column]).transform(
            lambda s: s.ffill().bfill())
    grain = ask_mod._GRAIN.get(by, "M")
    work["_period"] = dt.dt.tz_localize(None).dt.to_period(grain).astype(str)
    out = work.groupby("_period")["_v"].sum()
    return out.reindex(revenue_result.by_period.index).fillna(0.0)


def _top(df: Any, aggregation_plan: Any, dimension: str, n: int):
    import pandas as pd

    from .evaluate import choose_amount_basis, rows_from_frame

    pattern = (r"(?i)(email|customer|billing[ _]?name)" if dimension == "customer"
               else r"(?i)(lineitem[ _]?name|item[ _]?name|product|sku)")
    key = next((c for c in df.columns if re.search(pattern, str(c))), None)
    if key is None:
        raise PlanError(f"this file has no column identifying a {dimension}.")
    basis = choose_amount_basis(list(df.columns), aggregation_plan)
    rows = rows_from_frame(df)
    amounts = [float(basis.amount_for(r) or 0) for r in rows]
    tmp = pd.DataFrame({"key": df[key].astype(str), "amount": amounts})
    tmp = tmp[tmp["key"].str.lower() != "nan"]
    return tmp.groupby("key")["amount"].sum().sort_values(
        ascending=False).head(max(1, n))
