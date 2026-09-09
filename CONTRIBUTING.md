# Contributing

## Set up

One command, on any platform. It installs the right Python, builds `.venv` from
`uv.lock`, and runs the suite to prove the environment works before you change
anything.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1   # Windows
```

```bash
bash scripts/setup.sh                                        # macOS, Linux
```

Both need [uv](https://docs.astral.sh/uv/), which manages the interpreter as well
as the packages — you do not need a matching Python already installed.

<details>
<summary>Doing it by hand instead</summary>

```bash
uv sync --extra app --extra dev      # .venv, exact versions from uv.lock
uv run pytest                        # 364 tests
```

Or with plain pip, accepting that you get resolved-today versions rather than
locked ones:

```bash
python -m venv .venv && .venv/bin/pip install -e ".[app,dev]"
```
</details>

## Everyday commands

| | |
|---|---|
| Run the tests | `uv run pytest` |
| One file | `uv run pytest tests/test_ask.py -q` |
| Start the app | `uv run streamlit run devapp/app.py --server.address localhost` |
| Lint | `uvx ruff@0.14.2 check .` |
| Check the reference pack | `uv run python scripts/check_pack.py` |
| See the kernel work | `uv run python examples/demo.py` |
| Re-lock after changing deps | `uv lock` — commit `uv.lock` |

On Windows PowerShell, chain commands with `;`. `&&` is a parser error there.

## What CI checks

Every push and pull request runs:

- the suite on **Python 3.11 and 3.14**, on **Ubuntu and Windows** — four combinations;
- **ruff**, pinned so a new release cannot fail an unrelated change;
- the **reference pack** — that it resolves to this checkout rather than a copy
  installed at `~/.claude/skills`, that every file its index names exists, and
  that every ASC paragraph a rule relies on is in the catalog;
- that **the app still imports**. Every test can pass while the app is broken;
  it has happened here, from a scripted edit that wrote a literal `\n` into a
  source line.

## House rules

**Money is `Decimal`, never `float`.** `0.1 + 0.2 != 0.3` in binary floating
point, and a trial balance summed in float drifts out of balance within a few
hundred thousand rows. Use `gaapai.money`.

**The kernel takes no dependencies.** `gaapai/core`, `gaapai/skills`,
`semantics`, `router` and `diagrams` run on the standard library alone. pandas
belongs at the boundary — `ask.py`, `plan.py`, `evaluate.py` — and is imported
inside functions there, not at module level. `tests/test_packaging.py` enforces
this per module, so you will hear about it immediately.

**Every computation returns a `GaapResult`** carrying its inputs, ASC citations,
assumptions, checks, and a fingerprint. A number without its authority is not
reviewable.

**Never invent a citation.** Every ASC reference must resolve through
`gaapai.core.asc.cite()`, which raises on anything uncatalogued. If you are sure
of the requirement but not the paragraph number, add it with `_u()` rather than
`_c()` — it will render as `UNVERIFIED` and cannot back a computation, only a
row rule.

**Judgements belong to the preparer.** Whether a promise is distinct, whether a
return is probable, what a standalone selling price is — take these as explicit
arguments and record them as assumptions. Never infer them from data.

**Fail closed.** When the layer cannot answer something correctly it says so.
A rule that cannot be applied warns; it does not silently do nothing. A plan
that does not validate is rejected whole, not run halfway.

## Tests

Compute expected values **by hand from the standard**, not by running the code
and pasting what it printed. A test written the second way passes forever and
proves nothing — it has already caught a genuinely inverted warranty accrual
here, which a self-derived expectation would have blessed.

Name the bug in the test when you fix one. Several tests here read like
`test_a_bare_chart_request_redraws_the_previous_answer`, with a docstring saying
what went wrong before. That is the point: the next person changing that code
learns why the branch exists.

## Adding things

**A chart type** — one entry in `gaapai/charts.py`, one renderer branch in
`devapp/app.py`. The question parser, the model prompt, the plan validator and
the renderer all read that registry, so nothing else changes.

**A computation** — decorate with `@subskill`, declare its `citations`,
`triggers` and `inputs`, mark it `judgement=True` if it depends on an entity
determination, and return a `GaapResult`.

**A row rule** — add it to `_ROW_RULES` in `gaapai/semantics.py` keyed to an
industry that exists. A key matching no profile raises at import; three rules
once sat dead for weeks because that check was missing.

**A plan operation** — add it to `OPS` in `gaapai/plan.py` and handle it in
`execute()`. The planning prompt is generated from `OPS`, so the model can use
it straight away.

## The reference pack

`skills/gaap-accounting/` is derived from a third-party text and is documented
as such in the README, with the measured overlap per folder. If you regenerate
it, re-run `scripts/check_pack.py` and update those figures rather than leaving
the old ones in place.
