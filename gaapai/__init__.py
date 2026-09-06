"""gaapai — a deterministic GAAP layer for conversational data analysis.

The problem this solves: a language model asked "what was our Q3 revenue" will
produce a confident number. Nothing about the answer reveals whether the model
applied ASC 606 correctly, whether the trial balance it read was in balance, or
whether it simply did arithmetic that looked right. In accounting, a plausible
wrong answer is worse than no answer.

So the arithmetic does not happen in the model. It happens here, in registered
subskills that are ordinary Python functions with declared ASC citations. The
model's job is reduced to routing -- picking which vetted function to call and
with what inputs. Everything it returns carries a workpaper: inputs, formula,
intermediate steps, authority, and the GAAP checks that were run.

Two layers sit on top of this package:

* ``skills/wiley-gaap`` -- the reference knowledge pack distilled from
  *Wiley GAAP 2020*: 64 ASC topic chapters and 20 specialized industry regimes.
  That layer answers "what does the standard require".
* the PandasAI adapter -- exposes the subskills below as callable tools to a
  code-generating model, so generated code composes vetted primitives instead
  of inventing formulas.

Money is exact decimal throughout. Floats are never used for amounts: a trial
balance summed in binary floating point drifts out of balance within a few
hundred thousand rows, and ``0.1 + 0.2 != 0.3`` is not an acceptable property
for a general ledger.
"""

from __future__ import annotations

from .core import (
    ASC,
    REGISTRY,
    Assumption,
    Check,
    Citation,
    GaapResult,
    Money,
    Severity,
    SkillNotFound,
    Step,
    SubSkill,
    all_citations,
    allocate,
    cite,
    money,
    quantize,
    subskill,
)
from . import skills as _skills  # noqa: F401 -- populates REGISTRY on import

__version__ = "0.1.0"

__all__ = [
    "ASC", "Citation", "cite", "all_citations",
    "Money", "money", "quantize", "allocate",
    "GaapResult", "Step", "Assumption", "Check", "Severity",
    "REGISTRY", "SubSkill", "subskill", "SkillNotFound",
    "resolve", "catalog", "coverage", "__version__",
]


def resolve(qualified_name: str) -> SubSkill:
    """Look up a subskill by ``"skill.subskill"``.

    >>> resolve("revenue.allocate_transaction_price")  # doctest: +ELLIPSIS
    SubSkill(name='allocate_transaction_price', ...)
    """
    return REGISTRY.resolve(qualified_name)


def catalog() -> str:
    """Human-readable index of every registered skill and subskill."""
    return REGISTRY.catalog()


def coverage() -> dict:
    """ASC paragraph -> the subskills implementing it.

    Reverse traceability: given a citation, which code claims to implement it.
    """
    return REGISTRY.coverage()
