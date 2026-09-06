# ASC 944 — Financial Services: Insurance

> Industry skill distilled from *Wiley GAAP 2020*, ch. 64 (Specialized Industry GAAP).
> Rules and structure synthesised locally; no source text reproduced.

> **Technical alert — ASU 2018-12, Targeted Improvements to Long-Duration Contracts.** Issued August 2018; applies to insurance entities that **issue** long-duration contracts, **not** to policyholders or noninsurance entities. Effective for financial statements issued on or after **1 January 2022** for public business entities and **1 January 2024** for all others (per the October 2019 deferral). It materially changes the model — see "What ASU 2018-12 changes" below.

---

## Core model

Everything in insurance accounting starts with **classifying the contract**, because measurement diverges completely from there:

| Contract type | Includes | Premium revenue |
|---|---|---|
| **Short-duration** | Most property and liability insurance | Recognised **over the contract term in proportion to the amount of insurance provided** (944-605-25-1) |
| **Long-duration** | Most life, mortgage, and title insurance | **Accrued as premiums become due** from policyholders (944-605-25-3) |

**Exception within long-duration**: where benefits are provided over a term **longer than the premium payment term** — a twenty-year life policy paid over ten, say — income is recognised **over the longer benefit period**, not the payment period.

Long-duration subtypes: traditional fixed and variable annuity and life contracts, **universal life-type**, nontraditional fixed and variable annuity and life, participating life, and group participatory pension contracts. **Reinsurance** and **financial guarantee** are separate categories.

**Nominal insurance contracts that are effectively investment contracts are not accounted for as insurance.** Substance governs.

### SAP versus GAAP
Insurance is dual-reported. **Statutory accounting principles (SAP)** — state laws, regulations, and administrative rulings — exist to protect **policyholders**, so they emphasise liquidity and solvency and are deliberately conservative:

| | SAP | GAAP |
|---|---|---|
| Policy acquisition costs | **Written off as incurred** | Capitalised and amortised |
| Nonliquid assets (property, furniture) | **Not recognised** | Recognised |
| Claims liabilities | Very conservatively estimated | Best estimate |
| Perspective | Short-term, solvency | Going concern, net worth |

Wiley's ASC 944 discussion does **not** reflect SAP under the NAIC codification project.

---

## Subskills

### 1. Capitalise only qualifying acquisition costs
**Only two categories may be capitalised** (ASC 944-30-25-1A):
1. **Incremental direct costs of successfully acquiring or renewing** contracts — costs resulting directly from the contract transaction, essential to it, and which would not have been incurred had the acquisition not occurred.
2. Costs **directly related to underwriting, policy issuance, medical and inspection, and sales force contract selling** — again, **for successfully acquired or renewed contracts**.

Everything else is a **period cost**: market research, training, administration, product development. **All administrative expenses are period costs.**

Note the word **successfully**. Costs of failed solicitations are expensed; this is the single biggest constraint on deferred acquisition costs (DAC).

Capitalised acquisition costs are charged to expense **on a constant-level basis** (944-30-35-3A).

### 2. Handle internal replacements
An **internal replacement** modifies an insurance product's benefits, features, rights, or coverages, including by extinguishing and replacing a contract. The question is whether the replacement **continues** the old contract or **extinguishes** it — which decides the fate of unamortised DAC, unearned revenue liabilities, and deferred sales inducement assets.

**Continuation** requires **all six** conditions (944-30-35-37). If **any** fails, the contract is substantially changed:
1. The insured event, risk, or period of coverage **has not changed**.
2. The contract holder's **investment return rights have not changed**.
3. Either **no change in premium**, or a premium reduction **matched by a corresponding reduction in benefits**.
4. **Net of distributions, no net reduction in contract value.**
5. **No change in contractual participation or dividend features.**
6. **No change in the amortisation method or revenue classification.**

| Outcome | Treatment |
|---|---|
| **Continuation** | Unamortised DAC, unearned revenue liabilities, and deferred sales inducements **carry over**; costs of the replacement are **expensed as incurred** (944-30-35-24) |
| **Substantially changed** | Replaced contract is **extinguished**; those balances **may not be deferred** into the replacement (944-30-40-1, 40-2) |

For a continuation: if the contract is a **long-duration participating** contract, the replacement's estimated gross profit **revises** the replaced contract's gross profit for amortisation purposes; if accounted for as **nonrefundable fees**, the replacement's cash flows **revise** the replaced contract's cash flows for interest-rate amortisation.

