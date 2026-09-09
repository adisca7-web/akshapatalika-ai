"""The entity profile: facts about a reporting entity that data cannot reveal.

Column bindings and row rules are derived from a schema. A large class of GAAP
questions cannot be, because the answer depends on something the entity decided
rather than something the file records:

* which date column represents transfer of control (ASC 606-10-25-23);
* whether the fiscal calendar is calendar months or a 52/53-week retail year;
* which practical expedients and policy elections were taken;
* whether a right of return exists, and over what window;
* which legal entities consolidate, and how intercompany rows are flagged.

None of that is in a transactions export. Asking per query is worse than
useless -- the answer would change between two runs of the same question. So it
is asserted once, versioned on disk, and carried into every run.

The profile also holds the outcome of the propose-and-ratify loop. A row rule
proposed against real data is a *candidate* and changes nothing; once a
preparer ratifies it, its name lands in :attr:`EntityProfile.ratified_rules`
and it is applied from then on, deterministically. Rejections are recorded too,
so the same rejected rule is not proposed again at every refresh.

Storage is plain JSON, so a profile diffs in review like any other artifact.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

__all__ = ["DEFAULT_DIR", "EntityProfile", "RuleDecision", "list_profiles", "load", "save"]

DEFAULT_DIR = Path.home() / ".gaapai" / "entities"

# Facts the layer knows it needs and cannot derive. Presented as open questions
# rather than defaults: a wrong default here is silently wrong for every answer,
# whereas an unanswered question can at least be displayed as unanswered.
OPEN_QUESTIONS = {
    "control_transfer_column":
        "Which column marks transfer of control? Order date and fulfilment date "
        "give materially different period cuts (ASC 606-10-25-23).",
    "fiscal_calendar":
        "Calendar months, or a 4-5-4 / 52-53-week retail year? Month boundaries "
        "move if it is the latter.",
    "right_of_return":
        "Do customers have a right of return? If so a refund liability is "
        "required for EXPECTED returns, not only those already taken "
        "(ASC 606-10-32-10).",
    "return_window_days":
        "Over what window? Recent periods are understated until the window "
        "closes, which makes the most recent month look better than it is.",
    "sales_tax_presentation":
        "Are sales taxes collected excluded from the transaction price? "
        "(ASC 606-10-32-2A).",
    "intercompany_flag":
        "If more than one legal entity is present, which column identifies "
        "intercompany rows so they can be eliminated (ASC 810-10-45-1)?",
}


@dataclass
class RuleDecision:
    """A preparer's decision on one proposed row rule."""

    rule_name: str
    decision: str               # "ratified" | "rejected"
    decided_at: str
    rows_at_decision: int = 0
    amount_at_decision: str = ""
    note: str = ""

    @staticmethod
    def now(rule_name: str, decision: str, rows: int = 0,
            amount: str = "", note: str = "") -> "RuleDecision":
        return RuleDecision(
            rule_name=rule_name, decision=decision,
            decided_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            rows_at_decision=rows, amount_at_decision=amount, note=note,
        )


@dataclass
class EntityProfile:
    """Everything asserted about one reporting entity."""

    name: str
    industry: str = "606"
    fiscal_calendar: str = ""
    control_transfer_column: str = ""
    right_of_return: Optional[bool] = None
    return_window_days: Optional[int] = None
    sales_tax_presentation: str = ""
    intercompany_flag: str = ""
    elections: Dict[str, Any] = field(default_factory=dict)
    decisions: List[RuleDecision] = field(default_factory=list)
    notes: str = ""
    updated_at: str = ""

    # -- ratification ---------------------------------------------------

    @property
    def ratified_rules(self) -> List[str]:
        return [d.rule_name for d in self.decisions if d.decision == "ratified"]

    @property
    def rejected_rules(self) -> List[str]:
        return [d.rule_name for d in self.decisions if d.decision == "rejected"]

    def decide(self, rule_name: str, decision: str, *, rows: int = 0,
               amount: str = "", note: str = "") -> None:
        """Record a decision, replacing any earlier one for the same rule."""
        if decision not in ("ratified", "rejected"):
            raise ValueError(f"decision must be ratified or rejected, got {decision!r}")
        self.decisions = [d for d in self.decisions if d.rule_name != rule_name]
        self.decisions.append(
            RuleDecision.now(rule_name, decision, rows, amount, note))

    def clear(self, rule_name: str) -> None:
        """Return a rule to candidate status."""
        self.decisions = [d for d in self.decisions if d.rule_name != rule_name]

    # -- completeness ---------------------------------------------------

    def unanswered(self) -> Dict[str, str]:
        """Open questions this profile has not answered yet.

        Surfaced rather than defaulted. Every entry here is a level of
        identification the layer cannot perform, and saying so is the difference
        between a known gap and a wrong number.
        """
        out: Dict[str, str] = {}
        for key, question in OPEN_QUESTIONS.items():
            value = getattr(self, key, None)
            if value in (None, "", []):
                out[key] = question
        return out

    # -- persistence ----------------------------------------------------

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ratified_rules"] = self.ratified_rules
        d["rejected_rules"] = self.rejected_rules
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "EntityProfile":
        decisions = [RuleDecision(**d) for d in data.get("decisions", [])]
        fields = {k: v for k, v in data.items()
                  if k in cls.__dataclass_fields__ and k != "decisions"}
        return cls(decisions=decisions, **fields)

    def save(self, directory: Optional[Path] = None) -> Path:
        return save(self, directory)


def _slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "entity"


def path_for(name: str, directory: Optional[Path] = None) -> Path:
    return (Path(directory) if directory else DEFAULT_DIR) / f"{_slug(name)}.json"


def save(profile: EntityProfile, directory: Optional[Path] = None) -> Path:
    profile.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    target = path_for(profile.name, directory)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
    return target


def load(name: str, directory: Optional[Path] = None) -> EntityProfile:
    target = path_for(name, directory)
    if not target.exists():
        return EntityProfile(name=name)
    return EntityProfile.from_dict(json.loads(target.read_text(encoding="utf-8")))


def list_profiles(directory: Optional[Path] = None) -> List[str]:
    d = Path(directory) if directory else DEFAULT_DIR
    if not d.exists():
        return []
    out = []
    for f in sorted(d.glob("*.json")):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")).get("name", f.stem))
        except (json.JSONDecodeError, OSError):
            continue
    return out
