---
name: gaap-accounting
description: "US GAAP knowledge base distilled from Wiley GAAP 2020, covering all 64 ASC topic chapters and 20 specialized industry regimes. Use when applying US GAAP to revenue, leases, business combinations, financial instruments, income taxes, consolidation, or any industry-specific accounting question (film, insurance, oil and gas, not-for-profit, software, real estate, banking, broadcasting, casinos, franchising, plan accounting), when citing ASC paragraph authority, or when checking an accounting treatment before booking it."
---

<!-- argument-hint: [ASC topic number, industry name, chapter number, or accounting concept] -->

# Wiley GAAP 2020 — Interpretation and Application of GAAP

**Source**: *Wiley GAAP 2020* | **Pages**: ~2,286 | **Chapters**: 64 + 20 industry regimes | **Generated**: 2026-09-04

## How to use this skill

- **By ASC topic** — ask for `ASC 606`, `ASC 842`, `ASC 740`; I read that chapter file.
- **By industry** — ask for `film accounting`, `insurance`, `not-for-profit`, `oil and gas`; I read the industry file. **These are fully written out**, not indexes.
- **By concept** — ask about `technological feasibility`, `variance power`, `prematurity period`, `closed block`; the topic index below routes to the right file.
- **By chapter** — ask for `ch38`.

Chapter files are loaded on demand and cost nothing until read.

---

## The five questions that resolve most GAAP problems

**1. What is the unit of account?** Nearly every hard question is really a unit-of-account question. A performance obligation (ASC 606), a lease component (842), an asset group (360), a reporting unit (350), a phase (970), a film group (926), a portfolio segment (326). Fix the unit before measuring anything — most disputes dissolve once it is settled.

**2. Recognition or measurement?** These fail independently. ASC 606 restrictions affect *classification*, conditions affect *timing*. In ASC 958 the same split decides whether a gift is revenue today or nothing yet. Ask which one the fact pattern moves.

**3. Which threshold applies?** GAAP uses a graded vocabulary, and the words are load-bearing:

| Term | Meaning | Example |
|---|---|---|
| **Remote** | Slight chance | ASC 450 |
| **Reasonably possible** | More than remote, less than likely | ASC 450 disclosure |
| **More likely than not** | > 50% | ASC 740 valuation allowance; ASC 350 qualitative |
| **Probable** | Likely to occur | ASC 450 accrual; ASC 606 collectibility |
| **Reasonably certain** | A high hurdle, deliberately above probable | ASC 842 renewal options |
| **Virtually certain** | Near-absolute | Gain contingencies |

Using "probable" where the standard says "reasonably certain" understates lease terms and liabilities.

**4. Discounted or undiscounted?** A recurring trap. ASC 360 step 1 uses **undiscounted** cash flows to test recoverability, then measures the loss at **fair value**. Discounting in step 1 recognises impairments GAAP does not require. Contrast ASC 410 AROs and ASC 842, which are discounted from the start.

**5. Does the write-down reverse?** Under US GAAP, almost never — and this is where it diverges most from IFRS. Inventory write-downs (330-10-35-14), long-lived asset impairments (360-10-35-20), film cost write-offs (926-20-35-13), broadcast rights (920-350-35-3), and software NRV adjustments (985-20-35-4) all **establish a new cost basis**. IAS 2 and IAS 36 require reversal; US GAAP forbids it.

## Cross-cutting mechanisms worth knowing by name

- **Relative standalone selling price allocation** (606-10-32-31) — the pattern reused for lease components, asset groups, and real estate parcels: allocate the whole across parts in proportion to standalone values, and make the parts tie back to the whole.
- **Effective interest method** — one computation underlying lease liabilities (842), debt discount (835), PIK bonds (946), and financial guarantee premium accretion (944).
- **Forecast/units-of-revenue amortisation** — amortise an asset against the revenue it is projected to earn: film costs (926), software (985, with a straight-line floor), oil and gas (932 units of production).
- **Two-step impairment** — screen, then measure. ASC 360 (undiscounted, then fair value); ASC 926 and 985 use single-step fair value or NRV comparisons instead.
- **Control, not risks and rewards** — the modern recognition trigger across ASC 606 (transfer of control), 810 (consolidation), 842 (right to control use), and 860 (transfers).
- **Substance over form** — an arrangement nominally insurance that is really an investment contract is not insurance (944); a nominal franchise fee is still ASC 606 revenue (952).