**Two carve-outs from this guidance entirely:**
- A modification arising from a **contract holder election within the original contract**, provided the election followed the original terms, **is not subject to underwriting**, the insurer **cannot decline coverage or adjust pricing**, and the benefit **has been accounted for since inception** (944-30-35-26).
- A **nonintegrated** contract feature — one priced **solely** for the incremental benefit coverage that **does not alter other components** — is accounted for as a **separately issued contract** (944-30-35-31 to 33).

### 3. Financial guarantee insurance
Contracts protecting the holder of a financial obligation (a municipal bond, an asset-backed security) from loss on default.

**At inception**, recognise a liability for **unearned premium revenue** equal to the **present value of premiums due** — or expected to be collected, if certain criteria are met and used — discounted at the **risk-free rate at inception**, based on the contract period unless prepayments may be considered. **Accrete the discount on the premium receivable through earnings** over that period (944-310-30-2).

- **Update the discount rate to a current risk-free rate only when prepayment assumptions change.** Where an expected period is used, adjust prepayment assumptions when they change; the adjustment to unearned premium revenue **equals** the adjustment to the premium receivable, so **there is no earnings effect** at that time (944-310-35-5).
- An **expected credit loss** on the premium receivable is adjusted under **ASC 326** at amortised cost, **charged against earnings** (944-310-35-6).
- **Revenue** is recognised over the insurance period **in proportion to coverage outstanding**, which typically declines as insured principal is retired.
- **Claim liability**: unearned premium revenue represents the stand-ready obligation at initial recognition. If default likelihood later rises such that the **present value of expected net cash outflows exceeds the declining unearned premium revenue**, recognise a **claim liability in addition to** the unearned premium revenue (944-40-25-42). Update it for new information and discount at an **updated risk-free rate for each balance sheet date presented**.

### 4. Reinsurance
- **Reinsurance receivables, including amounts for claims incurred but not reported, are reported as assets**, consistent with how the underlying reinsured liabilities are accounted for. They are **not netted** against the ceded liabilities.
- Conditions must be satisfied for a contract to be treated as reinsurance at all; **absent them, use the deposit method** (944-20-25-4).
- For **foreign property and liability reinsurance**, **only the periodic method** is acceptable except in special circumstances (944-605-25-18). Foreign reinsurance accounted for by the **open-year method** carries specific disclosures (944-605-50-1d).
- A **reinsurer assuming an insurance benefit feature** assesses the significance of mortality and morbidity risk **regardless of whether there is an account balance** (944-40-25-35), and classifies the reinsurance contract as investment or insurance **at the inception of the reinsurance contract** (944-40-25-36). Critically, **mortality or morbidity risk may be other than nominal for the reinsurer even where the original issuer concluded it was nominal** (944-40-25-37).

### 5. Nontraditional long-duration contracts and separate accounts
**Separate accounts**: the portion of separate account assets representing **contract holder funds** is measured at **fair value** (944-80-30-1) and reported as a **summary total with an equivalent summary total for related liabilities** — but only if the arrangement meets all specified criteria (944-80-25-3, 45-3). **If it does not, the assets and liabilities are general account items** (944-80-25-4).

- Assets underlying the **insurer's own proportionate interest** are **not** contract holder funds and are **not** separately reported and valued (944-80-25-6).
- Where the arrangement meets the criteria **and** either the contract permits investing in additional units or the insurer is marketing such contracts, the insurer's proportionate interest is accounted for **consistently with similar general account assets it may be required to sell** (944-80-25-8, 25-9).
- **Under-20% expedient**: if the insurer's proportionate interest is **less than 20%** of the separate account and all underlying investments meet the definition of **securities** or of **cash and cash equivalents**, the insurer may report its portion as an **investment in equity securities classified as trading** under ASC 320 (944-80-25-10).
- **Transfers from general to separate account**: recognise at **fair value to the extent of third-party contract holders' proportionate interest**, if the criteria are met. **Gain on that proportionate interest is recognised immediately in general account earnings** — but only if the **risks and rewards of ownership have transferred**. A **guarantee of value, a minimum return guarantee, or a repurchase commitment indicates risks have not transferred, and no gain may be recognised** (944-80-40-1). If the arrangement fails the criteria, the transfer generally has **no financial reporting effect**, though loss recognition may sometimes be appropriate.

