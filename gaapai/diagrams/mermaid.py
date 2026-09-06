"""Mermaid diagram generation.

Diagrams are built from a :class:`GaapResult`, not from free text, so the
picture always matches the computation. Where a decision has been made, the
taken branch is highlighted -- the reader sees not just the rule but which way
this fact pattern went, which is the part a reviewer actually needs.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, List, Optional

from ..core.evidence import GaapResult
from ..core.money import Money, quantize
from ..core.registry import REGISTRY

__all__ = [
    "five_step_diagram", "lease_classification_diagram", "impairment_diagram",
    "allocation_diagram", "cash_flow_diagram", "skill_map",
]

# Mermaid class definitions reused across diagrams. Colours are chosen to read
# in both light and dark themes.
_STYLES = """
    classDef taken fill:#1a7f37,stroke:#0d4f21,color:#ffffff,font-weight:bold
    classDef nottaken fill:#f6f8fa,stroke:#b0b7c0,color:#57606a
    classDef result fill:#0969da,stroke:#0a3069,color:#ffffff,font-weight:bold
    classDef warn fill:#bf8700,stroke:#7d4e00,color:#ffffff
    classDef step fill:#eef2f6,stroke:#8c959f,color:#1f2328
"""


def _esc(text: str) -> str:
    """Mermaid node labels cannot contain quotes or unescaped brackets."""
    return (
        str(text)
        .replace('"', "'")
        .replace("[", "(")
        .replace("]", ")")
        .replace("\n", " ")
    )


def _fmt(value) -> str:
    if isinstance(value, Money):
        return f"{quantize(value.amount, 2):,}"
    if isinstance(value, Decimal):
        return f"{quantize(value, 4).normalize():,}"
    return _esc(value)


def five_step_diagram(result: Optional[GaapResult] = None) -> str:
    """The ASC 606 five-step model, optionally annotated with an actual result."""
    lines = ["flowchart TD"]
    lines.append('    S1["Step 1<br/>Identify the contract<br/><i>ASC 606-10-25-1</i>"]')
    lines.append('    S2["Step 2<br/>Identify performance obligations<br/><i>606-10-25-14</i>"]')
    lines.append('    S3["Step 3<br/>Determine transaction price<br/><i>606-10-32-2</i>"]')
    lines.append('    S4["Step 4<br/>Allocate on relative SSP<br/><i>606-10-32-31</i>"]')
    lines.append('    S5["Step 5<br/>Recognise as control transfers<br/><i>606-10-25-23</i>"]')
    lines.append("    S1 --> S2 --> S3 --> S4 --> S5")

    lines.append('    S3 -.-> V["Variable consideration<br/>constrained 606-10-32-11"]')
    lines.append('    S3 -.-> F["Significant financing<br/>606-10-32-15"]')
    lines.append('    S5 -.-> OT["Over time<br/>606-10-25-27"]')
    lines.append('    S5 -.-> PT["Point in time<br/>606-10-25-30"]')

    if result is not None and isinstance(result.value, dict):
        recognized = result.value.get("recognized")
        deferred = result.value.get("deferred")
        if recognized is not None:
            lines.append(
                f'    R["Recognised {_fmt(recognized)}<br/>'
                f'Deferred {_fmt(deferred)}"]'
            )
            lines.append("    S5 --> R")
            lines.append("    class R result")

    lines.append(_STYLES)
    lines.append("    class S1,S2,S3,S4,S5 step")
    return "\n".join(lines)


def lease_classification_diagram(result: Optional[GaapResult] = None) -> str:
    """The five ASC 842-10-25-2 criteria, with the actual outcome highlighted."""
    taken: List[str] = []
    outcome = None
    if result is not None:
        outcome = result.value
        for step in result.steps:
            if step.value == "MET" and step.label.startswith("("):
                taken.append(step.label[1])

    lines = ["flowchart TD"]
    lines.append('    START["Lease commencement"]')
    labels = {
        "a": "Ownership transfers<br/>by end of term",
        "b": "Purchase option<br/>reasonably certain",
        "c": "Term is a major part<br/>of economic life",
        "d": "PV of payments is<br/>substantially all of fair value",
        "e": "Specialised asset,<br/>no alternative use",
    }
    for key, label in labels.items():
        lines.append(f'    {key.upper()}["({key}) {label}"]')
        lines.append(f"    START --> {key.upper()}")

    lines.append('    FIN["FINANCE LEASE<br/>interest + straight-line amortisation"]')
    lines.append('    OPS["OPERATING LEASE<br/>single straight-line lease cost"]')
    for key in labels:
        lines.append(f"    {key.upper()} -->|met| FIN")
    lines.append("    A -.->|none met| OPS")

    lines.append(_STYLES)
    if taken:
        lines.append("    class " + ",".join(k.upper() for k in taken) + " taken")
    untaken = [k.upper() for k in labels if k not in taken]
    if untaken:
        lines.append("    class " + ",".join(untaken) + " nottaken")
    if outcome == "finance":
        lines.append("    class FIN result")
        lines.append("    class OPS nottaken")
    elif outcome == "operating":
        lines.append("    class OPS result")
        lines.append("    class FIN nottaken")
    return "\n".join(lines)


def impairment_diagram(result: Optional[GaapResult] = None) -> str:
    """The ASC 360 two-step test, making the undiscounted screen explicit."""
    lines = ["flowchart TD"]
    lines.append('    C["Carrying amount"]')
    lines.append('    S1{"Step 1<br/>Undiscounted cash flows<br/>>= carrying amount?<br/><i>360-10-35-17</i>"}')
    lines.append('    OK["Not impaired<br/>no loss, even if fair value is lower"]')
    lines.append('    S2["Step 2<br/>Loss = carrying amount - FAIR VALUE"]')
    lines.append('    NB["New cost basis<br/>never restored (360-10-35-20)"]')
    lines.append("    C --> S1")
    lines.append("    S1 -->|yes| OK")
    lines.append("    S1 -->|no| S2 --> NB")

    lines.append(_STYLES)
    if result is not None and isinstance(result.value, dict):
        if result.value.get("impaired"):
            lines.append(f'    L["Loss {_fmt(result.value.get("loss"))}"]')
            lines.append("    S2 --> L")
            lines.append("    class S2,NB,L taken")
            lines.append("    class OK nottaken")
        else:
            lines.append("    class OK result")
            lines.append("    class S2,NB nottaken")
    return "\n".join(lines)


def allocation_diagram(result: GaapResult) -> str:
    """Sankey-style view of a transaction price allocation."""
    if not result.schedule:
        raise ValueError("allocation_diagram needs a result carrying a schedule")

    lines = ["flowchart LR"]
    price = result.inputs.get("transaction_price")
    lines.append(f'    TP["Transaction price<br/>{_fmt(price)}"]')
    for i, row in enumerate(result.schedule):
        name = _esc(row.get("obligation", f"PO{i}"))
        allocated = row.get("allocated")
        ssp = row.get("ssp")
        basis = row.get("basis", "")
        node = f"PO{i}"
        lines.append(
            f'    {node}["{name}<br/>allocated {_fmt(allocated)}<br/>'
            f'<i>SSP {_fmt(ssp)} ({basis})</i>"]'
        )
        lines.append(f"    TP --> {node}")
    lines.append(_STYLES)
    lines.append("    class TP result")
    lines.append("    class " + ",".join(f"PO{i}" for i in range(len(result.schedule)))
                 + " step")
    return "\n".join(lines)


def cash_flow_diagram(result: GaapResult) -> str:
    """Operating, investing, and financing flows into the change in cash."""
    if not isinstance(result.value, dict):
        raise ValueError("cash_flow_diagram needs an indirect_method result")
    v = result.value
    lines = ["flowchart LR"]
    lines.append(f'    OP["Operating<br/>{_fmt(v.get("operating"))}"]')
    lines.append(f'    IN["Investing<br/>{_fmt(v.get("investing"))}"]')
    lines.append(f'    FI["Financing<br/>{_fmt(v.get("financing"))}"]')
    lines.append(f'    NET["Net change in cash<br/>{_fmt(v.get("net_change"))}"]')
    for n in ("OP", "IN", "FI"):
        lines.append(f"    {n} --> NET")
    if "ending_cash" in v:
        lines.append(f'    END["Ending cash<br/>{_fmt(v["ending_cash"])}"]')
        lines.append("    NET --> END")
        lines.append("    class END result")
    lines.append(_STYLES)
    lines.append("    class OP,IN,FI step")
    lines.append("    class NET result")
    return "\n".join(lines)


def skill_map(skills: Optional[Iterable[str]] = None) -> str:
    """Map the registered deterministic layer: skills and their subskills."""
    lines = ["flowchart TD"]
    lines.append('    ROOT["gaapai<br/>deterministic GAAP layer"]')
    wanted = set(skills) if skills else None

    for skill in REGISTRY.skills:
        if wanted and skill.name not in wanted:
            continue
        sid = f"S_{skill.name}"
        lines.append(f'    {sid}["{_esc(skill.title)}<br/><i>ASC {skill.topic}</i>"]')
        lines.append(f"    ROOT --> {sid}")
        for sub in skill:
            uid = f"{sid}_{sub.name}"
            refs = ", ".join(c.key for c in sub.citations[:2])
            flag = " *" if sub.judgement else ""
            lines.append(f'    {uid}["{_esc(sub.name)}{flag}<br/><i>{refs}</i>"]')
            lines.append(f"    {sid} --> {uid}")
    lines.append(_STYLES)
    lines.append("    class ROOT result")
    return "\n".join(lines)
