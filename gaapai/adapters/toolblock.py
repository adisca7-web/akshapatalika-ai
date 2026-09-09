"""Expose the GAAP kernel to any code-generating model as callable tools.

A model asked to answer a financial question by writing code will, left alone,
write the accounting itself — and an invented revenue allocation or lease
schedule looks exactly like a correct one in the output.

This module produces the two blocks that stop that:

:func:`tool_descriptions`
    Each subskill rendered as a function signature with its docstring and ASC
    authority, so the model composes vetted primitives instead of deriving
    arithmetic.
:func:`aggregation_contract`
    The retrieval half: which column means revenue in this industry, what must
    be netted against it, and which columns must never be summed as revenue at
    all. An exactly-correct ASC 606 allocation of the *wrong* revenue figure is
    still wrong, so both halves are needed.

:data:`GAAP_POLICY` states the rules in prose for the system message.

All three are plain strings. They can be pasted into any prompt, sent to any
provider, or inspected in a test — nothing here binds to a particular model or
framework, and :func:`gaap_skill_functions` hands back the callables if you
want to wire them into a tool-calling loop yourself.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, List, Optional

from ..core.evidence import GaapResult
from ..core.registry import REGISTRY, SubSkill

__all__ = [
    "GAAP_POLICY",
    "aggregation_contract",
    "gaap_skill_functions",
    "tool_descriptions",
]


GAAP_POLICY = """
You are a financial analysis assistant operating under US GAAP (FASB Accounting
Standards Codification). You have been given vetted accounting functions. Follow
these rules without exception.

1. NEVER compute an accounting result with your own arithmetic when one of the
   provided GAAP functions covers it. Call the function. This applies to revenue
   allocation and recognition, lease classification and schedules, inventory cost
   flow and lower-of-cost measurement, depreciation, impairment, earnings per
   share, deferred taxes, cash flow statements, and statement assembly.

2. NEVER use floating point for monetary amounts. The GAAP functions take and
   return exact decimal Money values. Do not convert them to float, and do not
   round intermediate results -- rounding happens once, at presentation.

3. ALWAYS verify a trial balance before deriving anything from it. Call
   verify_trial_balance first. If it does not balance, report that and stop; do
   not produce statement figures from an unbalanced ledger.

4. EVERY returned GaapResult carries a workpaper. Surface result.summary in your
   answer and keep the result object so its citations and checks travel with the
   number. An accounting answer without its authority is not reviewable.

5. If a GaapResult reports a failed check (result.ok is False), report the
   exception. Do not silently present the value.

6. Judgements belong to the preparer, not to you. Whether a promise is distinct,
   what a standalone selling price is, whether an option is reasonably certain of
   exercise, whether collection is probable -- these are entity determinations.
   Pass them in as explicit arguments and state the assumption; never infer them
   from the data.

7. If no provided function covers the question, say so and explain what would be
   needed. Do not improvise an accounting treatment.
""".strip()


def _wrap(sub: SubSkill) -> Callable[..., Any]:
    """Adapt a subskill into a plain function, recording the results it produces.

    The workpaper is kept on the wrapper so a caller can collect the evidence
    after a run rather than having to thread it through the model's output.
    """

    @functools.wraps(sub.func)
    def caller(*args: Any, **kwargs: Any) -> GaapResult:
        result = sub(*args, **kwargs)
        caller.last_result = result
        caller.results.append(result)
        return result

    caller.__name__ = sub.name
    caller.__doc__ = sub.describe()
    caller.last_result = None
    caller.results = []
    caller.subskill = sub
    return caller


def gaap_skill_functions(skills: Optional[List[str]] = None) -> Dict[str, Callable]:
    """Every registered subskill as a callable, keyed by qualified name."""
    wanted = set(skills) if skills else None
    out: Dict[str, Callable] = {}
    for sub in REGISTRY.subskills():
        if wanted and sub.skill not in wanted:
            continue
        out[sub.qualified_name] = _wrap(sub)
    return out


def tool_descriptions(skills: Optional[List[str]] = None) -> str:
    """The subskills rendered as a tool block for a code-generating prompt."""
    lines: List[str] = []
    wanted = set(skills) if skills else None
    for sub in REGISTRY.subskills():
        if wanted and sub.skill not in wanted:
            continue
        lines.append(sub.as_function_block())
    return "\n".join(lines)


def _columns_of(dfs: Any) -> List[str]:
    """Best-effort column extraction from a frame, a list of frames, or a schema."""
    frames = dfs if isinstance(dfs, (list, tuple)) else [dfs]
    cols: List[str] = []
    for f in frames:
        got = getattr(f, "columns", None)
        if got is not None:
            cols.extend(str(c) for c in got)
            continue
        schema = getattr(f, "schema", None)
        schema_cols = getattr(schema, "columns", None) if schema is not None else None
        if schema_cols:
            for c in schema_cols:
                cols.append(str(getattr(c, "name", c)))
    return cols


def aggregation_contract(
    dfs: Any = None,
    industry: Optional[str] = None,
    columns: Optional[List[str]] = None,
    concept: str = "net_revenue",
) -> str:
    """Render the GAAP aggregation contract for a schema and industry.

    This is the half of the guard that constrains *retrieval* rather than
    computation: which column means revenue here, what must be netted against
    it, and what a naive SUM would get wrong in this particular regime.
    """
    from ..semantics import plan_aggregation

    cols = columns if columns is not None else _columns_of(dfs)
    if not cols:
        return ""
    return plan_aggregation(cols, industry=industry, concept=concept).render()