**Accrued account balance** — the basis for the balance accruing to the holder (944-40-25-14):
```
  deposits net of withdrawals
+ amounts credited pursuant to the contract
− fees and charges assessed
+ additional interest (e.g. persistency bonus)
± other adjustments (e.g. appreciation/depreciation) not already credited
```
Refinements:
- Where features may produce **more than one potential account balance**, use the **highest contractually determinable balance** available in cash at contractual maturity or the reset date, **without reduction for future fees and charges** (944-40-25-22).
- **Do not reflect surrender adjustments** — fair value annuity adjustments, surrender charges, or credits.
- Where interest credited is **reset periodically**, base the balance on the **highest crediting rate guaranteed or declared through the reset date** (944-40-25-24).
- For a contract outside ASC 815 returning the **total return of a contractually referenced pool**, base the accrued balance on the **fair value of that pool (or index) at the balance sheet date — even if the related assets are not themselves carried at fair value** (944-40-25-19).

**Insurance versus investment classification**: for a contract with death or other insurance benefit features, first determine whether it is an **investment or universal-life-type** contract (944-20-15-26). A **rebuttable presumption of significant mortality risk** arises where the additional insurance benefit **would vary significantly in response to capital markets volatility**. Significance is assessed **at contract inception** (other than at transition), comparing the **present value of expected excess payments** — insurance benefit amounts and related incremental claim adjustment expenses **in excess of the account balance** — to the **present value of all amounts expected to be assessed against the contract holder**.

**Additional liabilities** beyond the account balance:
- Where assessments for an insurance benefit feature are structured to produce **profits in early years and losses later**, establish a liability for the portion of assessments compensating the insurer for **future benefits** (944-40-25-26, 25-27). The same applies to a **reinsurer or an issuer wrapping a noninsurance contract** — for example a guaranteed minimum death benefit on a mutual fund balance (944-40-25-39, 25-41).
- For benefits **payable only on annuitization** — annuity purchase guarantees, **guaranteed minimum income benefits (GMIB)**, two-tier annuities — first assess whether **ASC 815** applies. If not, establish an additional liability where the **present value of expected annuitization payments at the expected annuitization date exceeds the expected account balance at that date** (944-40-25-40).

**Sales inducements**: recognised as part of the liability for policy benefits **over the period the contract must remain in force to qualify**, or at the **crediting date if earlier**. **No adjustment may reduce that liability for anticipated surrender charges, persistency, or early withdrawal features** (944-40-25-12). Inducements explicitly identified in the contract at inception that meet the criteria are **deferred and amortised using the same methodology and assumptions as capitalised acquisition costs**.

**Unearned revenue liability**: required for amounts assessed to compensate the insurer for services to be performed in future periods (944-605-25-6). It **may not be used to inappropriately level or smooth gross profit** over the contract term, or to produce a level gross profit from the mortality benefit over the contract's life.

### 6. Present value of future profits, surplus notes, guaranty funds
**PVP** (944-20-S99): industry practice amortises the present value of future profits using an **interest method with accrual of interest added to the unamortised balance**. The Codification mandates the rate used be the **liability or contract rate**, requires **changes in estimates of future gross profits to be a catch-up adjustment**, and subjects PVP and any related liability to the **premium deficiency test** in ASC 944-60.

**Surplus notes** (944-470): accounted for as **debt** and included in liabilities (25-1). **Interest is accrued over the term whether or not payment of interest or principal has been approved** by the insurance commissioner (35-1) — but **disclose the commissioner's ability to approve those payments** (50-1).

**Guaranty funds** (ASC 405-30): state-mandated funds settling claims against insolvent insurers, funded by assessing licensed insurers on their volume of defined lines of business. To warrant accrual, **another insurer's insolvency must generally have occurred**, since a formal determination of insolvency is what makes assessment **probable** (405-30-30-1). Exception for **prospective premium-based** assessments: if the entity **cannot avoid** the obligation by ceasing to write policies, the obligating event is the **determination of insolvency**; if it **can** avoid it, the obligating event is the **writing of premiums after the insolvency** (405-30-30-13).

### 7. Demutualizations
A mutual insurer issuing stock, and the formation of a **mutual insurance holding company (MIHC)**. The central issue is the **closed block** — a ring-fenced pool protecting participating policyholders' adjustable policy features and dividend expectations from stockholders' competing interests.

Closed block mechanics: cash flows from closed block assets **benefit closed block policyholders only** and do not inure to stockholders; the insurer **remains obligated for minimum guarantees**, so stockholder funds may sometimes be needed; closed block assets are **subject to the same liabilities with the same insolvency priority** as other assets; commissions and management expenses often are **not charged** to the block; and the block **continues until no policy in it remains in force**, absent earlier state consent.

