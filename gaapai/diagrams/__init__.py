"""Diagram generation from GAAP results.

Two renderers, for two audiences:

* :mod:`mermaid` emits text diagrams that render inline in Markdown, chat, and
  Artifacts with no dependencies. Use these for decision flows and structure.
* :mod:`charts` emits matplotlib figures for quantitative schedules -- lease
  amortisation, revenue waterfalls, depreciation curves.

Both take a :class:`~gaapai.core.evidence.GaapResult` and read its schedule and
steps, so a diagram can never disagree with the workpaper it came from.
"""

from .mermaid import (
    allocation_diagram,
    cash_flow_diagram,
    five_step_diagram,
    impairment_diagram,
    lease_classification_diagram,
    skill_map,
)

__all__ = [
    "allocation_diagram",
    "cash_flow_diagram",
    "five_step_diagram",
    "impairment_diagram",
    "lease_classification_diagram",
    "skill_map",
]
