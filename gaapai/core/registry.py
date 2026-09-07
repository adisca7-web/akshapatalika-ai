"""The skill registry: a hierarchy of deterministic GAAP capabilities.

A *skill* is a topic area (revenue, leases, inventory). A *subskill* is one
specific computation inside it (allocate transaction price, classify a lease,
build a LIFO layer roll-forward). Subskills are ordinary Python functions with
declared inputs and ASC citations, registered by decorator.

Why a registry rather than just calling functions: three consumers need to see
the same catalog, and they must not drift apart.

1. The router matches a natural-language question to a subskill.
2. The tool block exposes each subskill to a code-generating model as a callable
   tool, so the model composes vetted primitives instead of inventing arithmetic.
3. The documentation and diagram generators render the catalog for humans.

Registration is the single source of truth for all three.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional

from .asc import Citation
from .evidence import GaapResult

__all__ = ["SubSkill", "Skill", "SkillRegistry", "REGISTRY", "subskill", "SkillNotFound"]


class SkillNotFound(LookupError):
    pass


@dataclass
class SubSkill:
    """One deterministic computation."""

    name: str
    skill: str
    func: Callable[..., GaapResult]
    summary: str
    citations: List[Citation] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)
    inputs: Dict[str, str] = field(default_factory=dict)
    produces: str = "GaapResult"
    judgement: bool = False  # True when the result depends on entity estimates

    @property
    def qualified_name(self) -> str:
        return f"{self.skill}.{self.name}"

    @property
    def signature(self) -> str:
        return f"{self.name}{inspect.signature(self.func)}"

    def __call__(self, *args: Any, **kwargs: Any) -> GaapResult:
        result = self.func(*args, **kwargs)
        if not isinstance(result, GaapResult):
            raise TypeError(
                f"{self.qualified_name} returned {type(result).__name__}; "
                "every subskill must return a GaapResult so the answer carries "
                "its workpaper and citations"
            )
        # Guarantee the declared authority is attached even if the body forgot.
        result.cite(*self.citations)
        return result

    def describe(self) -> str:
        """The docstring *body* handed to the code-generating model.

        Deliberately excludes the signature and the triple quotes. A tool
        renderer typically emits::

            <function>
            def name(args) -> ret:
                \"\"\"{description}\"\"\"
            </function>

        so returning a full docstring here would produce a doubled signature
        and nested quotes in the prompt. Callers that need the whole block use
        :meth:`as_function_block`.
        """
        lines = [self.summary]
        if self.citations:
            refs = ", ".join(f"ASC {c.key}" for c in self.citations)
            lines.append(f"    Authority: {refs}.")
        if self.judgement:
            lines.append("    Judgement: caller must supply the entity's determinations; "
                         "do not infer them from data.")
        if self.inputs:
            lines.append("    Args:")
            for k, v in self.inputs.items():
                lines.append(f"        {k}: {v}")
        lines.append("    Returns: GaapResult (.value holds the answer, "
                     ".workpaper() the tie-out).")
        return "\n".join(lines)

    def as_function_block(self) -> str:
        """The complete ``<function>`` block as a prompt would carry it.

        Lets the tool block be inspected and diffed in a test, so what the model
        sees never drifts from what the catalog declares.
        """
        return (f'<function>\ndef {self.signature}:\n'
                f'    """{self.describe()}"""\n</function>')

    def to_dict(self) -> dict:
        return {
            "name": self.qualified_name,
            "summary": self.summary,
            "signature": self.signature,
            "authorities": [c.key for c in self.citations],
            "triggers": self.triggers,
            "inputs": self.inputs,
            "judgement": self.judgement,
        }


@dataclass
class Skill:
    """A topic area holding related subskills."""

    name: str
    title: str
    topic: str  # primary ASC topic number, e.g. "606"
    description: str = ""
    subskills: Dict[str, SubSkill] = field(default_factory=dict)

    def add(self, sub: SubSkill) -> None:
        if sub.name in self.subskills:
            raise ValueError(f"subskill {sub.qualified_name} is already registered")
        self.subskills[sub.name] = sub

    def get(self, name: str) -> SubSkill:
        try:
            return self.subskills[name]
        except KeyError:
            available = ", ".join(sorted(self.subskills)) or "(none)"
            raise SkillNotFound(
                f"{self.name} has no subskill '{name}'. Available: {available}"
            ) from None

    def __iter__(self) -> Iterable[SubSkill]:
        return iter(self.subskills.values())

    def __len__(self) -> int:
        return len(self.subskills)

    def to_dict(self) -> dict:
        return {
            "skill": self.name,
            "title": self.title,
            "asc_topic": self.topic,
            "description": self.description,
            "subskills": [s.to_dict() for s in self],
        }


class SkillRegistry:
    """The catalog. One global instance, populated at import time."""

    def __init__(self) -> None:
        self._skills: Dict[str, Skill] = {}

    # -- registration ---------------------------------------------------

    def declare(self, name: str, title: str, topic: str, description: str = "") -> Skill:
        if name not in self._skills:
            self._skills[name] = Skill(name, title, topic, description)
        return self._skills[name]

    def register(self, sub: SubSkill) -> SubSkill:
        skill = self._skills.get(sub.skill)
        if skill is None:
            raise SkillNotFound(
                f"skill '{sub.skill}' must be declared before registering "
                f"subskill '{sub.name}'"
            )
        skill.add(sub)
        return sub

    # -- lookup ---------------------------------------------------------

    def skill(self, name: str) -> Skill:
        try:
            return self._skills[name]
        except KeyError:
            available = ", ".join(sorted(self._skills)) or "(none)"
            raise SkillNotFound(
                f"no skill '{name}'. Registered skills: {available}"
            ) from None

    def resolve(self, qualified: str) -> SubSkill:
        """Look up ``"revenue.allocate_transaction_price"``."""
        if "." not in qualified:
            raise SkillNotFound(
                f"'{qualified}' is not a qualified name; expected 'skill.subskill'"
            )
        skill_name, sub_name = qualified.split(".", 1)
        return self.skill(skill_name).get(sub_name)

    def __contains__(self, qualified: str) -> bool:
        try:
            self.resolve(qualified)
            return True
        except (SkillNotFound, ValueError):
            return False

    # -- enumeration ----------------------------------------------------

    @property
    def skills(self) -> List[Skill]:
        return [self._skills[k] for k in sorted(self._skills)]

    def subskills(self) -> List[SubSkill]:
        return [s for skill in self.skills for s in skill]

    def by_citation(self, asc_key: str) -> List[SubSkill]:
        """Every subskill implementing a given paragraph -- reverse traceability."""
        return [
            s for s in self.subskills()
            if any(c.key == asc_key for c in s.citations)
        ]

    def coverage(self) -> Dict[str, List[str]]:
        """ASC paragraph -> subskills implementing it."""
        out: Dict[str, List[str]] = {}
        for s in self.subskills():
            for c in s.citations:
                out.setdefault(c.key, []).append(s.qualified_name)
        return dict(sorted(out.items()))

    def to_dict(self) -> dict:
        return {
            "skills": [s.to_dict() for s in self.skills],
            "subskill_count": len(self.subskills()),
        }

    def catalog(self) -> str:
        """Human-readable index of the whole layer."""
        lines: List[str] = []
        for skill in self.skills:
            lines.append(f"{skill.name}  --  {skill.title} (ASC {skill.topic})")
            if skill.description:
                lines.append(f"    {skill.description}")
            for sub in skill:
                refs = ", ".join(c.key for c in sub.citations)
                flag = " *judgement" if sub.judgement else ""
                lines.append(f"    - {sub.name}{flag}")
                lines.append(f"        {sub.summary}")
                if refs:
                    lines.append(f"        ASC {refs}")
            lines.append("")
        return "\n".join(lines)


REGISTRY = SkillRegistry()


def subskill(
    skill: str,
    name: Optional[str] = None,
    *,
    summary: str = "",
    citations: Optional[Iterable[Citation]] = None,
    triggers: Optional[Iterable[str]] = None,
    inputs: Optional[Dict[str, str]] = None,
    judgement: bool = False,
    registry: Optional[SkillRegistry] = None,
) -> Callable[[Callable[..., GaapResult]], SubSkill]:
    """Register a function as a deterministic subskill.

    The decorated function is *replaced* by its :class:`SubSkill` wrapper, which
    stays callable. That way the return-type guarantee and citation attachment
    cannot be bypassed by importing the raw function.
    """

    reg = registry or REGISTRY

    def decorate(func: Callable[..., GaapResult]) -> SubSkill:
        doc = inspect.getdoc(func) or ""
        first_line = doc.strip().split("\n", 1)[0] if doc else ""
        sub = SubSkill(
            name=name or func.__name__,
            skill=skill,
            func=func,
            summary=summary or first_line or func.__name__,
            citations=list(citations or []),
            triggers=[t.lower() for t in (triggers or [])],
            inputs=dict(inputs or {}),
            judgement=judgement,
        )
        reg.register(sub)
        return sub

    return decorate