Conclusions:
- Demutualization and MIHC formation expenses are classified as **other than highly unusual expense**.
- **Closed block assets and liabilities are included with the corresponding financial statement line items** of the insurer (944-805-25-7) — not presented separately.
- **ASC 944 continues to apply after conversion** to a stock company.
- The **maximum future contribution of the closed block to earnings is typically the excess of GAAP liabilities over GAAP assets at the demutualization date**. Establish a **dividend liability** for current earnings that will be paid to policyholders through future benefits, and for **excess earnings that can never inure to shareholders**.
- **Distribution-form** demutualization: **reclassify all retained earnings** at the demutualization date to capital stock and additional paid-in capital. **Subscription-form**: **no reclassification** results in and of itself. MIHC equity accounts at formation follow **common control** principles, with the demutualized insurer's retained earnings **before reclassification** reported as MIHC retained earnings.

**Closed block alternatives** are used where the insurer and regulators agree other mechanisms fit — commitments to continue established dividend practices, or protection of nonguaranteed elements such as interest credits on deferred annuities and adjustable premiums on term business. Where profits inuring to stockholders are limited, a **formal agreement with the regulator** defines the covered contracts, the profit limitation calculation, and the timing and manner of distribution to policyholders (policy dividends, reduced premiums, or additional benefits).

---

## What ASU 2018-12 changes

| Area | Change |
|---|---|
| **Assumptions for liability for future policy benefits** (traditional and limited-payment) | **Review and update cash flow assumptions at least annually**; **update the discount rate at each reporting date** |
| **Provision for adverse deviation** and **premium deficiency / loss recognition testing** | **Eliminated** |
| **Effect of updating cash flow assumptions** | Recognised in **net income** |
| **Effect of updating the discount rate** | Recognised in **other comprehensive income** |
| **Discount rate** | An **upper-medium grade (low-credit-risk) fixed-income instrument yield**, maximising observable market inputs |
| **Market risk benefits** on deposit / account balance contracts | Measured at **fair value**; the portion of the change attributable to **instrument-specific credit risk** goes to **OCI** |
| **DAC amortisation** | Simplified: amortise **on a constant level basis over the expected term**; **written off for unexpected contract terminations** but **not subject to an impairment test** |
| **Disclosures** | **Disaggregated rollforwards** of the liability for future policy benefits, policyholder account balances, market risk benefits, separate account liabilities, and DAC; plus significant inputs, judgments, assumptions and methods, changes in them, and their measurement effect |

---

## Decision rules

| If | Then | Authority |
|---|---|---|
| Contract is short-duration | Premium over the term **in proportion to insurance provided** | 944-605-25-1 |
| Contract is long-duration | Premium **as it becomes due** | 944-605-25-3 |
| Benefits run longer than the premium payment term | Recognise over the **longer benefit period** | 944-605-25-3 |
| Contract is nominally insurance but effectively investment | **Not** accounted for as insurance | 944-10 |
| Acquisition cost relates to an **unsuccessful** solicitation | **Expense** | 944-30-25-1A |
| Cost is market research, training, administration, product development | **Period cost** | 944-30-25-1A |
| Internal replacement meets **all six** continuation criteria | Carry over DAC, unearned revenue, deferred inducements; expense replacement costs | 944-30-35-24, 35-37 |
| **Any** continuation criterion fails | Contract **extinguished**; balances **not** deferred into the replacement | 944-30-40-1/2 |
| Modification is a contract-holder election within the original contract, no underwriting, no repricing | Guidance **does not apply** | 944-30-35-26 |
| Feature is nonintegrated | Account as a **separately issued contract** | 944-30-35-31/33 |
| Financial guarantee written | Unearned premium = **PV of premiums at the inception risk-free rate**; accrete through earnings | 944-310-30-2 |
| Prepayment assumptions change | Update discount rate; unearned premium and receivable adjust equally — **no earnings effect** | 944-310-35-5 |
| PV of expected net cash outflows exceeds declining unearned premium | Recognise a **claim liability in addition** | 944-40-25-42 |
| Reinsurance conditions not satisfied | **Deposit method** | 944-20-25-4 |
| Foreign property and liability reinsurance | **Periodic method** only, absent special circumstances | 944-605-25-18 |
| Separate account arrangement fails the criteria | Treat as **general account** assets and liabilities | 944-80-25-4 |
| Insurer's proportionate interest < 20% and all underlying are securities or cash equivalents | May report as **trading equity securities** under ASC 320 | 944-80-25-10 |
| Transfer to separate account with a value guarantee or repurchase commitment | Risks **not** transferred — **no gain** | 944-80-40-1 |
| Contract has multiple potential account balances | Use the **highest contractually determinable** balance, before future fees | 944-40-25-22 |
| Crediting rate resets periodically | Use the **highest rate guaranteed or declared through the reset date** | 944-40-25-24 |
| Assessments produce early profits and later losses | Establish an **additional liability** | 944-40-25-26/27 |
| GMIB or annuity purchase guarantee outside ASC 815 | Additional liability where PV of annuitization payments exceeds expected account balance | 944-40-25-40 |
| Sales inducement liability | **No reduction** for anticipated surrenders, persistency, or early withdrawal | 944-40-25-12 |
| Another insurer becomes insolvent | Guaranty fund assessment generally becomes **probable** → accrue | 405-30-30-1 |
| Surplus notes issued | **Debt**; accrue interest **regardless of regulatory approval**; disclose approval requirement | 944-470-25-1, 35-1, 50-1 |
| Distribution-form demutualization | **Reclassify all retained earnings** to capital stock and APIC | 944-805 |
| Subscription-form demutualization | **No** retained earnings reclassification | 944-805 |

