# gaap-ai

A **deterministic US GAAP layer** for conversational financial analysis: exact-decimal
accounting computations that carry their ASC citation, a semantic layer that decides
which column means revenue in a given industry, a plain-English question engine, and
an optional model that plans calculations the engine then performs.

> **The reference pack is not in this repository.** The router can draw on a
> reference pack distilled from *Wiley GAAP 2020* (64 ASC topic chapters, 20
> specialized industry regimes). That pack is a derivative of a copyrighted book, so
> it is not redistributed here. Everything else runs without it; industry lookups
> return nothing until a pack is installed at `~/.claude/skills/gaap-accounting`.
> See [Reference pack](#reference-pack).

```
question ──► router ──► deterministic subskill ──► workpaper ──► diagram
                └────► reference pack (what the standard requires)
```

## The problem

Ask a language model "what was our Q3 revenue" and it returns a confident number. Nothing in that answer reveals whether ASC 606 was applied correctly, whether the trial balance was in balance, or whether the model simply did arithmetic that looked right. In accounting, **a plausible wrong answer is worse than no answer** — it is unreviewable, and it reads exactly like a correct one.

PandasAI makes this sharper: it asks an LLM to write Python and then executes it. Left alone, the model writes the accounting itself.

## The approach

**The arithmetic does not happen in the model.** It happens in registered Python functions with declared ASC citations. The model's job is reduced to *routing* — choosing which vetted function to call and with what inputs.

Every result carries a **workpaper**: inputs, formula, intermediate steps, the ASC paragraphs relied on, the assumptions asserted, and the GAAP checks that ran.

```
==============================================================================
WORKPAPER  revenue.five_step_revenue
Ref: cd1f904fb27c0a91
==============================================================================

Of the USD 900,000.00 transaction price, USD 663,750.00 is recognised as
revenue and USD 236,250.00 is deferred as a contract liability.

AUTHORITY
------------------------------------------------------------------------------
  ASC 606-10-32-31  Revenue from Contracts with Customers
      The transaction price is allocated to performance obligations in
      proportion to standalone selling prices.
  ...

ASSUMPTIONS AND JUDGEMENTS
------------------------------------------------------------------------------
  SSP -- Implementation: 250,000.00  (estimated)  [ASC 606-10-32-33]

SCHEDULE
------------------------------------------------------------------------------
        obligation   allocated  recognised    deferred
  ----------------  ----------  ----------  ----------
  Software licence  540,000.00  540,000.00        0.00
    Implementation  225,000.00   90,000.00  135,000.00
   Support (12 mo)  135,000.00   33,750.00  101,250.00

GAAP CHECKS
------------------------------------------------------------------------------
  [PASS] Allocated amounts sum to the transaction price [ASC 606-10-32-31]
  [WARN] All standalone selling prices are observable   [ASC 606-10-32-33]
  [PASS] Recognised plus deferred ties to the transaction price
==============================================================================
Status: TIES
==============================================================================
```

## Three design decisions

**Exact decimal money, never floats.** `0.1 + 0.2 != 0.3` in binary floating point, and a trial balance summed in float drifts out of balance within a few hundred thousand rows. Every amount is a `Money` backed by `decimal.Decimal`. A test sums 100,000 one-cent entries and asserts the result is exactly $1,000.00.

**Judgements stay with the preparer.** Whether a promise is distinct, what a standalone selling price is, whether a renewal option is *reasonably certain* of exercise — these are entity determinations, not things to infer from data. Subskills marked `*judgement` take them as explicit arguments and record them as assumptions in the workpaper.

**The kernel has zero dependencies.** Exact money, citations, workpapers, routing, and Mermaid diagrams all run on the standard library. Pandas and PandasAI enter only at the adapter boundary — which is why the kernel runs on Python 3.14 even though PandasAI cannot.

## Layout

```
gaapai/                     the deterministic kernel (stdlib only)
  core/       money, ASC citation catalog, workpapers, registry, present value
  skills/     revenue 606 · leases 842 · inventory 330 · ppe 360 · eps 260
              cashflow 230 · tax 740 · statements 205/210 · ratios
  router.py   question -> subskill + reference, deterministically
  semantics.py which column means what, per industry (the retrieval guard)
  diagrams/   Mermaid generation from results
  adapters/   PandasAI bridge (import-guarded)

  ask.py      plain-English questions -> figures, tables and charts
  plan.py     query plans a model emits and this engine executes
  charts.py   the chart registry (one entry per chart kind)
  assumptions.py  working hypotheses stated in conversation
  entity.py   facts about the entity that no data file contains
  evaluate.py row-rule evaluation and impact measurement
  llm.py      optional, provider-neutral model layer (stdlib HTTP)

devapp/app.py               Streamlit harness: Overview, Ask, Review, Details

skills/gaap-accounting/          reference pack (NOT in this repo -- see below)
tools/                      book extraction and skill generation
extraction/                 segmented source (gitignored: copyrighted)
tests/                      337 tests
examples/demo.py            end-to-end walkthrough
examples/warehouse_question.py  the data-warehouse flow, step by step
```

## Quick start

```bash
pip install -e .
python -m pytest          # 150 passed
python examples/demo.py
```

```python
from gaapai import money
from gaapai.router import route
from gaapai.skills import revenue
from gaapai.diagrams import mermaid

route("is our warehouse lease finance or operating?").explain()
# -> leases.classify_lease  [ASC 842-10-25-2]  + chapters/ch57-leases.md

r = revenue.allocate_transaction_price(
    money("900000"),
    [revenue.PerformanceObligation("Licence", money("600000")),
     revenue.PerformanceObligation("Support", money("400000"), observable=False)],
)
print(r.workpaper())
print(mermaid.allocation_diagram(r))
```

## The reference pack

Built with [book-to-skill](https://github.com/virgiliojr94/book-to-skill) from *Wiley GAAP 2020* (2,286 pages, 610K words). The extractor recovered 64 chapters, 20 industry sections, and 2 appendices; the 20 industry files were then written out in full — scope, core model, subskills, decision-rule tables, thresholds, anti-patterns, and ASC references.

| | |
|---|---|
| ASC topic chapters | 64 |
| Industry regimes | 20 (ASC 912–985) |
| Authored industry content | ~252 KB |
| Validation | `validate_skill.py` clean, `scan_generated_skill.py` clean |

Industries covered: federal government contractors, broadcasters, cable television, casinos, film, music, oil and gas, depository and lending, insurance, investment companies, mortgage banking, title plant, franchisors, not-for-profit, plan accounting, real estate general, retail land, time-sharing, regulated operations, software.

<a name="reference-pack"></a>
### Reference pack

The pack is **not distributed with this repository**. It is synthesised rather than
copied — structure, decision rules and citations in original wording, with no book
text reproduced — but it remains a derivative of a copyrighted work, so publishing it
would be redistribution.

`tools/segment_book.py` and `tools/generate_skills.py` build it from a copy of the
book you own. Install the result at `~/.claude/skills/gaap-accounting`, where
`gaapai.router.default_pack_path()` finds it. Without a pack the kernel, semantics,
question engine, planner and diagrams all work unchanged; only industry reference
lookups come back empty.

### Citations

The ASC catalog carries a `verified` flag. **24 industry references are currently
marked unverified**: their substance came from the reference pack, but the paragraph
numbers have not been checked against the published Codification. They render with an
UNVERIFIED marker and must be confirmed before being relied on. No subskill may cite
an unverified paragraph — a test enforces that; only row rules may.

## Two guards, not one

The subskills stop the model **inventing arithmetic**. That is only half the problem: an exactly-correct ASC 606 allocation of the *wrong revenue figure* is still wrong. So a second guard constrains **retrieval**.

`gaapai.semantics` binds warehouse columns to accounting concepts and, per industry, forbids the columns that look like revenue but are not:

| Industry | Looks like revenue | Actually is |
|---|---|---|
| Casinos (924) | `handle`, `drop` | `net_win` |
| Insurance (944) | `written_premium` | `earned_premium` |
| Film (926) | `ultimate_revenue` | actual revenue by market |
| Software (985) | `arr`, `tcv` | licence / PCS / services |
| Franchisors (952) | `system_wide_sales` | `royalty_revenue` |
| Mortgage banking (948) | `loan_volume` | gain on sale + servicing |
| Oil and gas (932) | `gross_wellhead_value` | net revenue interest |
| General (606) | `gross_bookings`, `gmv` | net of contra, agent = net fee |

The output is an **aggregation contract** injected into the code-generation prompt — bindings, the required SQL shape, forbidden columns, and the ASC citation for each rule. Forbidden columns are removed from the aggregation expression outright, not merely warned about.

```python
from gaapai.adapters import aggregation_contract
print(aggregation_contract(columns=df.columns, industry="film"))
```

```
REQUIRED AGGREGATION SHAPE:
  net revenue = SUM(theatrical_revenue) + SUM(home_video_revenue)
              + SUM(licensing_revenue) - SUM(distributor_discounts)
  EXCLUDE deferred/unearned columns: deferred_revenue

FORBIDDEN AS REVENUE under ASC 926:
  ultimate_revenue   NEVER include in a revenue total
```

See `examples/warehouse_question.py` for the whole flow.

## PandasAI integration

The bridge registers each subskill as a PandasAI skill, so its signature and docstring are injected into the code-generation prompt and its callable is placed in the executor environment. A policy in the agent description states the rules — never compute what a GAAP function covers, never use floats for money, always verify the trial balance first, always surface the workpaper.

```python
from gaapai.adapters import pandasai_bridge as bridge

bridge.tool_descriptions(["revenue"])   # inspect the prompt block on any Python
agent = bridge.build_agent(df, industry="926")   # needs Python 3.11
```

**Environment constraint**: PandasAI 3.0 pins `python = ">=3.8,<3.12"`. On Python 3.12+ `build_agent` raises with an explanation; everything else — kernel, router, diagrams, reference pack — works on any supported version. Use a dedicated 3.11 environment for the agent.

## What is verified, and what is not

**Verified**: 150 tests, with every expected value computed by hand from the standard rather than read back off the implementation. They cover exact-decimal behaviour, allocation residuals, FIFO/LIFO/average, declining balance flooring at salvage, the ASC 360 undiscounted screen, EPS antidilution sequencing, cash flow tie-out, statement articulation, the ASC 740 threshold-not-weighting rule, routing stability, and diagram generation.

**Not verified**: the live PandasAI agent loop has not been run end to end, because PandasAI cannot be installed on this interpreter. The bridge's prompt block and wrapper functions are tested; the agent round-trip is not.

**Scope**: this is study and reference apparatus, not authority. *Wiley GAAP 2020* predates later ASUs — check effective dates. For a conclusion that matters, read the ASC paragraph; the citations tell you which one.

## Copyright

The reference pack contains **synthesised structure, rules, and citations — not the book's text**, following book-to-skill's Quality Rule #7. `extraction/` holds raw extracted text and is gitignored. Skills derived from a copyrighted book should be kept private and not redistributed.
