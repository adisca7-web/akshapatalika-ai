# ASC 948 — Financial Services: Mortgage Banking

> Industry skill distilled from *Wiley GAAP 2020*, ch. 64 (Specialized Industry GAAP).
> Rules and structure synthesised locally; no source text reproduced.

**Covers two activities**: (1) origination or purchase of mortgage loans and their subsequent sale to permanent investors, and (2) **long-term servicing** of those loans.

Where a subsidiary or division of a commercial bank or savings institution conducts mortgage banking, **the same standards apply**. That entity's ordinary non-mortgage lending, however, follows its normal accounting policies.

---

## Core model

A mortgage banking entity (MBE) is an **intermediary, not a lender-holder**. It originates or buys loans intending to sell them, pools them into mortgage-backed securities (securitisation), sells them to permanent investors, and typically **retains the servicing rights** in exchange for a fee.

Everything follows from **intent**, expressed as a classification:

| Classification | Measurement | Origination fees and costs |
|---|---|---|
| **Held for sale** | **Lower of amortised cost or fair value** at the balance sheet date, via a valuation allowance; changes in the allowance go to income in the period of change | Capitalised into the loan, amortised by the **effective yield method** |
| **Held for long-term investment** | Amortised cost | Deferred and recognised as a **yield adjustment** |

(ASC 948-310-35-1, 35-2; 948-310-25-3)

**Fees and costs on commitments** to originate, sell, or purchase loans are *not* loan costs — they are part of the commitment, which is a **derivative under ASC 815**.

---

## Subskills

### 1. Determine the cost basis
Three adjustments to get the "amortised cost" side of the lower-of test right:
- If the loan is a **hedged item in a fair value hedge** under ASC 815, the basis reflects carrying-amount adjustments for changes in fair value attributable to the hedged risk (948-310-35-1).
- **Purchase discounts reduce the cost basis and are not amortised into interest revenue** while the loan is held for sale (948-310-35-2). They only become a yield adjustment on transfer to investment.
- **Capitalised costs of acquiring mortgage servicing rights** on purchase or origination are **excluded** from the loans' cost basis (948-310-35-6). Servicing is a separate asset.

### 2. Determine fair value
Fair value is determined **by type of loan** — at minimum, separately for **residential and commercial**. Within a type, either an **aggregate or an individual-loan basis** may be used.

Then split by commitment status (948-310-35-3):
- **Committed loans** (subject to investor purchase commitments): **market value is fair value**.
- **Uncommitted loans** (held speculatively): quotations from the principal market in which the MBE normally operates, or absent that, the most advantageous market — considering market prices and yields sought by the MBE's **normal market outlets**, quoted **GNMA** security prices or other public quotations for long-term mortgage loans, and **FHLMC and FNMA current delivery prices**.

### 3. Transfer between classifications
Transfer from held-for-sale to held-for-long-term-investment **only if the MBE has both the intent and the ability** to hold for the foreseeable future or until maturity.

Record the transfer at the **lower of cost or market value on the transfer date**. Any difference between the loan's adjusted carrying amount and its outstanding principal balance — such as those unamortised purchase discounts — is then recognised as a **yield adjustment using the interest method** (948-310-35-4).

### 4. Account for securitisation and retained securities
Securitisation of held-for-sale loans is accounted for as a **sale of the loans and a purchase of mortgage-backed securities**.

Retained MBS are classified under **ASC 320**:
- **Held-to-maturity** requires both intent and ability to hold for the foreseeable future or to maturity.
- If the MBE **had committed to sell** the securities before or during securitisation, they **must be classified as trading** (948-310-35-3A).
- MBS held by a **not-for-profit** entity are stated at fair value under ASC 958-320.

Fair value of **uncommitted MBS collateralised by the MBE's own loans** is ordinarily the market value of the securities — but if the trust may be **readily terminated and the loans sold directly**, fair value is based on the market value of either the loans or the securities, **depending on the entity's intentions**. Other uncommitted MBS use published yield data.

### 5. Handle servicing fees and the sale adjustment
Servicing fees are normally a percentage of the outstanding principal balance, compensating the MBE for processing principal, interest, and escrow payments, disbursing escrow for taxes and insurance, and remitting net proceeds with accounting reports.

When a loan is **sold with servicing retained**, the **sales price must be adjusted** if the stated servicing rate is **materially different from the current (normal) servicing fee rate**, so that gain or loss on sale can be determined (948-10-05-7). The adjustment and any resulting gain or loss are determined **as of the sale date**, and the adjustment allows normal servicing fees to be recognised in later years.

**If estimated normal servicing fees are less than total expected servicing costs, accrue that loss on the sale date.** A servicing contract that loses money is recognised immediately, not bled through future periods.

### 6. Sales to affiliated entities
Two different regimes (948-310-30-1, 30-2):

**Sale to an affiliate**: adjust the carrying amount to **lower of amortised cost or fair value as of the date management decides the sale will occur** — evidenced by formal approval by a representative of the purchasing affiliate, issuance of a purchase commitment, and the seller's acceptance. Charge any adjustment **to income**.

**Loans originated specifically for an affiliate**: the originator is an **agent** of the affiliate, and loans transfer at the **originator's cost of acquisition** with no gain or loss. This does **not** apply to right-of-first-refusal or similar contracts where the originator **retains all the risks of ownership**.

### 7. GNMA internal reserve method
An issuer electing the internal reserve method must deposit one month's interest on the collateralising loans with a trustee. That cost is **capitalised — at no greater than the present value of net future servicing income — and amortised** (948-340-25-1).

