"""PandasAI bridge: expose the GAAP kernel as tools the code generator must use.

PandasAI answers a question by asking an LLM to write Python, then executing it.
Left alone, the model writes the accounting itself -- and an invented revenue
allocation or lease schedule looks exactly like a correct one in the output.

This bridge changes what the model is asked to do. Each kernel subskill is
registered as a PandasAI skill, so its signature and docstring are injected into
the prompt (via ``shared/sql_functions.tmpl``) and its callable is placed in the
code executor's environment. The model then composes vetted primitives instead
of deriving arithmetic, and the policy text below tells it so explicitly.

Three integration points in PandasAI 3.0 are used:

1. ``SkillsManager.add_skills`` -- registers callables and injects their
   signatures into the generated-code prompt.
2. ``Agent(description=...)`` -- flows into ``generate_system_message.tmpl``,
   which is where the GAAP policy lands.
3. ``Agent.execute_code`` -- wrapped to capture the workpapers produced during
   execution, so the answer carries its audit trail.

**Environment note.** PandasAI 3.0 pins ``python = ">=3.8,<3.12"``. On a newer
interpreter :func:`available` returns False and :func:`build_agent` raises with
an explanation. The kernel itself is unaffected -- it needs only the standard
library, which is why the dependency lives here and not in the core.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Dict, List, Optional

from ..core.evidence import GaapResult
from ..core.registry import REGISTRY, SubSkill

__all__ = [
    "aggregation_contract",
    "available", "import_error", "gaap_skill_functions", "tool_descriptions",
    "register_skills", "build_agent", "GAAP_POLICY",
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


def import_error() -> Optional[Exception]:
    """Return the ImportError from loading PandasAI, or None if it imported."""
    try:
        import pandasai  # noqa: F401
        return None
    except Exception as exc:  # pragma: no cover - environment dependent
        return exc


def available() -> bool:
    """True when PandasAI can be imported in this interpreter."""
    return import_error() is None


def _wrap(sub: SubSkill) -> Callable[..., Any]:
    """Adapt a subskill into a plain function PandasAI can register.

    PandasAI derives the tool description from ``__name__``, ``__doc__``, and the
    signature, so those are set explicitly rather than left as the SubSkill
    wrapper's. The workpaper is recorded on the wrapper so the caller can collect
    evidence after execution.
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
    """The tool block as PandasAI would inject it -- useful without PandasAI installed.

    Lets you inspect, diff, and test exactly what the code generator will see,
    on any interpreter.
    """
    lines: List[str] = []
    wanted = set(skills) if skills else None
    for sub in REGISTRY.subskills():
        if wanted and sub.skill not in wanted:
            continue
        lines.append(sub.as_function_block())
    return "\n".join(lines)


def register_skills(skills: Optional[List[str]] = None) -> List[Any]:
    """Register kernel subskills with PandasAI's global SkillsManager.

    Idempotent. ``SkillsManager`` is a process-wide singleton whose
    ``add_skills`` raises ``ValueError`` on a duplicate name, so a second call --
    building two agents, re-running a notebook cell, retrying after an error --
    would otherwise crash. Already-registered subskills are skipped and the
    existing object returned, so the caller always gets the full set back
    regardless of how many times this has run.
    """
    err = import_error()
    if err is not None:
        raise RuntimeError(
            "PandasAI is not importable in this interpreter, so its skills "
            f"cannot be registered ({err}). PandasAI 3.0 requires Python "
            ">=3.8,<3.12; the GAAP kernel itself has no such constraint. Use "
            "tool_descriptions() to inspect the tool block without PandasAI."
        ) from err

    from pandasai.ee.skills import SkillType
    from pandasai.ee.skills.manager import SkillsManager

    registered = []
    for fn in gaap_skill_functions(skills).values():
        existing = SkillsManager.get_skill_by_func_name(fn.__name__)
        if existing is not None:
            registered.append(existing)
            continue
        skill_obj = SkillType(func=fn, name=fn.__name__, description=fn.__doc__)
        SkillsManager.add_skills(skill_obj)
        registered.append(skill_obj)
    return registered


def _columns_of(dfs: Any) -> List[str]:
    """Best-effort column extraction from whatever PandasAI was handed."""
    frames = dfs if isinstance(dfs, (list, tuple)) else [dfs]
    cols: List[str] = []
    for f in frames:
        got = getattr(f, "columns", None)
        if got is not None:
            cols.extend(str(c) for c in got)
            continue
        # Datasets carry their columns on a semantic-layer schema instead.
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

    This is the half of the bridge that constrains *retrieval* rather than
    computation. The subskills stop the model inventing arithmetic; this stops
    it summing the wrong column. Both are needed: an exactly-correct ASC 606
    allocation of the wrong revenue figure is still wrong.

    Inspectable on any interpreter, PandasAI installed or not.
    """
    from ..semantics import plan_aggregation

    cols = columns if columns is not None else _columns_of(dfs)
    if not cols:
        return ""
    return plan_aggregation(cols, industry=industry, concept=concept).render()


def build_agent(
    dfs: Any,
    skills: Optional[List[str]] = None,
    industry: Optional[str] = None,
    extra_description: str = "",
    **agent_kwargs: Any,
):
    """Construct a PandasAI Agent with the GAAP kernel, policy, and contract.

    Three things are attached that a bare PandasAI agent does not have:

    1. the kernel's subskills, callable from generated code;
    2. the GAAP policy, forbidding the model from doing accounting arithmetic;
    3. the aggregation contract for ``industry`` -- which column means revenue,
       what must be netted against it, and what a naive SUM would get wrong in
       this particular regime.

    ``industry`` takes an ASC code or a name fragment: ``"926"``, ``"film"``,
    ``"insurance"``, ``"not-for-profit"``. Omitting it applies the ASC 606
    baseline, which still requires netting contra-revenue and settling principal
    versus agent.
    """
    err = import_error()
    if err is not None:
        raise RuntimeError(
            "PandasAI is not importable in this interpreter "
            f"({err}). PandasAI 3.0 requires Python >=3.8,<3.12. Create a 3.11 "
            "environment to use the agent; the kernel, router, semantics, and "
            "diagrams work on any supported Python."
        ) from err

    from pandasai import Agent

    register_skills(skills)
    parts = [GAAP_POLICY]
    contract = aggregation_contract(dfs, industry=industry)
    if contract:
        parts.append(contract)
    if extra_description:
        parts.append(extra_description)
    return Agent(dfs, description="\n\n".join(parts), **agent_kwargs)
