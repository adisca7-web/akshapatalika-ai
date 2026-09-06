# ASC 985 — Software

> Industry skill distilled from *Wiley GAAP 2020*, ch. 64 (Specialized Industry GAAP).
> Rules and structure synthesised locally; no source text reproduced.

---

## Scope: pick the right regime first

Four distinct undertakings, and they do **not** share one standard. Getting this routing wrong is the most consequential software error, because the capitalisation triggers differ completely.

| Situation | Governing guidance |
|---|---|
| Software developed internally **for sale, lease, or marketing** to others | **ASC 985-20** — this skill |
| Software licensed, purchased, or leased from others **for internal use** | **ASC 350-40** |
| Software developed internally **for the developer's own use** | **ASC 350-40** |
| Software obtained from others **for resale** (standalone or in a larger product) | Inventory / ASC 330 |

Software may reside on the user's hardware or be **hosted by an application service provider** and leased for remote use. To decide whether a project is internal-use or subject to a plan to be marketed externally, see **ASC 350-40-15-2 through 15-2C and 350-40-15-5**.

---

## Core model: technological feasibility

The entire question for software built to sell is: **when do development costs stop being R&D?**

Until **technological feasibility** is established, **all development costs are R&D and must be expensed** (ASC 985-20-25-1, and ASC 730). After it, qualifying costs of producing product masters are **capitalised**. So technological feasibility is a switch that moves spending from the income statement to the balance sheet, and it is defined tightly to stop entities flipping it early.

```
   expense as R&D          capitalise            expense as period cost
 ├──────────────────┼──────────────────────┼────────────────────────────►
                    ▲                      ▲
        technological feasibility   available for general
             established              release to customers
```

Two ends, both hard boundaries. Capitalisation **starts** at technological feasibility and **ceases** once the product is available for general release (ASC 985-20-25-6).

### Establishing technological feasibility
Reached when all necessary planning, designing, coding, and testing activities have been completed to the extent needed to establish that the product **can meet its design specifications** — functions, features, and technical performance requirements (ASC 985-20-25-2).

**If the process involves a detail program design** (ASC 985-20-25-2a), all three:
1. Product design (the logical representation) **and** detailed program design completed — including demonstrating that the necessary **skills, hardware, and software technologies are accessible** to complete development.
2. Detailed program design **documented and traced to product specifications**, showing completeness and consistency.
3. Detailed program design **reviewed for high-risk elements** — unproven functions or product innovations — and any such elements **resolved through coding and testing**.

**If there is no detail program design** (ASC 985-20-25-2b), both:
1. Product design **and a working model** completed.
2. Completeness of the working model and its consistency with the product design **confirmed by testing**.

A **working model** is an operative version in the same language as the product to be marketed, performing all major planned functions, ready for initial customer (beta) testing.

---

## Subskills

### 1. Capitalise production costs
After technological feasibility, capitalise qualifying costs of producing **product masters** (ASC 985-20-25-3), which include:
- The master copy of the software itself
- **Related user documentation and training materials**
- Additional coding and testing performed after technological feasibility

Capitalised production costs **may include allocated indirect costs** — for example occupancy costs relating to programmers (ASC 985-20-25-5).

**Period costs**: maintenance and ongoing customer support are expensed as incurred (ASC 985-20-25-6). *Maintenance* means post-release activities to correct errors or keep the product current, including routine changes and additions. *Customer support* means installation assistance, training classes, telephone Q&A, newsletters, on-site visits, and software or data modifications.

### 2. Amortise — greater of two methods
Amortisation begins when the product is **first available for general release** (ASC 985-20-35-3), on a **product-by-product basis**. Costs of earlier products may **not be rolled forward** into newer products to defer expense.

Periodic amortisation is the **greater** of (ASC 985-20-35-1):
1. **Revenue-based** — capitalised cost × (current period revenue ÷ total estimated revenue for the product); or
2. **Straight-line** over the product's expected life cycle.

**Worked example.** $30,000 capitalised when sales begin; estimated total revenue $5,100,000 over four years; current half-year revenue $600,000.

- Revenue method: $30,000 × ($600,000 ÷ $5,100,000) = **$3,529**
- Straight-line: $30,000 ÷ 4 × ½ = **$3,750**
- **Amortisation = $3,750**, the greater.

The "greater of" rule is a floor that guarantees the asset is written off at least rateably over its life, even if the revenue forecast is optimistic. A pure revenue method would let a slow-selling product carry cost forward indefinitely.

### 3. Inventory the duplication costs
Product duplication, training material publication, and packaging are **capitalised as inventory on a unit-specific basis** and expensed as **cost of sales when the related product revenue is recognised** — not amortised with the master.

### 4. Test net realisable value annually
Capitalised software costs are evaluated annually for **net realisable value**. Where an impairment adjustment is recognised, the **written-down amount becomes the new cost basis** both for further amortisation and for the following period's NRV comparison (ASC 985-20-35-4). No restoration.

