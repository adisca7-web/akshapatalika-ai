"""The kernel's dependency-free claim, and the environment that backs it.

"Zero dependencies" is easy to break by accident -- one convenience import of
pandas inside a core module and the claim is false, silently, until somebody
installs the package clean and it fails on import.

Checking what is *installed* would not catch it: a development machine has
pandas either way. What matters is whether the kernel ever *reaches* for it, so
these tests inspect ``sys.modules`` and the source instead, which is true
regardless of what happens to be on the path.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Modules the kernel must never require. pandas and numpy belong to the data
# adapters, streamlit to the app, and the optional model layer speaks HTTP over
# urllib rather than a vendor SDK.
FORBIDDEN = ("pandas", "numpy", "streamlit", "matplotlib", "altair",
             "anthropic", "openai", "google.generativeai")

# These reach for pandas by design and are imported only at the boundary.
DATA_BOUND = {"ask.py", "plan.py", "evaluate.py"}


def _kernel_modules():
    """Every module in the kernel, excluding the app and the data adapters."""
    for path in sorted((ROOT / "gaapai").rglob("*.py")):
        if path.name in DATA_BOUND:
            continue
        yield path


def test_importing_the_kernel_pulls_in_nothing_heavy():
    """Import the kernel in a fresh interpreter and see what came with it."""
    code = (
        "import sys, json\n"
        "import gaapai\n"
        "from gaapai import money, semantics, router\n"
        "from gaapai.skills import revenue, leases, inventory, ppe, eps\n"
        "from gaapai.skills import cashflow, tax, statements, ratios\n"
        "from gaapai.core import asc, evidence, registry, timevalue\n"
        "from gaapai.diagrams import mermaid\n"
        f"print(json.dumps([m for m in {FORBIDDEN!r} if m in sys.modules]))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, cwd=ROOT, timeout=120)
    assert out.returncode == 0, out.stderr
    leaked = __import__("json").loads(out.stdout.strip().splitlines()[-1])
    assert not leaked, (
        f"importing the kernel pulled in {leaked}; the kernel must run on the "
        "standard library alone"
    )


def test_a_full_computation_needs_nothing_beyond_the_standard_library():
    code = (
        "import sys, json\n"
        "from gaapai import money\n"
        "from gaapai.skills import revenue\n"
        "r = revenue.five_step_revenue(money('900000'), "
        "[revenue.PerformanceObligation('Licence', money('600000'), progress=1)])\n"
        "assert r.ok, r.checks\n"
        "assert r.workpaper()\n"
        f"print(json.dumps([m for m in {FORBIDDEN!r} if m in sys.modules]))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, cwd=ROOT, timeout=120)
    assert out.returncode == 0, out.stderr
    leaked = __import__("json").loads(out.stdout.strip().splitlines()[-1])
    assert not leaked, f"computing a result pulled in {leaked}"


@pytest.mark.parametrize("path", list(_kernel_modules()), ids=lambda p: p.name)
def test_no_kernel_module_imports_a_data_package_at_module_level(path):
    """A top-level import is a hard dependency; one inside a function is not.

    ``ask``, ``plan`` and ``evaluate`` are excluded: they are the data boundary
    and import pandas inside their functions on purpose.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    offenders = []
    for node in tree.body:                       # module level only
        if isinstance(node, ast.Import):
            offenders += [a.name for a in node.names
                          if a.name.split(".")[0] in FORBIDDEN]
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".")[0] in FORBIDDEN:
                offenders.append(node.module)
    assert not offenders, (
        f"{path.relative_to(ROOT)} imports {offenders} at module level"
    )


def test_the_project_declares_no_required_dependencies():
    """pyproject must keep `dependencies = []`; extras are where the rest live."""
    try:
        import tomllib
    except ModuleNotFoundError:                  # pragma: no cover - py<3.11
        pytest.skip("tomllib needs Python 3.11+")
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == [], (
        "the kernel must have no required dependencies; put them in an extra"
    )
    extras = data["project"]["optional-dependencies"]
    assert {"data", "dev", "app"} <= set(extras), sorted(extras)


def test_the_lockfile_is_in_step_with_pyproject():
    """A stale lock means `uv sync` and `pip install` disagree about versions."""
    lock = ROOT / "uv.lock"
    if not lock.exists():
        pytest.skip("no uv.lock in this checkout")
    text = lock.read_text(encoding="utf-8")
    try:
        import tomllib
    except ModuleNotFoundError:                  # pragma: no cover - py<3.11
        pytest.skip("tomllib needs Python 3.11+")
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    for extra, requirements in data["project"]["optional-dependencies"].items():
        for req in requirements:
            name = req.split(">")[0].split("=")[0].split("[")[0].strip()
            assert f'name = "{name}"' in text, (
                f"{name} (from the '{extra}' extra) is missing from uv.lock; "
                "run `uv lock` and commit the result"
            )