---

## Industry regimes (fully written)

Each file gives scope, core model, subskills, decision-rule tables, thresholds, anti-patterns, and ASC references.

| ASC | Industry | Distinctive mechanism |
|---|---|---|
| [912](industries/asc912-federal-government-contractors.md) | Federal government contractors | Convenience terminations; no-cost settlements |
| [920](industries/asc920-broadcasters.md) | Broadcasters | Programme licences as rights purchases; daypart |
| [922](industries/asc922-cable-television.md) | Cable television | Prematurity period (≤ 2 years, irrevocable) |
| [924](industries/asc924-casinos.md) | Casinos | Chip liability; avoidable base jackpots; fixed-odds → ASC 606 |
| [926](industries/asc926-entertainment-film.md) | Film | Individual-film-forecast; 10/20-year ultimate revenue caps |
| [928](industries/asc928-music.md) | Music | Advance royalties recoverable-or-expense |
| [932](industries/asc932-oil-and-gas.md) | Oil and gas | Successful efforts vs full cost; units of production |
| [942](industries/asc942-depository-and-lending.md) | Depository and lending | Regulatory capital disclosure; NCUSIF asset |
| [944](industries/asc944-insurance.md) | Insurance | Short vs long duration; DAC; closed block; ASU 2018-12 |
| [946](industries/asc946-investment-companies.md) | Investment companies | NAV reporting; trade date; ex-dividend date |
| [948](industries/asc948-mortgage-banking.md) | Mortgage banking | Held-for-sale vs investment; servicing retained |
| [950](industries/asc950-title-plant.md) | Title plant | Capitalised and **never amortised** |
| [952](industries/asc952-franchisors.md) | Franchisors | Repossession with vs without refund |
| [958](industries/asc958-not-for-profit.md) | Not-for-profit | Restriction vs condition; joint activities; variance power |
| [960/962/965](industries/asc960-plan-accounting.md) | Plan accounting | Benefit obligation is **not** a liability |
| [970](industries/asc970-real-estate-general.md) | Real estate general | Preacquisition costs; amenities; abandonment |
| [976](industries/asc976-real-estate-retail-land.md) | Retail land | Allowance for contract cancellation |
| [978](industries/asc978-real-estate-time-sharing.md) | Time-sharing | Incidental operations reduce inventory cost |
| [980](industries/asc980-regulated-operations.md) | Regulated operations | Regulator-created assets and liabilities |
| [985](industries/asc985-software.md) | Software | Technological feasibility; greater-of amortisation |

---

## Chapter index

