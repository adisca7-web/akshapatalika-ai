# Patterns — reusable computational machinery

GAAP reuses a small number of computations under many names. Recognising the pattern tells you the mechanics before you read the topic.

## Relative-value allocation

**When to use**: a single amount must be split across parts — transaction price across performance obligations (606-10-32-31), consideration across lease components (842), project cost across parcels (970-360-30-1), package cost across programmes (920-405-30-1), amenity cost across benefited parcels (970-340-25-10).

**How**: allocate in proportion to each part's **standalone** value. Where standalone values aren't observable, estimate them, maximising observable inputs; where estimation is impractical, fall back to a physical measure (square footage, units).

**Trade-off**: proportional shares almost never land on whole cents, so rounding creates a residual. The standard requires the **entire** amount to be allocated, so use largest-remainder — round every share down, then distribute the leftover units to the largest truncated remainders. The parts then tie to the whole exactly, deterministically.

**Watch for**: a discount allocated entirely to specific obligations when evidence supports it (606-10-32-37); allocation by relative **fair value** before construction but relative **sales value** for construction costs (970).

## Effective interest amortisation

**When to use**: any obligation or asset where a discount unwinds over time — lease liabilities (842-20), debt discount and premium (835), PIK and step bonds (946-320), financial guarantee premium receivable (944-310-30-2), ASC 606 significant financing components, ARO accretion (410-20).

**How**: interest for the period equals the opening balance times the periodic rate; the payment less interest reduces principal.

**Trade-off / trap**: **payment timing changes the answer.** With an annuity due — the norm for lease payments — the payment lands at the *start* of the period and reduces the balance *before* interest accrues on it. Applying ordinary-annuity mechanics to a lease overstates the liability by roughly one period's interest. Getting this ordering wrong is the most common lease schedule defect.

## Forecast (units-of-revenue) amortisation

**When to use**: an asset whose earning pattern is front-loaded and uncertain — film costs and participations (926-20-35-1), software for sale (985-20-35-1), record masters (928-340-35-2), oil and gas reserves on units of production (932-360-35-3).

**How**:
```
expense = (current period revenue ÷ remaining estimated total revenue
           at the beginning of the fiscal year) × unamortised balance
```

**Trade-off**: yields a constant profit rate, which straight-line cannot for front-loaded assets. But it depends entirely on the denominator, so the standards fence it in — ASC 926 caps ultimate revenue at 10 years (20 for acquired libraries) and excludes unproven technologies; ASC 985 imposes a **straight-line floor** and takes the **greater** of the two methods.

**On revision**: reset the denominator to remaining revenue at the **beginning of the year of change**, leave the numerator (actual results) alone, and put the catch-up in the **period of revision**. Prospective, never restated.

## Two-step impairment

**When to use**: long-lived assets held and used (360-10-35-17), and by reference from 950-350-35-3, 932, and 980.

**How**: **Step 1** compares carrying amount to the sum of **undiscounted** future cash flows. Pass and you stop — no impairment, even if fair value is below carrying amount. Fail and **step 2** measures the loss as carrying amount less **fair value**.

**Trade-off**: the undiscounted screen deliberately tolerates economic impairment that a discounted test would catch, trading precision for reduced volatility and preparer subjectivity.

**Variants**: ASC 926 and 985 skip the screen — single-step fair value or NRV comparison. ASC 932 unproved properties use a **reserve-level** model, not ASC 350.

## Threshold test vs probability weighting

**When to use**: any "more likely than not" or "probable" determination.

**How**: a threshold test is **binary**. ASC 740-10-30-5 asks whether realisation of a deferred tax asset is more likely than not; if yes, no valuation allowance, if no, reduce to the portion that *is*. It does **not** mean multiplying the DTA by a probability.

**Contrast** with genuine probability weighting: ASC 606-10-32-8 expected-value variable consideration, and the ASC 360 expected cash flow approach, both of which do probability-weight outcomes.

**Trap**: scaling a balance by a probability where the standard states a threshold — a common and material error.

## Recognise losses now, gains on realisation

**When to use**: asymmetric recognition appears deliberately across topics.

| Situation | Loss | Gain |
|---|---|---|
| Debt-equity swap (942-310-35-5/6) | On agreement date | Only in **unrestricted cash** |
| Broadcast affiliation replacement (920-350-40-1) | Recognised | **Never** |
| Loss contracts (606, 985-605) | Immediately and in full | — |
| Servicing sold at a loss (948) | Accrue at sale date | — |
| Incidental operations (970-340-25-12) | Expensed as incurred | **Reduces capitalised cost** |

**Why**: conservatism where the measurement is soft and management has an incentive to be optimistic.

## Presumption plus rebuttal criteria

**When to use**: where a preparer incentive runs against faithful reporting, standards start from an adverse presumption and require specific criteria to overcome it.

**Examples**: NFP joint activities are presumed **entirely fund raising** unless purpose, audience, **and** content are all met, each with sub-tests (958-720-45-29). Development costs are presumed **R&D** until technological feasibility criteria are met (985-20-25-1). Ambiguous donor stipulations are presumed **conditional** (958-605). An insurance contract with mortality risk varying with capital markets is **presumed** to carry significant mortality risk (944-20-15-26).

**How to apply**: enumerate the criteria and test each explicitly. Failing one sub-test usually fails the whole criterion, and the presumption stands.

## Time-boxed hybrid accounting

**When to use**: an asset that is simultaneously under construction and in service — cable systems in the prematurity period (922-360), and by analogy real estate projects partly occupied (970-340-25-18).

**How**: fix the window in advance, split costs between current operations (expensed) and future operations (capitalised) using a ratio recomputed each period, then revert to normal accounting when the window closes.

**Trade-off**: the window must be **irrevocable** or the mechanism fails — an operator that could extend it when a build ran late would capitalise indefinitely. ASC 922 presumes ≤ 2 years and permits change only in highly unusual circumstances. Real estate uses a bright line instead: tenant improvements complete **or one year** after major construction.

## Look-through vs consolidate

**When to use**: an entity holds an interest in another entity.

**How**: consolidation is not automatic on control. ASC 958-810 gives the clearest matrix — majority voting ownership consolidates; board control **with** an economic interest consolidates; board control **without** one **prohibits** consolidation. ASC 978-810-25-3 looks *through* a legally required, debt-free, interval-only VIE and presents unsold interests as **inventory**. ASC 946 displaces consolidation entirely so NAV stays visible.

**Principle**: consolidation is a presentation choice serving the statement's user. Where consolidating would obscure the number the reader came for — NAV, or a developer's saleable inventory — GAAP looks through instead.

## Articulation and tie-out

**When to use**: before reporting any figure derived from a data set.

**How**: debits equal credits; assets equal liabilities plus equity; net income flows to retained earnings and rolls forward; the cash flow statement ties to the change in cash (230-10-45-24); allocated parts sum to the whole; amortisation schedules reach zero at term end.

**Why it matters more than it looks**: these are the only checks that catch a *silently* wrong answer. A figure computed from an unbalanced trial balance is confidently wrong and reads exactly like a right one.
