#!/usr/bin/env bash
# Set up the development environment on macOS or Linux.
#
#   bash scripts/setup.sh
#
# Creates .venv from uv.lock, so every machine gets byte-identical dependency
# versions, then runs the test suite to prove the environment works before you
# start changing things.

set -euo pipefail
cd "$(dirname "$0")/.."

printf '\nAkshapatalika AI - development setup\n\n'

# -- uv ---------------------------------------------------------------------
# uv manages both the interpreter and the packages, so a contributor does not
# need a matching Python already installed.
if ! command -v uv >/dev/null 2>&1; then
    printf 'uv is not installed. Install it with:\n\n'
    printf '    curl -LsSf https://astral.sh/uv/install.sh | sh\n\n'
    printf 'then run this script again.\n'
    exit 1
fi
printf '  uv          %s\n' "$(uv --version)"

# -- interpreter + packages -------------------------------------------------
# .python-version pins 3.11; uv downloads it if this machine lacks it.
printf '  syncing     .venv from uv.lock ...\n'
uv sync --extra app --extra dev --quiet

PY=".venv/bin/python"
printf '  python      %s\n' "$("$PY" -c 'import sys; print(sys.version.split()[0])')"

# -- prove it works ---------------------------------------------------------
printf '  tests       running ...\n'
"$PY" -m pytest -q

printf '\nReady.\n\n'
printf '  Start the app     .venv/bin/python -m streamlit run devapp/app.py --server.address localhost\n'
printf '  Run the tests     .venv/bin/python -m pytest\n'
printf '  Try the kernel    .venv/bin/python examples/demo.py\n\n'