### 8. Loan and commitment fees
- **Third-party services** in a loan origination (e.g. appraisal fees): recognised **when the services are performed** (948-720-25-1).
- **Commitment fees paid to permanent investors on loans held for sale**: recognised as expense **when the loans are sold, or when it is determined the commitment will not be used** (948-605-25-1). Residential commitment fees typically cover groups of loans and are allocated to individual transactions.

---

## Decision rules

| If | Then | Authority |
|---|---|---|
| Loan is held for sale | Lower of amortised cost or fair value, via valuation allowance | 948-310-35-1/2 |
| Loan is held for long-term investment | Amortised cost; fees as yield adjustment | 948-310-25-3 |
| Fee relates to a commitment to originate/sell/purchase | Part of the commitment — **ASC 815 derivative** | 948-310-25-3 |
| Loan has a purchase discount while held for sale | Reduce cost basis; **do not** amortise into interest revenue | 948-310-35-2 |
| Servicing rights capitalised on origination/purchase | Exclude from the loans' cost basis | 948-310-35-6 |
| Loan is committed to an investor | Market value **is** fair value | 948-310-35-3 |
| Loan is uncommitted | Use principal-market quotations, GNMA/FHLMC/FNMA reference prices | 948-310-35-3 |
| Reclassifying HFS → investment | Requires intent **and** ability; record at lower of cost or market at transfer | 948-310-35-4 |
| Committed to sell securities before/during securitisation | Classify retained MBS as **trading** | 948-310-35-3A |
| Selling loans with servicing retained at an off-market rate | Adjust the sales price to the normal servicing fee rate | 948-10-05-7 |
| Expected servicing costs exceed normal servicing fees | **Accrue the loss on the sale date** | 948-10-05-7 |
| Selling to an affiliate | Remeasure to lower of cost or fair value at the decision date; charge to income | 948-310-30-1 |
| Originating specifically for an affiliate | Agent relationship; transfer at cost, no gain | 948-310-30-2 |
| Originator retains all ownership risks | Agent treatment does **not** apply | 948-310-30-2 |
| Electing GNMA internal reserve method | Capitalise ≤ PV of net future servicing income; amortise | 948-340-25-1 |

---

## Anti-patterns

- **Amortising purchase discounts into interest revenue on held-for-sale loans.** They reduce the cost basis instead, and only become a yield adjustment after transfer to investment.
- **Leaving servicing rights inside the loan cost basis.** They are excluded, and their capitalised cost is a separate asset.
- **Treating commitment fees as loan origination fees.** Commitments are ASC 815 derivatives.
- **Classifying retained MBS as held-to-maturity** when a sale commitment existed before or during securitisation — they must be trading.
- **Applying one fair value approach to the whole book.** Residential and commercial are determined separately, as are committed and uncommitted loans.
- **Reclassifying to long-term investment to avoid a lower-of-cost-or-fair-value write-down.** Requires genuine intent *and* ability, and the transfer is recorded at the lower amount anyway.
- **Deferring a known servicing loss.** Accrue it at the sale date.
- **Recognising a gain on loans originated as agent for an affiliate.** They transfer at cost.

---

## Key terms

- **Mortgage banking entity** — engaged primarily in originating, marketing, and servicing real estate mortgage loans **for other than its own account**, acting as correspondent between lenders and borrowers.
- **Permanent investor** — invests in mortgage loans for its own account: insurers, banks, savings and loans, pension plans, REITs, FNMA.
- **Current (normal) servicing fee rate** — the rate most commonly used in comparable servicing agreements for similar loans; the benchmark for the sale-price adjustment.
- **GNMA (Ginnie Mae)** — U.S. government agency guaranteeing certain mortgage-backed securities; GNMA pass-through payments are **backed by the U.S. government**.
- **FHLMC (Freddie Mac) / FNMA (Fannie Mae)** — congressionally created secondary-market corporations; their pass-through payments are **guaranteed by those corporations, not backed by the U.S. government**.
- **Mortgage-backed securities / participation certificates** — an undivided interest in a pool of specific mortgage loans.
- **Internal reserve method** — a GNMA issuer payment method requiring a custodial deposit of one month's interest on the collateralising loans.
- **Gap commitment** — interim financing bridging the floor loan and the maximum permanent loan while the borrower satisfies conditions such as an occupancy level.
- **Affiliated entity** — controls, is controlled by, or is under common control with another entity; or a party over whose operating and financial policies one can exercise significant influence.

---

## ASC references cited

- **ASC 948-10** — 05-7 (servicing retained; sale price adjustment)
- **ASC 948-310** — 25-3 (origination fees by classification), 30-1, 30-2 (sales to and originations for affiliates), 35-1, 35-2 (lower of amortised cost or fair value; hedged basis; purchase discounts), 35-3 (fair value determination), 35-3A (retained MBS classification), 35-4 (transfers), 35-6 (servicing rights excluded from basis)
- **ASC 948-340** — 25-1 (GNMA internal reserve method)
- **ASC 948-605** — 25-1 (commitment fees paid to investors)
- **ASC 948-720** — 25-1 (third-party service fees)
- **Cross-topic** — ASC 320 (debt securities), ASC 815 (derivatives and hedging), ASC 860 (transfers and servicing), ASC 326 (credit losses), ASC 958-320 (NFP investments)

## Related skills

- `asc942-depository-and-lending` — the balance-sheet lender counterpart
- `asc950-title-plant` — adjacent participant in the real estate transaction chain
- Core topics: `ch63` ASC 860 (transfers and servicing), `ch51` ASC 815 (derivatives), `ch18` ASC 320 (debt securities), `ch22` ASC 326 (credit losses)

## Source

- Segment: `industries/asc948-financial-services-mortgage-banking.txt` (2,010 words)