| # | ASC | Topic | # | ASC | Topic |
|---|---|---|---|---|---|
| [01](chapters/ch01-generally-accepted-accounting.md) | 105 | GAAP hierarchy | [33](chapters/ch33-guarantees.md) | 460 | Guarantees |
| [02](chapters/ch02-presentation-of-financial-statements.md) | 205 | Presentation | [34](chapters/ch34-debt.md) | 470 | Debt |
| [03](chapters/ch03-balance-sheet.md) | 210 | Balance sheet | [35](chapters/ch35-distinguishing-liabilities-from-equity.md) | 480 | Liabilities vs equity |
| [04](chapters/ch04-statement-of-shareholder-equity.md) | 215 | Shareholder equity *(stub)* | [36](chapters/ch36-equity.md) | 505 | Equity |
| [05](chapters/ch05-income-statement-reporting.md) | 220 | Income statement / OCI | [37](chapters/ch37-revenue-recognition.md) | 605 | Revenue (legacy) |
| [06](chapters/ch06-statement-of-cash-flows.md) | 230 | Cash flows | [38](chapters/ch38-revenue-from-contracts-with-customers.md) | **606** | **Revenue from contracts** |
| [07](chapters/ch07-notes-to-financial-statements.md) | 235 | Notes | [39](chapters/ch39-other-income.md) | 610 | Other income |
| [08](chapters/ch08-accounting-changes-and-error.md) | 250 | Changes and errors | [40](chapters/ch40-cost-of-sales-and-services.md) | 705 | Cost of sales |
| [09](chapters/ch09-changing-prices.md) | 255 | Changing prices | [41](chapters/ch41-compensation-general.md) | 710 | Compensation general |
| [10](chapters/ch10-earnings-per-share.md) | 260 | Earnings per share | [42](chapters/ch42-compensation-nonretirement-postemployment-benefits.md) | 712 | Postemployment benefits |
| [11](chapters/ch11-interim-reporting.md) | 270 | Interim reporting | [43](chapters/ch43-compensation-retirement-benefits.md) | 715 | Retirement benefits |
| [12](chapters/ch12-limited-liability-entities.md) | 272 | LLEs | [44](chapters/ch44-compensation-stock-compensation.md) | 718 | Stock compensation |
| [13](chapters/ch13-personal-financial-statements.md) | 274 | Personal statements | [45](chapters/ch45-other-expenses.md) | 720 | Other expenses |
| [14](chapters/ch14-risks-and-uncertainties.md) | 275 | Risks and uncertainties | [46](chapters/ch46-research-and-development.md) | 730 | R&D |
| [15](chapters/ch15-segment-reporting.md) | 280 | Segment reporting | [47](chapters/ch47-income-taxes.md) | **740** | **Income taxes** |
| [16](chapters/ch16-receivables.md) | 310 | Receivables | [48](chapters/ch48-business-combinations.md) | **805** | **Business combinations** |
| [17](chapters/ch17-investments-debt-and-equity-securities.md) | 320 | Debt and equity securities | [49](chapters/ch49-collaborative-arrangements.md) | 808 | Collaborative arrangements |
| [18](chapters/ch18-investments-debt-securities.md) | 320 | Debt securities | [50](chapters/ch50-consolidations.md) | **810** | **Consolidation** |
| [19](chapters/ch19-investments-equity-securities.md) | 321 | Equity securities | [51](chapters/ch51-derivatives-and-hedging.md) | **815** | **Derivatives and hedging** |
| [20](chapters/ch20-investments-equity-method-and.md) | 323 | Equity method / JVs | [52](chapters/ch52-fair-value-measurements.md) | 820 | Fair value |
| [21](chapters/ch21-investments-other.md) | 325 | Investments other | [53](chapters/ch53-financial-instruments.md) | 825 | Financial instruments |
| [22](chapters/ch22-financial-instruments-credit-losses.md) | 326 | Credit losses (CECL) | [54](chapters/ch54-foreign-currency.md) | 830 | Foreign currency |
| [23](chapters/ch23-inventory.md) | 330 | Inventory | [55](chapters/ch55-interest.md) | 835 | Interest |
| [24](chapters/ch24-other-assets-and-deferred-costs.md) | 340 | Deferred costs | [56](chapters/ch56-leases.md) | 840 | Leases (legacy) |
| [25](chapters/ch25-intangibles-goodwill-and-other.md) | 350 | Goodwill and intangibles | [57](chapters/ch57-leases.md) | **842** | **Leases** |
| [26](chapters/ch26-property-plant-and-equipment.md) | 360 | PP&E and impairment | [58](chapters/ch58-nonmonetary-transactions.md) | 845 | Nonmonetary transactions |
| [27](chapters/ch27-liabilities.md) | 405 | Liabilities | [59](chapters/ch59-related-party-disclosures.md) | 850 | Related parties |
| [28](chapters/ch28-asset-retirement-and-environmental.md) | 410 | AROs and environmental | [60](chapters/ch60-reorganizations.md) | 852 | Reorganizations |
| [29](chapters/ch29-exit-or-disposal-cost-obligations.md) | 420 | Exit and disposal costs | [61](chapters/ch61-service-concession-arrangements.md) | 853 | Service concessions |
| [30](chapters/ch30-deferred-revenue.md) | 430 | Deferred revenue *(stub)* | [62](chapters/ch62-subsequent-events.md) | 855 | Subsequent events |
| [31](chapters/ch31-commitments.md) | 440 | Commitments | [63](chapters/ch63-transfers-and-servicing.md) | 860 | Transfers and servicing |
| [32](chapters/ch32-contingencies.md) | 450 | Contingencies | [64](chapters/ch64-specialized-industry-gaap.md) | 900s | Specialized industry |

