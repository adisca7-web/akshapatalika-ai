"""Deterministic GAAP skills, grouped by ASC topic.

Importing this package populates :data:`gaapai.core.registry.REGISTRY`. Each
module declares its skill and registers its subskills at import time, so the
catalog is complete as soon as ``import gaapai`` returns.
"""

from . import (  # noqa: F401  -- imported for registration side effects
    cashflow,
    eps,
    inventory,
    leases,
    ppe,
    ratios,
    revenue,
    statements,
    tax,
)

__all__ = [
    "revenue", "leases", "inventory", "ppe", "eps", "cashflow", "tax",
    "statements", "ratios",
]
