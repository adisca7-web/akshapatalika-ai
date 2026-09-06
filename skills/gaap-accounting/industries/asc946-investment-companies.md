# ASC 946 — Financial Services: Investment Companies

> Industry skill distilled from *Wiley GAAP 2020*, ch. 64 (Specialized Industry GAAP).
> Rules and structure synthesised locally; no source text reproduced.

**An investment company pools shareholders' funds** to provide professional investment management: selling capital shares to the public, investing the proceeds in securities, and distributing net income and net realised gains to shareholders.

Types include management investment companies (open-end/mutual funds, closed-end funds, special-purpose funds, venture capital companies, small business investment companies, business development companies), unit investment trusts, collective trust funds, investment partnerships, certain life insurance separate accounts, and offshore funds.

---

## Core model

Investment company accounting inverts the normal reporting objective. A commercial entity reports the results of *operating* assets; an investment company reports the **net asset value available to each shareholder**, because that is the price at which investors transact. Everything follows from that:

- Investments are carried at **fair value**, not cost or equity method.
- Transactions are recorded on **trade date**, so the statements reflect every trade entered into as of the reporting date.
- Dividend income and dividends payable are recorded on the **ex-dividend date**, because that is when market price and shareholder entitlement change.

Consolidation and equity-method accounting, which would obscure NAV, are displaced.

---

## Subskills

### 1. Assess investment company status
**All entities regulated under the Investment Company Act of 1940 are in scope.** Others must assess their characteristics, considering the entity's purpose and design.

**Fundamental characteristics** — all four required (ASC 946-10-15-6). The entity:
1. Obtains funds from one or more investors.
2. Provides those investors with **investment management services**.
3. **Commits to its investors** that its business purpose and only substantive activities are investing the funds **solely for returns from capital appreciation, investment income, or both**.
4. Does **not** obtain, or have the objective of obtaining, returns or benefits from an investee or its affiliates that are **not normally attributable to ownership interests**, or that are other than capital appreciation or investment income.

The fourth criterion is the real gate. A holding company that takes strategic or operational benefit from its investees fails it, however diversified the portfolio.

**Typical characteristics** — indicative, not required (946-10-15-7): more than one investment and one investor; investors not related parties of the parent or investment manager; ownership interests in **equity or partnership** form; substantially all investments managed on a **fair value** basis. An entity lacking one or more may **still** be an investment company (946-10-15-8).

**Change in status** (946-10-15-5) — deliberately asymmetric:

| Transition | Accounting |
|---|---|
| **Becoming** an investment company | Account for the effect **from the date of the change**, as a **cumulative effect adjustment** |
| **Ceasing** to be one | Discontinue the guidance; account for the effect **prospectively** under other topics |

### 2. Apply the core accounting policies
- **Trade date** recording of security purchases and sales (946-320-25-1).
- **Fair value** for investment securities, per ASC 825 (946-320-35-1).
- **Ex-dividend date** for dividend income **and** for the liability for dividends payable (946-320-25-4). Rationale: market price reflects exclusion of the declared dividend, and fund shares are bought and redeemed at prices based on NAV — investors buying between declaration and ex-dividend are entitled to the dividend; those buying after are not.
- **Equalization** (open-end funds): NAV per share comprises par value, undistributed income, and paid-in capital and other surplus. On a sale of shares, the per-share undistributed income is **credited to an equalization account**; on repurchase the account is **charged**. This keeps distributions per share stable as the share count changes.

Policies are also shaped by the SEC, the Small Business Administration, and Subchapter M of the Internal Revenue Code.

### 3. Account for high-yield and defaulted debt
**Step bonds** pay no interest for a period after issuance, then a stipulated rate, then a higher rate, and so on to maturity — combining zero-coupon and current-interest features. **PIK bonds** pay some or all interest in other debt instruments ("baby" bonds), which may themselves pay in kind; all babies mature at the parent bond's due date.

For PIK and step bonds (946-320-35-10 through 35-13):
- Use the **interest method** to determine interest income.
- Establish a **reserve against income** for interest income **not expected to be realised**.
- **Cost plus any discount must not exceed undiscounted future cash collections.**

For defaulted securities (946-320-35-14 through 35-18) — note carefully which items hit income and which do not:

| Item | Treatment |
|---|---|
| Interest receivable written off that **had been recognised as income** | **Reduction of income** |
| Write-off of **purchased** interest | **Increases the cost basis**; an **unrealised loss** until the security is sold |
| **Capital infusions** | Addition to cost basis |
| Related **workout expenditures** | **Unrealised losses** |
| Ongoing expenditures to **protect the value** of the investment | **Operating expenses** |