---

## Anti-patterns

- **Deferring acquisition costs of unsuccessful solicitations.** Only successfully acquired or renewed contracts qualify.
- **Capitalising administrative expense.** All administrative expense is a period cost.
- **Carrying DAC into a substantially changed replacement contract.** Failing any one of the six criteria extinguishes the old contract.
- **Netting reinsurance recoverables against ceded liabilities.** Reinsurance receivables, including IBNR, are reported as assets.
- **Assuming a reinsurer inherits the ceding company's risk conclusion.** Mortality or morbidity risk can be other than nominal for the reinsurer even where the issuer concluded otherwise.
- **Recognising a gain on transfer to a separate account** where a value guarantee, minimum return, or repurchase commitment shows risks did not transfer.
- **Reducing the accrued account balance for surrender charges** or future fees.
- **Using the unearned revenue liability to smooth gross profit.** Expressly prohibited.
- **Recognising a financial guarantee claim liability only when the unearned premium is exhausted.** It is recognised as soon as expected net cash outflows exceed the declining unearned premium.
- **Deferring surplus note interest** because the commissioner has not approved payment. Accrue anyway; disclose the approval requirement.
- **Accruing guaranty fund assessments before an insolvency determination**, except under the prospective premium-based fact pattern where the obligation is unavoidable.
- **Presenting closed block assets and liabilities separately.** They are included with the corresponding line items.
- **Confusing SAP with GAAP** — most visibly on acquisition costs, nonadmitted assets, and claims conservatism.

---

## ASC references cited

- **ASC 944-20** — 15-26 (investment vs universal-life-type), 25-4 (reinsurance conditions; deposit method), S99 (present value of future profits)
- **ASC 944-30** — 25-1A (capitalisable acquisition costs), 35-3A (constant-level amortisation), 35-24 (continuation), 35-26 (contract-holder elections), 35-31 to 35-33 (nonintegrated features), 35-37 (six continuation criteria), 40-1, 40-2 (extinguishment)
- **ASC 944-40** — 25-12 (sales inducements), 25-14, 25-19, 25-22, 25-24 (accrued account balance), 25-26, 25-27 (additional liability), 25-35 to 25-37, 25-39, 25-41 (reinsurers and wrappers), 25-40 (annuitization benefits), 25-42 (financial guarantee claim liability)
- **ASC 944-60** — premium deficiency test
- **ASC 944-80** — 25-3, 25-4, 25-6, 25-8, 25-9, 25-10, 30-1, 40-1, 45-3 (separate accounts)
- **ASC 944-310** — 30-2, 35-5, 35-6 (financial guarantee premium and credit loss)
- **ASC 944-470** — 25-1, 35-1, 50-1 (surplus notes)
- **ASC 944-605** — 25-1, 25-3 (premium recognition), 25-6 (unearned revenue liability), 25-18, 50-1d (foreign reinsurance)
- **ASC 944-805** — 25-7 (demutualization and closed blocks)
- **Cross-topic** — ASC 405-30 (guaranty fund assessments), ASC 326 (credit losses), ASC 320 (debt and equity securities), ASC 815 (derivatives), ASU 2018-12

## Related skills

- `asc942-depository-and-lending`, `asc946-investment-companies`, `asc948-mortgage-banking` — sibling financial services regimes
- `asc950-title-plant` — title insurers apply both this topic and ASC 950
- Core topics: `ch22` ASC 326 (credit losses), `ch51` ASC 815 (derivatives), `ch32` ASC 450 (contingencies), `ch52` ASC 820 (fair value)

## Source

- Segment: `industries/asc944-financial-services-insurance.txt` (4,878 words)
