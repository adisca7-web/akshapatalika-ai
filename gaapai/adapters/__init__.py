"""Adapters connecting the GAAP kernel to data tools.

The kernel deliberately depends on nothing but the standard library, so pandas
and PandasAI enter only here, at the boundary. Import failures are surfaced as
clear errors rather than crashing the kernel.
"""

from .pandasai_bridge import (
    aggregation_contract,
    GAAP_POLICY,
    available,
    build_agent,
    gaap_skill_functions,
    tool_descriptions,
)

__all__ = [
    "available", "build_agent", "gaap_skill_functions", "tool_descriptions",
    "GAAP_POLICY", "aggregation_contract",
]
