"""Adapters connecting the GAAP kernel to data tools and code-generating models.

The kernel deliberately depends on nothing but the standard library, so pandas
enters only here, at the boundary.
"""

from .toolblock import (
    GAAP_POLICY,
    aggregation_contract,
    gaap_skill_functions,
    tool_descriptions,
)

__all__ = [
    "tool_descriptions", "aggregation_contract", "gaap_skill_functions",
    "GAAP_POLICY",
]
