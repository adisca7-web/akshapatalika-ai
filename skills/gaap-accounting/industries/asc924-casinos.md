# ASC 924 — Entertainment: Casinos

> Industry skill distilled from *Wiley GAAP 2020*, ch. 64 (Specialized Industry GAAP).
> Rules and structure synthesised locally; no source text reproduced.

**Applies to** gaming entities — casinos, riverboat and Native American gaming, and legalised betting operations including horse racing, dog racing, lotteries, and jai alai. (ASC 924-10-05-3)

**Also consult**: the GASB codification for gaming entities classified as governmental, and the AICPA audit and accounting guide *Gaming*. ASC 924 is thin; most casino accounting runs through general GAAP.

---

## Core model

Only three things are genuinely casino-specific, and each is a recognition question rather than a measurement one.

### 1. Outstanding chips are a liability
Patrons exchange cash for chips, so chips in patrons' hands are an unsettled obligation of the house.

```
chip liability = total chips placed in service − chips in the casino's custody
```

(ASC 924-405-25-2). The measurement is by difference, which means chip inventory control *is* the liability control. A weak chip count produces a misstated liability directly.

### 2. Base jackpots may not be a liability yet
A base jackpot is the fixed minimum payout for a specific slot combination. Where the entity **can avoid the payout** — for example by removing the machine from service before the combination hits — no liability is recorded **until the entity is subject to pay** (ASC 924-405-55-1).

The test is avoidability, not probability. A jackpot that is likely to be hit but legally avoidable is still not a liability.

### 3. Fixed-odds wagers are revenue, not derivatives
A wagering contract whose odds are known or knowable when the bet is placed is a **fixed-odds contract**. Its issuer accounts for it under **ASC 606**, not ASC 815 (ASC 924-815-25-1).

This is a deliberate scope carve-out. A fixed-odds bet has every surface feature of a derivative — an underlying, a notional, net settlement — and would otherwise sweep into ASC 815, forcing fair-value remeasurement of the entire wagering book each period. ASC 924 routes it to revenue instead.

---

## Decision rules

| If | Then | Authority |
|---|---|---|
| Chips are in patrons' hands | Recognise a liability for chips in service less chips in custody | 924-405-25-2 |
| Base jackpot payout can be avoided | No liability until the entity is subject to pay | 924-405-55-1 |
| Base jackpot payout cannot be avoided | Accrue the liability | 924-405-55-1 |
| Wager has known or knowable odds when placed | Account under ASC 606 | 924-815-25-1 |
| Gaming entity is governmental | Follow the GASB codification, not ASC 924 | 924-10-05-3 |

---

## Anti-patterns

- **Treating chip sales as revenue on issue.** Cash received for chips is a liability until the chips are played or retired.
- **Accruing base jackpots on a probability basis.** The trigger is whether the payout is avoidable, not whether it is likely.
- **Classifying fixed-odds wagering books as derivatives.** ASC 924-815-25-1 sends them to ASC 606, avoiding fair-value remeasurement of the wagering book.
- **Ignoring the AICPA *Gaming* guide.** ASC 924 covers very little; most practice questions are answered there.

---

## Key terms

- **Base jackpot** — the fixed minimum payout from a slot machine for a specific combination.
- **Chips** — money substitutes issued by the gaming entity and used by patrons for wagering.
- **Slot machine** — a mechanical or electrical apparatus used in connection with gaming.

---

## ASC references cited

- **ASC 924-10** — 05-3 (scope and industry background), 20 (definitions)
- **ASC 924-405** — 25-2 (chip liability measurement), 55-1 (base jackpot avoidability)
- **ASC 924-815** — 25-1 (fixed-odds contracts follow ASC 606, not ASC 815)

## Related skills

- Core topics: ASC 606 (revenue, including fixed-odds wagers and loyalty programmes), ASC 815 (derivatives — scope exclusion), ASC 405 (liabilities)
- `asc970-real-estate-general` — resort operators typically hold significant real estate

## Source

- Segment: `industries/asc924-entertainment-casinos.txt` (282 words)