### 5. Revenue: losses and non-delivery
- **Provision for losses** — if it is probable that the transaction price allocated to an **unsatisfied performance obligation** under ASC 606 will result in a loss, recognise the loss under **ASC 450**.
- **Delivery may not equal the product.** Where services involve significant **production, modification, or customisation** of the software, physical delivery does not constitute delivery of the contracted product. Such arrangements are accounted for as **construction-type or production-type contracts** under ASC 606-35 (ASC 985-605-25-2).

---

## Decision rules

| If | Then | Authority |
|---|---|---|
| Software is for internal use | Apply **ASC 350-40**, not 985-20 | 350-40-15-2 |
| Software is to be sold, leased, or marketed | Apply ASC 985-20 | 985-20 |
| Technological feasibility not yet established | **Expense all development cost as R&D** | 985-20-25-1 |
| Detail program design used | Require design completion + documentation/tracing + high-risk resolution | 985-20-25-2a |
| No detail program design | Require product design + working model, confirmed by testing | 985-20-25-2b |
| Technological feasibility established | Capitalise product master production costs, incl. documentation and training materials | 985-20-25-3 |
| Indirect costs relate to programmers | May be allocated into capitalised cost | 985-20-25-5 |
| Product available for general release | **Stop capitalising**; start amortising | 985-20-25-6, 35-3 |
| Cost is maintenance or customer support | Expense as incurred | 985-20-25-6 |
| Computing periodic amortisation | **Greater of** revenue ratio and straight-line | 985-20-35-1 |
| Tempted to pool old product costs into a new release | Not permitted — product-by-product | 985-20-35-1 |
| Cost is duplication, packaging, or training material publication | Inventory, unit-specific; COGS when revenue recognised | 985-20 |
| Carrying amount exceeds NRV | Write down; new cost basis, no restoration | 985-20-35-4 |
| Loss probable on an unsatisfied performance obligation | Recognise under ASC 450 | 985-605 |
| Contract requires significant customisation | Account as a production-type contract under ASC 606-35 | 985-605-25-2 |

---

## Anti-patterns

- **Declaring technological feasibility at project kickoff** to start capitalising. The criteria are specific, evidenced, and include resolving high-risk elements.
- **Capitalising internal-use software under ASC 985-20.** That is ASC 350-40 territory with different triggers.
- **Continuing to capitalise after general release.** Capitalisation stops at availability for general release.
- **Capitalising maintenance and customer support.** Both are period costs.
- **Using only the revenue-based amortisation method.** The straight-line floor applies; take the greater.
- **Rolling forward legacy product costs** into a new release to defer expense. Prohibited by the product-by-product rule.
- **Amortising duplication and packaging costs.** They are inventory, relieved as COGS with the related revenue.
- **Restoring a prior NRV write-down.** The reduced amount is the new cost basis.
- **Recognising revenue on physical delivery** where significant customisation remains.

---

## Key terms

- **Technological feasibility** — the point at which planning, designing, coding, and testing establish that the product can meet its design specifications.
- **Detail program design** — the design taking product functions, features, and technical requirements to their most detailed logical form, enabling coding.
- **Product design** — a logical representation of all product functions in sufficient detail to serve as product specifications.
- **Working model** — an operative version in the final language, performing all major planned functions, ready for beta testing.
- **Coding** — generating detailed instructions in a computer language to carry out the detail program design; may begin before, during, or after that design is complete.
- **Testing** — determining whether the coded product meets the function, feature, and technical performance requirements in the product design.
- **Product enhancement** — improvements intended to extend life or significantly improve marketability; normally requires its own product design and may require redesign of the existing product.
- **Maintenance** — post-release correction of errors and updating, including routine changes and additions.
- **Customer support** — installation assistance, training, telephone Q&A, newsletters, on-site visits, software or data modifications.

---

## ASC references cited

- **ASC 985-20** — 25-1 (R&D until technological feasibility), 25-2 / 25-2a / 25-2b (establishing feasibility), 25-3 (product master costs), 25-5 (allocated indirect costs), 25-6 (cessation; period costs), 35-1 (greater-of amortisation), 35-3 (amortisation start), 35-4 (NRV and new cost basis)
- **ASC 985-605** — 25-2 (customisation → production-type contract)
- **ASC 985-70**, **ASC 985-705** — related software subtopics
- **Cross-topic** — ASC 350-40 (internal-use software, incl. 15-2 through 15-2C and 15-5), ASC 730 (R&D), ASC 606 and 606-35 (revenue; production-type contracts), ASC 450 (loss provisions), ASC 330 (inventory)

## Related skills

- `asc926-entertainment-film` — the other "capitalise then amortise against forecast revenue" content regime
- Core topics: `ch25` ASC 350 (intangibles and internal-use software), `ch46` ASC 730 (R&D), `ch38` ASC 606 (revenue), `ch32` ASC 450 (contingencies)

## Source

- Segment: `industries/asc985-software.txt` (1,468 words)