### 4. Claim the cash flow statement exemption
An investment company is exempt from providing a statement of cash flows only if **all** conditions are met (ASC 230-10-15-4):
- Investments are carried at fair value and classified as **Level 1 or Level 2** under ASC 820.
- The entity had **little or no debt**, based on average debt outstanding relative to average total assets.
- The entity provides a **statement of changes in net assets**.

Level 3 holdings or meaningful leverage defeat the exemption.

### 5. Taxes
An investment company that **distributes all taxable income and taxable realised gains** qualifying under **Subchapter M** need not record a provision for federal income taxes. If it does not distribute all of them, record a liability **at the end of the last day of the taxable year** — because only shareholders of record at that date are entitled to credit for taxes paid.

### 6. Presentation and specialised disclosures
- **Commodity pools**: investment partnerships that are commodity pools subject to the Commodity Exchange Act must include a **schedule of investments**, notwithstanding the rapid turnover typical of such pools (946-210-50-4).
- **Foreign currency**: transactions denominated in a foreign currency are **originally measured in that currency** (946-830-45-2). Reporting exchange rate gains and losses **separately** from gain or loss due to market price change is **allowable but not required** (946-830-45-4).
- **Nonpublic investment partnerships** exempt from SEC registration (946-210-50-6): include a **condensed schedule of securities** categorised by **type, country or geographic region, and industry**; disclose pertinent information on investments **greater than 5% of net assets**; and **aggregate** holdings below that threshold. Present the statement of operations in conformity with public company requirements, and present **management fees with their computation disclosed**.
- **12b-1 plans** (946-20-25-4): funds with enhanced 12b-1 or board-contingent plans where the board has committed to pay costs must **recognise a liability and related expense for the excess costs**, because the fund has assumed an obligation to pay the 12b-1 fee after plan termination to the extent the distributor has excess costs. **Discount** at an appropriate current rate if amount and timing are reliably determinable and distribution costs are not subject to a reasonable interest charge.

### 7. Fully benefit-responsive investment contracts
A contract is **fully benefit-responsive** only if **all five** conditions are met (946-210-20):
1. Negotiated **directly** between the fund and the issuer, and it **prohibits assignment or sale** of the contract or its proceeds without the issuer's consent.
2. Either (a) repayment of principal and interest credited to participants is **guaranteed by the issuer**, or (b) the fund provides **prospective interest crediting rate adjustments** on a designated pool, with the crediting rate **never below zero** and that below-zero risk transferred to a financially responsible third party through a **wrapper contract**. If an event occurs — such as a decline in creditworthiness of the issuer or wrapper provider — that may affect realisation of full contract value, the contract **ceases to be fully benefit-responsive**.
3. Terms require **all permitted participant-initiated transactions to occur at contract value** with no conditions, limits, or restrictions (withdrawals for benefits, loans, transfers within the plan).
4. Events limiting the fund's ability to transact at contract value with the issuer — premature termination, plant closings, layoffs, plan termination, bankruptcy, mergers, early retirement incentives — must be **probable of not occurring**.
5. The fund must allow participants **reasonable access to their funds**.

**Presentation** (946-210-45-15): report separately, at **fair value**, the investments (including guaranteed investment contracts) and the **wrapper contracts**, plus an **additional account bringing total assets to contract amounts** — the amounts at which participants can transact.

**Per-contract disclosures**, reconciled to the balance sheet (946-210-45-18): fair value of the wrapper and of each corresponding underlying investment; the **adjustment from fair value to contract value**; and **major credit ratings** of the issuer or wrapper provider.

**Expanded disclosures** (946-210-50-14): the nature and operation of the contracts and the crediting-rate methodology, including key influencing factors, reset basis and frequency, and any minimum rate; a **reconciliation of the beginning and ending difference** between net assets at fair value and at contract value, split between the change in that difference and the effect of contracts entering or leaving fully benefit-responsive status; **average yield** both without regard to and adjusted for the rate actually credited to participants; and **two sensitivity analyses** over the next four reset dates — one with immediate hypothetical market yield changes of at least **one-quarter and one-half of the current yield**, and one combining those with an **immediate hypothetical 10% decrease in net assets** from participant transfers. Also describe the events limiting contract-value transactions with a statement of whether they are probable, and the events allowing issuers to terminate and settle at other than contract value.

**Scope limit** (946-210-45-18A): any portion of net assets **not** held by participants in qualified employer-sponsored defined-contribution plans as of the effective date **may not increase** through gross contributions, loan repayments, or transfers into the fund.

---

## Decision rules