*ASC 215 and ASC 430 are genuine stubs in the source — each simply refers to another topic (ASC 505 and ASC 605-50 respectively).*

## Topic index

- **Abandonment** → ch26, ch29, [970](industries/asc970-real-estate-general.md), [980](industries/asc980-regulated-operations.md)
- **Acquisition costs, deferred (DAC)** → [944](industries/asc944-insurance.md)
- **Advance royalties** → [928](industries/asc928-music.md)
- **Amenities** → [970](industries/asc970-real-estate-general.md), [978](industries/asc978-real-estate-time-sharing.md)
- **Antidilution / diluted EPS** → ch10
- **Asset retirement obligations** → ch28, [980](industries/asc980-regulated-operations.md), [932](industries/asc932-oil-and-gas.md)
- **CECL / credit losses** → ch22, [942](industries/asc942-depository-and-lending.md)
- **Closed block / demutualization** → [944](industries/asc944-insurance.md)
- **Collections (art, treasures)** → [958](industries/asc958-not-for-profit.md)
- **Consolidation, VIEs** → ch50, [958](industries/asc958-not-for-profit.md), [978](industries/asc978-real-estate-time-sharing.md)
- **Contract asset / liability** → ch38
- **Contributions, restrictions vs conditions** → [958](industries/asc958-not-for-profit.md)
- **Deferred tax, valuation allowance** → ch47
- **Endowments, UPMIFA** → [958](industries/asc958-not-for-profit.md)
- **Fully benefit-responsive contracts** → [946](industries/asc946-investment-companies.md), [960](industries/asc960-plan-accounting.md)
- **Guaranty funds** → [944](industries/asc944-insurance.md)
- **Impairment, long-lived assets** → ch26, ch25
- **Internal replacement (insurance)** → [944](industries/asc944-insurance.md)
- **Inventory, LCNRV vs LCM** → ch23
- **Joint activities / joint costs** → [958](industries/asc958-not-for-profit.md)
- **Leases, classification and measurement** → ch57, ch56
- **Master trusts** → [960](industries/asc960-plan-accounting.md)
- **Prematurity period** → [922](industries/asc922-cable-television.md)
- **Principal vs agent** → ch38
- **Regulatory assets and liabilities** → [980](industries/asc980-regulated-operations.md)
- **Reinsurance** → [944](industries/asc944-insurance.md)
- **Segment reporting** → ch15
- **Servicing rights** → [948](industries/asc948-mortgage-banking.md), ch63
- **Split-interest agreements** → [958](industries/asc958-not-for-profit.md)
- **Successful efforts vs full cost** → [932](industries/asc932-oil-and-gas.md)
- **Technological feasibility** → [985](industries/asc985-software.md)
- **Time-sharing intervals** → [978](industries/asc978-real-estate-time-sharing.md)
- **Ultimate revenue** → [926](industries/asc926-entertainment-film.md)
- **Variance power** → [958](industries/asc958-not-for-profit.md)
- **Variable consideration and the constraint** → ch38

## Supporting files

- [cheatsheet.md](cheatsheet.md) — decision rules, thresholds, and the traps worth memorising
- [glossary.md](glossary.md) — key terms with their topic
- [patterns.md](patterns.md) — reusable computational patterns across topics

---

## Scope and limits

Covers *Wiley GAAP 2020* as published, so it predates later ASUs — **verify effective dates before relying on any conclusion.** ASU 2018-12 (insurance long-duration contracts) is described but was not yet effective in the source.

This skill contains **synthesised structure, rules, and citations — not the book's text**. It is study and reference apparatus, not authority. For an accounting conclusion that matters, read the ASC paragraph itself; the citations here tell you exactly which one.

Two extraction gaps to be aware of: formula images in the source PDF did not survive text extraction (noted in [922](industries/asc922-cable-television.md)), and the ASC 900-series chapter was reconstructed by section boundaries.
