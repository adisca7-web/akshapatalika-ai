# Akshapatalika AI

**Ask questions about your sales data and get accounting answers you can defend.**

Load a spreadsheet or CSV of orders. The app works out which columns mean what,
flags the things that look like revenue but are not, and answers questions in plain
English — with the accounting rule behind every figure.

Nothing here guesses. If it cannot answer something correctly, it says so rather than
producing a number that looks right.

---

## Who this is for

**If you keep the books for a small business**, this reads your sales export and
tells you what your revenue actually is under US accounting rules — which is usually
not the total at the bottom of the file.

**If you are an accountant**, every figure carries its ASC paragraph, a workpaper
showing how it was derived, and an explicit list of the judgements it depends on.
Nothing is adjusted without your approval.

**If you are a developer**, there is a dependency-free Python kernel underneath with
337 tests. Skip to [For developers](#for-developers).

---

## What problem it solves

Here is a real Shopify export of 57 orders. Its `Total` column sums to **32,204.06**.
Reported revenue under US GAAP is **29,723.47**. Here is what the app finds in
between — each one flagged separately, none of it adjusted without your say-so:

| Finding | Amount | Why it matters |
|---|---:|---|
| Sales tax collected | 1,961.54 | Money you owe the tax authority, not income (ASC 606-10-32-2A) |
| Gift cards sold | 500.00 | You owe goods, not earned income, until redeemed (ASC 606-10-45-1) |
| Test line items | 92.00 | Not sales to a customer at all (ASC 606-10-25-1) |
| Refunds given | 2,557.23 | Sits in a contra column, reducing the sale price |
| Shipping charged | 51.91 | Revenue, but a separate obligation — shown on its own line |

It also catches two things about the file itself. `Subtotal + Taxes + Shipping` comes
to 32,328.92 against a `Total` of 32,204.06 — **the export does not foot**, by 124.86.
And `Fulfilled at` has a value in only 1 row out of 81, so delivery date cannot be
used to decide which month a sale belongs in, however much you might want it to.

That is the point. A confident wrong number is worse than no number, because it is
unreviewable and it looks exactly like a right one.

---

## Getting started

You need **Python 3.11 or newer** — that is what this is tested on. ([python.org/downloads](https://www.python.org/downloads/))

**1. Download the code**

```bash
git clone https://github.com/adisca7-web/akshapatalika-ai.git
cd akshapatalika-ai
```

**2. Install what it needs**

```bash
pip install -e ".[app]"
```

**3. Start the app**

```bash
python -m streamlit run devapp/app.py --server.address localhost
```

Your browser opens at `http://localhost:8501`. That is the whole setup — no account,
no API key, no data leaves your computer.

> **On Windows PowerShell**, chain commands with `;` rather than `&&`, which is not a
> valid separator there.

---

## Using the app

### First run

In the sidebar:

1. **Business** — give it a name. Your settings and decisions are saved under it.
2. **What kind of business?** — pick your industry. This matters: what counts as
   revenue for a casino, an insurer, or a film studio are all different things.
3. **Your data** — upload a CSV or Excel file, or paste a path to one.

Then work through four tabs, left to right.

### Overview — what your numbers are

Three figures at the top: **Revenue**, **Excluded by rules**, and **Awaiting your
review**. A chart by month, switchable between bar, line and area.

Below that, **What we found in your file** — every column that carries accounting
meaning, what the app read it as, and the actual total in it. Check this first. If a
column was read wrongly, every figure above it is wrong too, and this is where you
would see it.

It also flags columns too sparse to trust. On the example file it caught that
`Fulfilled at` had a value in only 1 row out of 81 — so you cannot use delivery date
to decide which month a sale belongs to, however much you might want to.

### Review — decisions only you can make

The app can spot a gift card in your data. It cannot decide whether you agree it
should come out of revenue. That is your call as the preparer, so it asks:

> **Gift card sales** · Needs your decision
> Gift card sales are a contract liability, not revenue. Revenue arises on
> redemption.
> *Why: ASC 606-10-45-1*
> **500.00** across 12 lines
> `Exclude from revenue`  `Keep in revenue`

Nothing changes until you press a button. An item you have not decided on is
reported as pending and **left out of the adjustment**, so you always know which
figure you are looking at.

Your decisions are saved to `~/.gaapai/entities/` and reload next time.

### Ask — questions in plain English

Type a question, get a figure, a table and a chart.

| Ask this | You get |
|---|---|
| *What is my revenue?* | The total, after your approved adjustments |
| *Show revenue by month* | A table and chart by month |
| *What did you exclude and why?* | Every adjustment, its amount and its ASC rule |
| *How much sales tax did I collect?* | The tax total, with each tax column broken out |
| *How much was refunded?* | Refunds, plus a note that expected returns also matter |
| *What are my top products?* | Ranked by line value |
| *How many orders did I have?* | Order count, not row count — they differ |
| *What is my average order value?* | Revenue ÷ orders |
| *Cost of goods is 50% of revenue* | Noted as your assumption |
| *Show profitability by month* | Revenue, cost, gross profit and margin |

**Charts.** Ask for a chart type by name — *"revenue by month as a line chart"*, *"a
pie chart of revenue"*, *"top products as a bar chart"*. Or just say *"make it a line
graph"* and it redraws the last answer. Available: bar, line, area, pie, scatter, or
`table` for figures only.

**Assumptions carry forward.** Tell it *"cost of goods is 50% of revenue"* once and
it applies to every profit question afterwards, with a banner showing what is in
force. Say *"gross margin is 40%"* and it recalculates. Anything derived from an
assumption is labelled an estimate, not your books.

### Details — the workings

Four sub-tabs: your entity settings, how each column was read, which computation a
question routes to, and the catalog of everything the system knows.

**Your settings** is worth a visit. It asks six things no data file can tell it —
which date counts as the sale, whether you run a calendar or 4-5-4 year, whether
customers can return goods and over what window, how you present sales tax, and
which column marks intercompany sales. Until you answer them, the Overview says so.

---

## What it will not do

This is the part that makes the rest trustworthy.

**It will not guess which column is revenue.** If nothing matches, it stops and shows
you how it read each column, rather than picking the largest number.

**It will not forecast.** Ask *"what will revenue be next quarter"* and it declines.
It reports what your data says; projecting is a different exercise.

**It will not compute profit without a cost.** Your file has no cost of sales column,
so it asks for your assumption instead of inventing a margin.

**It will not apply a rule you have not approved.** An unreviewed item reports the
delta it *would* make and changes nothing.

**It will not make an accounting judgement for you.** Whether a promise is distinct,
whether a return is probable, what a standalone selling price is — these are your
determinations. It tells you what the decision depends on and records your answer.

**It will not answer questions it cannot compute exactly** — unless you connect an AI
assistant, and then it labels those answers clearly.

---

## Optional: connecting an AI assistant

Everything above works with no AI and no internet. The trade is coverage: the
built-in engine answers a fixed set of questions exactly, and refuses the rest.

Connect a model and it can also handle open-ended questions. **Sidebar → AI
assistant.** Choose a provider, paste a key, pick a model, press **Test connection**.

Supported: **Anthropic (Claude)**, **OpenAI**, **Google Gemini**, **DeepSeek**,
**Groq**, **OpenRouter**, **Ollama** (local), **LM Studio** (local), or any
OpenAI-compatible endpoint. The local options need no key and no internet.

**The model never produces a number.** It decides *what to calculate* and writes the
formula; the deterministic engine performs the calculation. Ask *"if products cost
50% of the sale price, chart profitability by month"* and the model emits a plan —
take revenue by month, multiply by 0.5 for cost, subtract for gross profit — which
the engine then runs against your data with your approved rules applied. The answer
shows **How this was calculated** with the formulas it chose.

Your key is held in memory for the session only. It is never written to disk.

---

## For developers

### Install

```bash
pip install -e ".[data,dev]"      # kernel + pandas + pytest
pytest                            # 337 tests
```

The library itself supports Python 3.9+; the test suite is run on 3.11 and 3.14.

The kernel itself has **zero dependencies** — exact money, citations, workpapers,
routing and diagram generation all run on the standard library. Pandas enters at the
adapter boundary; the optional model layer uses `urllib`, not a vendor SDK.

### Ask a question in code

```python
import pandas as pd
from gaapai import semantics, ask

df = pd.read_csv("orders.csv")
plan = semantics.plan_aggregation(list(df.columns), industry="retail")

answer = ask.answer("show revenue by month", df, plan,
                    ratified=["gift_card_sales", "test_orders"])
print(answer.headline)     # 29,723.47 total
print(answer.table)
print(answer.citations)    # ['606-10-45-1', '606-10-25-1']
```

### Compute something with a workpaper

```python
from gaapai import money
from gaapai.skills import revenue

result = revenue.five_step_revenue(
    money("900000"),
    [revenue.PerformanceObligation("Licence", money("600000"), progress=1)],
)
print(result.workpaper())   # inputs, authority, schedule, GAAP checks, fingerprint
```

Every result carries its ASC paragraphs, the assumptions asserted, the checks that
ran, and a SHA-256 fingerprint of inputs and output.

### Layout

```
gaapai/
  core/          exact Money, ASC citation catalog, workpapers, registry
  skills/        ASC 606 · 842 · 330 · 360 · 260 · 230 · 740 · 205/210 · ratios
  semantics.py   which column means revenue, per industry, plus row-level rules
  evaluate.py    row-rule impact, measured and fail-closed
  entity.py      facts no data file contains, asserted once and versioned
  ask.py         plain-English questions -> figures, tables, charts
  plan.py        query plans a model emits and this engine executes
  charts.py      the chart registry — one entry per chart kind
  assumptions.py working hypotheses stated in conversation
  llm.py         optional, provider-neutral model layer
  router.py      question -> subskill + reference material
  diagrams/      Mermaid generation from results

devapp/app.py    the Streamlit app
skills/gaap-accounting/   the reference pack
tests/           337 tests
```

### The two guards

Subskills stop a model **inventing arithmetic**. That is half the problem: an
exactly-correct ASC 606 allocation of the *wrong revenue figure* is still wrong. So
`gaapai.semantics` constrains **retrieval** — binding columns to accounting concepts
and forbidding, per industry, the ones that look like revenue but are not:

| Industry | Looks like revenue | Actually is |
|---|---|---|
| Casinos (924) | `handle`, `drop` | `net_win` |
| Insurance (944) | `written_premium` | `earned_premium` |
| Film (926) | `ultimate_revenue` | actual revenue by market |
| Software (985) | `arr`, `tcv` | licence / PCS / services |
| Franchisors (952) | `system_wide_sales` | `royalty_revenue` |
| Mortgage banking (948) | `loan_volume` | gain on sale + servicing |
| Oil and gas (932) | `gross_wellhead_value` | net revenue interest |
| General (606) | `gross_bookings`, `gmv` | net of contra; agent reports net fee |

Forbidden columns are removed from the aggregation outright, not merely warned about.
33 row-level rules then handle what column names cannot express — gift cards, test
orders, cancellations, unreleased film costs, conditional contributions.

### Adding a chart type

One entry in `gaapai/charts.py` plus one renderer branch. The question parser, the
model's prompt, the plan validator and the renderer all read that registry, so
nothing else needs touching. A plan naming an unregistered kind is rejected rather
than silently drawn as bars.

### Query plans

A model emits JSON; the engine executes it:

```json
{"steps": [{"id": "rev",  "op": "revenue", "by": "month"},
           {"id": "cost", "op": "formula", "expr": "rev * 0.5"},
           {"id": "gp",   "op": "formula", "expr": "rev - cost"}],
 "output": {"kind": "chart", "chart": "line", "series": ["rev", "gp"]}}
```

Operations: `revenue`, `metric`, `count`, `top`, `formula`, `constant`. Formulas are
parsed to an AST and walked against a whitelist — arithmetic, `abs/min/max/round`,
and references to earlier steps only. Attribute access, indexing, imports and other
calls are rejected at parse time, as are unknown operations, unknown chart types and
forward references. Validation runs before execution, so an invalid plan reports why
rather than half-running.

---

## The GaapAccounting reference pack

64 ASC topic chapters and 20 specialized industry regimes, in `skills/gaap-accounting/`.
The router consults it for what a standard *requires*, alongside the subskills that
*compute*.

### Provenance

Distilled from *Wiley GAAP 2020 — Interpretation and Application of Generally
Accepted Accounting Principles* by `tools/segment_book.py` and
`tools/generate_skills.py`. Named for its contents rather than its source; the source
is stated here and in the pack's own `SKILL.md`.

**How original is it?** Measured as verbatim 10-word overlap against the extracted
source text, rather than asserted:

| Part | Size | Overlap |
|---|---|---:|
| `SKILL.md`, `cheatsheet.md`, `patterns.md` | 88 KB | 0.0% |
| `glossary.md` | — | 0.9% |
| `industries/` (20 files) | 308 KB | 3.1% |
| `chapters/` (64 files) | 552 KB | 26.9% |

The industry files and top-level material are original work — scope, core model,
decision-rule tables, thresholds, anti-patterns and ASC references, written out
rather than extracted. The chapter files largely follow the source's heading
structure and section ordering, which is why their overlap is high; treat them as an
index into the standard, not as independent exposition.

No ASC text is reproduced anywhere — the Codification is copyright of the Financial
Accounting Foundation. The raw extracted book text (`extraction/`) is not in this
repository.

The router looks in `./skills/gaap-accounting`, then `~/.claude/skills/gaap-accounting`,
then `~/.agents/skills/gaap-accounting`.

---

## What is verified, and what is not

**Verified.** 337 tests on Python 3.11, 334 on 3.14, with expected values computed by
hand from the standard rather than read back off the implementation. They cover
exact-decimal behaviour, allocation residuals, FIFO/LIFO/average, declining balance
flooring at salvage, the ASC 360 undiscounted screen, EPS antidilution sequencing,
cash flow tie-out, statement articulation, the ASC 740 threshold-not-weighting rule,
row-rule impact, plan validation and formula sandboxing, routing stability, and
diagram generation.

**Not verified.**

- **24 of the 77 ASC citations are marked unverified.** Their substance came from the
  reference pack, but the paragraph numbers have not been checked against the
  published Codification. They render with an `UNVERIFIED` marker. No subskill may
  cite an unverified paragraph — a test enforces that; only row rules may.
- **The AI assistant has not been exercised against a live endpoint.** Plan parsing,
  validation, execution and sandboxing are all tested with realistic model replies.
  How reliably a given model emits *valid* plans in practice is unmeasured.
- **Two row rules overlap.** `gift_card_sales` and `gift_card_structural` can match
  the same lines. Approving both would double-count. Nothing detects this yet.

**Scope.** This is study and reference apparatus, not accounting authority. *Wiley
GAAP 2020* predates later ASUs — check effective dates. For a conclusion that
matters, read the ASC paragraph itself; the citations tell you which one.

---

## Licence

MIT — see [LICENSE](LICENSE). The licence covers the software. It does not cover the
FASB Accounting Standards Codification, which is not reproduced here.