| If | Then | Authority |
|---|---|---|
| Entity is regulated under the 1940 Act | **In scope** automatically | 946-10-15-6 |
| Entity obtains non-ownership benefits from investees | **Fails** the fundamental characteristics | 946-10-15-6 |
| Entity lacks a typical characteristic | May **still** be an investment company | 946-10-15-8 |
| Entity **becomes** an investment company | **Cumulative effect** adjustment from the date of change | 946-10-15-5 |
| Entity **ceases** to be one | **Prospective** accounting | 946-10-15-5 |
| Recording a securities trade | **Trade date** | 946-320-25-1 |
| Recording dividend income or payable | **Ex-dividend date** | 946-320-25-4 |
| Holding step or PIK bonds | Interest method; reserve unrealisable interest; cap cost+discount at undiscounted collections | 946-320-35-10/13 |
| Writing off previously recognised interest | **Reduce income** | 946-320-35-17 |
| Writing off **purchased** interest | Increase cost basis; unrealised loss until sale | 946-320-35-18 |
| Making a capital infusion into a defaulted issuer | Add to cost basis | 946-320-35-14 |
| Incurring workout expenditures | **Unrealised loss** | 946-320-35-15 |
| Incurring costs to protect investment value | **Operating expense** | 946-320-35-16 |
| Holding Level 3 investments or meaningful debt | **No** cash flow statement exemption | 230-10-15-4 |
| Distributing all taxable income under Subchapter M | No federal tax provision | — |
| Retaining taxable income | Liability at the **last day of the taxable year** | — |
| Board committed to pay 12b-1 excess costs | Recognise liability and expense; discount if determinable | 946-20-25-4 |
| Issuer or wrapper creditworthiness declines | Contract is **no longer** fully benefit-responsive | 946-210-20 |

---

## Anti-patterns

- **Consolidating investees or applying the equity method.** Investment companies carry investments at fair value; consolidation would defeat NAV reporting.
- **Recording dividends on the record or payable date.** Ex-dividend date governs both income and the payable.
- **Settlement-date accounting for trades.** Trade date is required so the statements capture all trades entered into.
- **Treating a strategic holding company as an investment company** where it takes benefits beyond capital appreciation and investment income.
- **Applying prospective treatment on becoming an investment company.** Entry is a cumulative effect adjustment; only exit is prospective.
- **Accruing full interest on PIK and step bonds** without a reserve for amounts not expected to be realised, or letting cost plus discount exceed undiscounted future collections.
- **Running all defaulted-security costs through income.** Workout expenditures are unrealised losses; only value-protection costs are operating expenses.
- **Omitting the cash flow statement** while holding Level 3 investments or meaningful leverage.
- **Continuing fully benefit-responsive treatment** after a creditworthiness event.

---

## Key terms

- **Net asset value per share** — net assets attributable to each share of capital stock (other than senior equity securities) outstanding at period close. **Excludes** the effects of assuming conversion of outstanding convertibles, whether or not dilutive.
- **Front-end load** — a sales commission or charge payable at the time of purchase of mutual fund shares.
- **Equalization** — the practice of crediting/charging per-share undistributed income to an equalization account on share sales and repurchases.
- **Step bonds** — pay no interest for a period, then escalating stipulated rates to maturity.
- **PIK bonds** — pay interest in other debt instruments ("baby" bonds) maturing with the parent bond.
- **Wrapper contract** — transfers the risk of a crediting rate falling below zero to a financially responsible third party.

---

## ASC references cited

- **ASC 946-10** — 15-5 (change in status), 15-6 (fundamental characteristics), 15-7 (typical characteristics), 15-8 (entities lacking a characteristic)
- **ASC 946-20** — 25-4 (12b-1 and board-contingent plans)
- **ASC 946-210** — 20 (fully benefit-responsive conditions), 45-15, 45-18, 45-18A (presentation and scope limit), 50-4 (commodity pools), 50-6 (condensed schedule of securities), 50-14 (expanded disclosures)
- **ASC 946-320** — 25-1 (trade date), 25-4 (ex-dividend date), 35-1 (fair value), 35-10 to 35-13 (PIK and step bonds), 35-14 to 35-18 (defaulted securities)
- **ASC 946-830** — 45-2, 45-4 (foreign currency)
- **Cross-topic** — ASC 230-10-15-4 (cash flow exemption), ASC 820 (fair value hierarchy), ASC 825 (financial instruments), ASC 810 (consolidation — displaced), IRC Subchapter M

## Related skills

- `asc960-plan-accounting` — shares the fully benefit-responsive contract concepts
- `asc942-depository-and-lending`, `asc944-insurance` — sibling financial services regimes
- Core topics: `ch52` ASC 820 (fair value), `ch53` ASC 825 (financial instruments), `ch50` ASC 810 (consolidation), `ch06` ASC 230 (cash flows)

## Source

- Segment: `industries/asc946-financial-services-investment-companies.txt` (2,647 words)
