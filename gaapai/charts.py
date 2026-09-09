"""The chart registry: one declaration per chart kind, used by everything.

Chart handling used to be spelled out three times -- a regex in the question
parser, a branch in the renderer, and a list in the model's prompt. Adding a
kind meant finding all three, and missing one failed silently in a different
way each time (an unknown kind quietly drew bars).

Now a kind is declared once, here, and everything derives from it:

* the phrase patterns that recognise it in a question;
* the description the planning model is shown, so it can request it;
* the validator, so a plan naming an unknown kind is rejected rather than
  drawn as something else;
* the renderer the app dispatches on.

**Adding a chart type** is therefore one entry plus one renderer branch in
``devapp/app.py``. If the renderer is missing, :func:`renderable` reports it
instead of the app silently substituting bars.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = [
    "CHARTS",
    "ChartKind",
    "caveat_for",
    "chart_names",
    "describe_for_model",
    "detect",
    "get",
    "is_known",
]


@dataclass(frozen=True)
class ChartKind:
    """One way of drawing a series."""

    name: str
    summary: str
    aliases: List[str] = field(default_factory=list)
    # True when the kind implies the values are parts of one whole. Drawing a
    # period series this way is misleading, so it earns a caveat.
    parts_of_whole: bool = False
    # True when the kind needs a single numeric series rather than several.
    single_series: bool = False

    @property
    def pattern(self) -> str:
        words = [re.escape(self.name)] + [a for a in self.aliases]
        return r"\b(" + "|".join(words) + r")\b"


CHARTS: Dict[str, ChartKind] = {
    c.name: c for c in [
        ChartKind("bar", "Vertical bars. The default for comparing periods or categories.",
                  aliases=[r"bar\s*(chart|graph|plot)?", r"column\s*(chart|graph)"]),
        ChartKind("line", "A connected line. Best for a trend over time.",
                  aliases=[r"line\s*(chart|graph|plot)?", r"as a line", r"trend\s*line"]),
        ChartKind("area", "A filled line. A trend where the magnitude matters.",
                  aliases=[r"area\s*(chart|graph|plot)?"]),
        ChartKind("pie", "Slices of a single total.",
                  aliases=["pie", "donut", "doughnut"],
                  parts_of_whole=True, single_series=True),
        ChartKind("scatter", "Points. For a relationship between two measures.",
                  aliases=[r"scatter\s*(chart|graph|plot)?", "scatterplot"]),
        ChartKind("table", "No chart, just the figures.",
                  aliases=[r"just the (numbers|figures)", "no chart",
                           "as a table", "table only"]),
    ]
}


def chart_names() -> List[str]:
    return list(CHARTS)


def is_known(name: str) -> bool:
    return name in CHARTS


def get(name: str) -> Optional[ChartKind]:
    return CHARTS.get(name)


def detect(question: str) -> str:
    """The chart kind named in a question, or "" when none is.

    Longer, more specific kinds are tried first so "bar" inside "bar chart"
    cannot shadow a phrase belonging to another kind.
    """
    q = (question or "").lower()
    for kind in sorted(CHARTS.values(), key=lambda k: -len(k.name)):
        if re.search(kind.pattern, q):
            return kind.name
    return ""


def describe_for_model() -> str:
    """The chart menu, rendered for the planning prompt.

    Generated rather than written out, so a kind added here is immediately
    available to the model without the prompt drifting out of date.
    """
    return "\n".join(f'  "{k.name}" -- {k.summary}' for k in CHARTS.values())


def caveat_for(kind: str, series_count: int = 1, over_time: bool = True) -> List[str]:
    """Warnings about drawing this data this way. The chart is still drawn."""
    spec = CHARTS.get(kind)
    if spec is None:
        return []
    out: List[str] = []
    if spec.parts_of_whole and over_time:
        out.append(
            "A pie chart shows parts of a single whole, so a period-by-period "
            "series reads poorly in one — the slices imply the months sum to "
            "something meaningful rather than following each other in time. "
            "A bar or line chart shows a trend more honestly.")
    if spec.single_series and series_count > 1:
        out.append(
            f"A {kind} chart shows one series; {series_count} were requested, "
            "so only the first is drawn. Use a bar or line chart to compare "
            "them side by side.")
    return out
