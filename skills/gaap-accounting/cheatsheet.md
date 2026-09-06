# Cheatsheet — US GAAP decision rules

Judgment calls and thresholds, not definitions. For terms see [glossary.md](glossary.md).

## Probability vocabulary — the words are load-bearing

| Term | Rough threshold | Where it bites |
|---|---|---|
| Remote | Slight | ASC 450 — no accrual, no disclosure |
| Reasonably possible | > remote, < likely | ASC 450 — disclose, don't accrue |
| **More likely than not** | **> 50%** | ASC 740 valuation allowance; ASC 350 qualitative screen |
| **Probable** | Likely to occur | ASC 450 accrual; ASC 606 collectibility; ASC 410 |
| **Reasonably certain** | **Deliberately above probable** | ASC 842 renewal and purchase options |
| Virtually certain | Near-absolute | Gain contingencies |

**Trap**: applying "probable" to an ASC 842 renewal option understates the lease term and liability.

## Discounted or undiscounted?

| Test | Cash flows |
|---|---|
| ASC 360 step 1 — recoverability | **Undiscounted** |
| ASC 360 step 2 — measure the loss | Fair value |
| ASC 410 AROs | Discounted, then accreted |
| ASC 842 lease liability | Discounted |
| ASC 926 ultimate revenue | **Undiscounted**, unless ASC 606 financing |
| ASC 946 PIK/step bonds ceiling | **Undiscounted** future collections |

**Trap**: discounting in ASC 360 step 1 books impairments GAAP does not require.

## Does a write-down reverse?

**Under US GAAP: essentially never.** The reduced amount is a new cost basis.

| Item | Authority |
|---|---|
| Inventory | 330-10-35-14 |
| Long-lived assets | 360-10-35-20 |
| Film costs | 926-20-35-13 |
| Broadcast programme rights | 920-350-35-3 |
| Software NRV | 985-20-35-4 |

IAS 2 and IAS 36 require reversal. This is the sharpest US GAAP / IFRS divergence in routine work.

## Inventory: which lower-of rule?

The **cost flow method picks the rule** — the preparer does not choose.

| Method | Rule | Needs |
|---|---|---|
| FIFO, average | Lower of cost and **NRV** | Selling price − completion/disposal |
| **LIFO, retail** | Lower of cost or **market** | Replacement cost, bounded by NRV ceiling and NRV-less-normal-profit floor |

**Trap**: applying NRV to a LIFO pool is a real misstatement.

## Capitalisation start and stop lines

| Regime | Start | Stop |
|---|---|---|
| Software for sale (985) | Technological feasibility | Available for **general release** |
| Internal-use software | Application development stage | Substantially complete and ready |
| Real estate (970) | Acquisition **probable** | Substantially complete and ready for intended use |
| Rental cost amortisation (970) | — | Tenant improvements done **or 1 year** after major construction |
| Cable plant (922) | — | End of the **prematurity period** (presumed ≤ 2 years, irrevocable) |
| Title plant (950) | — | Usable for title searches; **then never amortised** |
| Film (926) | — | Amortise from **release**, on forecast |
| Oil and gas exploratory well (932) | Drilling | Determination of proved reserves |

## Revenue: the questions in order

1. **Contract?** All five ASC 606-10-25-1 criteria, collectibility **probable**.
2. **Distinct?** Capable of being distinct **and** separately identifiable — defeated by significant integration, significant customisation, or high interdependence.
3. **Transaction price?** Variable consideration (expected value or most likely amount), **constrained** to the amount for which a significant reversal is not probable; adjust for significant financing (> 1 year).
4. **Allocate** on relative standalone selling price; parts must tie to the whole.
5. **Recognise** as control transfers — over time if any of the three criteria, otherwise point in time.

**Principal vs agent**: 2 of 3 control indicators (primarily responsible, inventory risk, pricing discretion) → principal, report **gross**.

## Industry tells — recognise the regime fast

| If you see | Regime | Key move |
|---|---|---|
| "Ultimate revenue", participations, residuals | ASC 926 film | Individual-film-forecast; 10-yr cap (20 for libraries) |
| "Technological feasibility", working model | ASC 985 software | Greater of revenue ratio and straight-line |
| "Prematurity period", head-end, drops | ASC 922 cable | Monthly fraction; subscriber costs are period costs |
| "Daypart", programme licence package | ASC 920 broadcasters | Rights purchase; gross or PV liability |
| Chips, base jackpot, fixed odds | ASC 924 casinos | Fixed odds → **ASC 606**, not ASC 815 |
| Successful efforts, dry hole, G&G | ASC 932 oil and gas | Units of production; reserve-based impairment |
| Closed block, DAC, short/long duration | ASC 944 insurance | Only **successful** acquisition costs capitalise |
| NAV, ex-dividend, equalization | ASC 946 investment cos | Trade date; no consolidation |
| Variance power, donor condition, joint activity | ASC 958 NFP | Condition delays; restriction only classifies |
| Regulatory asset, stranded cost, PCA | ASC 980 / 942 | Regulator creates assets; capital disclosures |
| Interval, floating time, points | ASC 978 time-share | Incidental ops reduce inventory cost |
| Held-for-sale vs investment, servicing retained | ASC 948 mortgage banking | LOCOM via valuation allowance |

## Traps that recur across topics

- **Netting when the standard says gross.** Reinsurance recoverables are assets (944); NFPs report revenues and expenses gross (958); offsetting needs a right of setoff (210-20-45-1).
- **Reallocating costs off a failure.** Abandoned real estate costs may **not** move to other projects (970-360-40-1).
- **Smoothing.** The unearned revenue liability may not level gross profit (944-605-25-6).
- **Incidental operations as income.** They **reduce capitalised cost** (970, 978); they never create profit.
- **Straight-lining a forecast asset.** Film and software amortise against expected revenue (with a straight-line **floor** in software).
- **Treating an avoidable obligation as a liability.** Base jackpots (924); moral-suasion cleanup is not an ARO (410 / 980).
- **Consolidating on control alone.** NFP board control **without** an economic interest **prohibits** consolidation (958-810-25-4).
- **Assuming FAR-allowable equals GAAP-recognisable** (912).
- **Recognising gains symmetrically with losses.** Debt-equity swaps: losses on agreement, gains only in unrestricted cash (942-310-35-5/6). No gain on broadcast affiliation replacement (920-350-40-1).

## Articulation checks before answering anything

1. Debits = credits.
2. Assets = liabilities + equity.
3. Net income flows to retained earnings; retained earnings rolls forward.
4. Cash flow statement ties to the change in cash (230-10-45-24).
5. Allocated parts sum to the whole (606-10-32-31).
6. Schedules amortise to zero at term end.

An answer computed off an unbalanced trial balance is confidently wrong, and nothing in its phrasing reveals that.
