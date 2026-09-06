"""The ASC citation catalog.

Every deterministic skill in this system declares which paragraphs of the FASB
Accounting Standards Codification it implements. A computed answer that cannot
name its authority is not a GAAP answer, it is a spreadsheet formula.

Citations are data, not prose. They are attached to results, rendered into
workpapers, and checked by tests, so a skill cannot drift away from the
paragraph it claims to implement without something failing.

Scope note: this catalog covers the topics the shipped skills implement. It is
deliberately not a full copy of the Codification -- the ASC text itself is
copyrighted by the FAF and is not reproduced here. What is stored is the
citation key, the topic title, and a short neutral description of the
requirement, which is the same thing a workpaper reference column holds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = ["Citation", "ASC", "cite", "topic_of", "all_citations"]


@dataclass(frozen=True)
class Citation:
    """A reference to an ASC paragraph and what it requires."""

    key: str  # e.g. "606-10-32-31"
    topic: str  # e.g. "Revenue from Contracts with Customers"
    requirement: str  # neutral one-line statement of the rule
    subtopic: Optional[str] = None
    # False marks a reference carried for traceability that has NOT been checked
    # against the published Codification. The distinction is load-bearing: a
    # citation that merely looks well-formed is indistinguishable from a correct
    # one at a glance, which is how unverified references spread. Anything
    # unverified is rendered with a warning and must be confirmed before it is
    # relied on in a filing.
    verified: bool = True

    @property
    def topic_number(self) -> str:
        return self.key.split("-")[0]

    @property
    def is_paragraph(self) -> bool:
        """False for a topic- or subtopic-level stub such as ``932-10``.

        A stub is a legitimate workpaper reference but it is not authority for a
        specific requirement, so it is worth telling apart from a paragraph.
        """
        return len(self.key.split("-")) >= 4

    def __str__(self) -> str:
        mark = "" if self.verified else " [UNVERIFIED]"
        return f"ASC {self.key} ({self.topic}){mark}"

    def to_dict(self) -> dict:
        return {
            "asc": self.key,
            "topic": self.topic,
            "requirement": self.requirement,
            "verified": self.verified,
            "paragraph_level": self.is_paragraph,
        }


def _c(key: str, topic: str, requirement: str) -> Citation:
    return Citation(key=key, topic=topic, requirement=requirement)


def _u(key: str, topic: str, requirement: str) -> Citation:
    """An unverified reference: correct in substance, unchecked in paragraph number."""
    return Citation(key=key, topic=topic, requirement=requirement, verified=False)


_REVENUE = "Revenue from Contracts with Customers"
_LEASES = "Leases"
_INVENTORY = "Inventory"
_PPE = "Property, Plant, and Equipment"
_EPS = "Earnings Per Share"
_CASHFLOW = "Statement of Cash Flows"
_TAX = "Income Taxes"
_CREDIT = "Financial Instruments -- Credit Losses"
_PRESENT = "Presentation of Financial Statements"
_FRAMEWORK = "Generally Accepted Accounting Principles"


class ASC:
    """Named citation constants, grouped by topic."""

    # -- 105 / framework ------------------------------------------------
    GAAP_HIERARCHY = _c(
        "105-10-05-1", _FRAMEWORK,
        "The Codification is the single source of authoritative nongovernmental U.S. GAAP.",
    )

    # -- 810 consolidation ----------------------------------------------
    INTERCOMPANY_ELIMINATION = _c(
        "810-10-45-1", "Consolidation",
        "Intercompany balances and transactions are eliminated in full on consolidation.",
    )

    # -- 205 / 210 presentation -----------------------------------------
    CLASSIFIED_BALANCE_SHEET = _c(
        "210-10-05-4", _PRESENT,
        "A classified balance sheet separates current from noncurrent assets and liabilities.",
    )
    CURRENT_ASSETS = _c(
        "210-10-45-1", _PRESENT,
        "Current assets are those reasonably expected to be realized within one year or the operating cycle, whichever is longer.",
    )
    OFFSETTING = _c(
        "210-20-45-1", _PRESENT,
        "Assets and liabilities may be offset only when a right of setoff exists.",
    )

    # -- 230 cash flows -------------------------------------------------
    CF_CLASSIFICATION = _c(
        "230-10-45-1", _CASHFLOW,
        "Cash receipts and payments are classified as operating, investing, or financing.",
    )
    CF_INDIRECT = _c(
        "230-10-45-28", _CASHFLOW,
        "Under the indirect method, net income is adjusted for noncash items and working capital changes to derive operating cash flow.",
    )
    CF_RECONCILE = _c(
        "230-10-45-24", _CASHFLOW,
        "The statement reconciles beginning and ending cash and cash equivalents, including restricted cash.",
    )
    CF_NONCASH = _c(
        "230-10-50-3", _CASHFLOW,
        "Noncash investing and financing activities are disclosed outside the statement body.",
    )

    # -- 260 earnings per share -----------------------------------------
    EPS_BASIC = _c(
        "260-10-45-10", _EPS,
        "Basic EPS is income available to common shareholders divided by the weighted-average shares outstanding.",
    )
    EPS_WEIGHTED = _c(
        "260-10-55-2", _EPS,
        "Shares are weighted by the portion of the period they were outstanding.",
    )
    EPS_DILUTED = _c(
        "260-10-45-16", _EPS,
        "Diluted EPS reflects the dilutive effect of all potential common shares.",
    )
    EPS_TREASURY_STOCK = _c(
        "260-10-45-23", _EPS,
        "The treasury stock method assumes option proceeds repurchase shares at the average market price.",
    )
    EPS_ANTIDILUTIVE = _c(
        "260-10-45-17", _EPS,
        "Potential common shares are excluded when their effect would be antidilutive.",
    )
    EPS_IF_CONVERTED = _c(
        "260-10-45-40", _EPS,
        "Convertible instruments are tested under the if-converted method, adding back related after-tax charges.",
    )

    # -- 326 credit losses ----------------------------------------------
    CECL = _c(
        "326-20-30-1", _CREDIT,
        "An allowance is measured for current expected credit losses over the asset's contractual life.",
    )
    CECL_POOLING = _c(
        "326-20-30-2", _CREDIT,
        "Financial assets with similar risk characteristics are measured on a pooled basis.",
    )

    # -- 330 inventory --------------------------------------------------
    INVENTORY_COST = _c(
        "330-10-30-1", _INVENTORY,
        "Inventory is initially measured at cost, including all costs of purchase and conversion.",
    )
    INVENTORY_LCNRV = _c(
        "330-10-35-1B", _INVENTORY,
        "Inventory measured on FIFO or average cost is stated at the lower of cost and net realizable value.",
    )
    INVENTORY_LCM_LIFO = _c(
        "330-10-35-1C", _INVENTORY,
        "Inventory measured on LIFO or the retail method is stated at the lower of cost or market.",
    )
    INVENTORY_FLOW = _c(
        "330-10-30-9", _INVENTORY,
        "Cost is assigned using FIFO, LIFO, or average cost, applied consistently.",
    )
    INVENTORY_NO_REVERSAL = _c(
        "330-10-35-14", _INVENTORY,
        "A write-down to net realizable value creates a new cost basis; subsequent recovery is not restored.",
    )

    # -- 360 property, plant and equipment ------------------------------
    PPE_DEPRECIATION = _c(
        "360-10-35-4", _PPE,
        "Depreciable cost is allocated over the asset's useful life in a systematic and rational manner.",
    )
    PPE_IMPAIRMENT_TEST = _c(
        "360-10-35-17", _PPE,
        "A long-lived asset is tested for recoverability by comparing carrying amount to undiscounted future cash flows.",
    )
    PPE_IMPAIRMENT_MEASURE = _c(
        "360-10-35-17", _PPE,
        "If not recoverable, impairment equals the excess of carrying amount over fair value.",
    )

    # -- 606 revenue ----------------------------------------------------
    REV_STEP1_CONTRACT = _c(
        "606-10-25-1", _REVENUE,
        "A contract exists when it is approved, rights and payment terms are identifiable, it has commercial substance, and collection is probable.",
    )
    REV_STEP2_PO = _c(
        "606-10-25-14", _REVENUE,
        "Each promise to transfer a distinct good or service is a separate performance obligation.",
    )
    REV_DISTINCT = _c(
        "606-10-25-19", _REVENUE,
        "A good or service is distinct if the customer can benefit from it on its own and it is separately identifiable in the contract.",
    )
    REV_STEP3_PRICE = _c(
        "606-10-32-2", _REVENUE,
        "The transaction price is the consideration expected in exchange for transferring promised goods or services.",
    )
    REV_TAX_EXCLUDED = _c(
        "606-10-32-2A", _REVENUE,
        "Amounts collected on behalf of third parties, such as sales taxes, are excluded from the transaction price.",
    )
    REV_RETURN_LIABILITY = _c(
        "606-10-32-10", _REVENUE,
        "A refund liability is recognised for consideration expected to be refunded, measured on expected returns rather than returns already taken.",
    )
    REV_BREAKAGE = _c(
        "606-10-55-46", _REVENUE,
        "Breakage on unexercised customer rights is recognised in proportion to the pattern of rights exercised, or when the likelihood of exercise becomes remote.",
    )
    REV_VARIABLE = _c(
        "606-10-32-8", _REVENUE,
        "Variable consideration is estimated using expected value or most likely amount, whichever better predicts the entitlement.",
    )
    REV_CONSTRAINT = _c(
        "606-10-32-11", _REVENUE,
        "Variable consideration is included only to the extent a significant revenue reversal is not probable.",
    )
    REV_FINANCING = _c(
        "606-10-32-15", _REVENUE,
        "The transaction price is adjusted for a significant financing component when the timing of payment provides financing.",
    )
    REV_STEP4_ALLOCATE = _c(
        "606-10-32-31", _REVENUE,
        "The transaction price is allocated to performance obligations in proportion to standalone selling prices.",
    )
    REV_SSP_ESTIMATE = _c(
        "606-10-32-33", _REVENUE,
        "When a standalone selling price is not observable it is estimated, maximizing observable inputs.",
    )
    REV_DISCOUNT_ALLOC = _c(
        "606-10-32-37", _REVENUE,
        "A discount is allocated proportionately to all performance obligations unless evidence supports allocating it to specific ones.",
    )
    REV_STEP5_RECOGNIZE = _c(
        "606-10-25-23", _REVENUE,
        "Revenue is recognized when (or as) control of the promised good or service transfers to the customer.",
    )
    REV_OVER_TIME = _c(
        "606-10-25-27", _REVENUE,
        "Revenue is recognized over time when the customer simultaneously receives and consumes the benefit, the entity's work creates an asset the customer controls, or the asset has no alternative use and there is an enforceable right to payment.",
    )
    REV_PROGRESS = _c(
        "606-10-25-31", _REVENUE,
        "A single method of measuring progress is applied to each performance obligation satisfied over time.",
    )
    REV_CONTRACT_BALANCES = _c(
        "606-10-45-1", _REVENUE,
        "A contract asset or contract liability is presented depending on the relationship between performance and payment.",
    )
    REV_PRINCIPAL_AGENT = _c(
        "606-10-55-36", _REVENUE,
        "A principal controls the good or service before transfer and reports revenue gross; an agent reports the net fee.",
    )

    # -- 740 income taxes -----------------------------------------------
    TAX_DEFERRED = _c(
        "740-10-25-2", _TAX,
        "A deferred tax liability or asset is recognized for the future tax effects of temporary differences and carryforwards.",
    )
    TAX_RATE = _c(
        "740-10-30-8", _TAX,
        "Deferred taxes are measured using enacted tax rates expected to apply when the difference reverses.",
    )
    TAX_VALUATION_ALLOWANCE = _c(
        "740-10-30-5", _TAX,
        "A valuation allowance reduces deferred tax assets to the amount more likely than not to be realized.",
    )
    TAX_RATE_RECONCILIATION = _c(
        "740-10-50-12", _TAX,
        "The reconciliation of statutory to effective tax rate is disclosed.",
    )

    # -- 842 leases -----------------------------------------------------
    LEASE_IDENTIFY = _c(
        "842-10-15-3", _LEASES,
        "A contract is or contains a lease if it conveys the right to control the use of an identified asset for a period in exchange for consideration.",
    )
    LEASE_CLASSIFY = _c(
        "842-10-25-2", _LEASES,
        "A lessee classifies a lease as finance if any of the five criteria are met; otherwise it is an operating lease.",
    )
    LEASE_INITIAL = _c(
        "842-20-30-1", _LEASES,
        "At commencement the lease liability is the present value of unpaid lease payments discounted at the rate implicit in the lease, or the incremental borrowing rate if that rate is not readily determinable.",
    )
    LEASE_ROU = _c(
        "842-20-30-5", _LEASES,
        "The right-of-use asset comprises the lease liability, prepaid lease payments, and initial direct costs, less lease incentives received.",
    )
    LEASE_FINANCE_SUBSEQUENT = _c(
        "842-20-35-4", _LEASES,
        "A finance lease produces interest on the liability and separate straight-line amortization of the right-of-use asset.",
    )
    LEASE_OPERATING_SUBSEQUENT = _c(
        "842-20-35-6", _LEASES,
        "An operating lease produces a single straight-line lease cost over the lease term.",
    )
    LEASE_SHORT_TERM = _c(
        "842-20-25-2", _LEASES,
        "A short-term lease of twelve months or less with no purchase option may be exempted by policy election.",
    )

    # -- specialized industry references --------------------------------
    #
    # These back the row rules in gaapai.semantics. They are recorded here so
    # every rule resolves through cite() rather than carrying a bare string --
    # which is how 22 unchecked references shipped in the first place.
    #
    # They are marked UNVERIFIED deliberately. The substance of each rule was
    # taken from the industry reference pack, but the paragraph numbers have not
    # been confirmed against the published Codification, and a plausible-looking
    # citation is worse than an absent one. Confirm before relying on any of
    # these; promote to _c() once checked.

    FILM_AMORTIZATION = _u(
        "926-20-35-1", "Entertainment -- Films",
        "Capitalized film costs are amortized in proportion to current revenue over total estimated ultimate revenue.",
    )
    FILM_ADVERTISING = _u(
        "926-20-35-5", "Entertainment -- Films",
        "Reimbursements of advertising and exploitation costs are not exhibition revenue.",
    )
    FILM_PARTICIPATIONS = _u(
        "926-10-20", "Entertainment -- Films",
        "Participation and residual costs are film costs, not a reduction of revenue.",
    )
    INSURANCE_PREMIUM_DURATION = _u(
        "944-605-25-1", "Financial Services -- Insurance",
        "Premium revenue recognition depends on whether the contract is short-duration or long-duration.",
    )
    INSURANCE_CEDED = _u(
        "944-20", "Financial Services -- Insurance",
        "Subtopic-level reference: ceded reinsurance is presented separately and does not reduce written premium.",
    )
    CASINO_PROMOTIONAL = _u(
        "924-10-05-3", "Entertainment -- Casinos",
        "Promotional allowances and complimentaries are not gaming revenue.",
    )
    CASINO_CHIPS = _u(
        "924-405-25-2", "Entertainment -- Casinos",
        "Chips and tokens outstanding are a liability until redeemed, not revenue.",
    )
    SOFTWARE_INTERNAL_USE = _u(
        "350-40-15-2", "Intangibles -- Internal-Use Software",
        "Software developed for internal use is scoped out of the software-to-be-sold guidance.",
    )
    NFP_CONDITIONAL = _u(
        "958-605-25-5A", "Not-for-Profit Entities",
        "A conditional contribution is not recognized until the barrier is overcome and the right of return lapses.",
    )
    NFP_RESTRICTION = _u(
        "958-210-45-2", "Not-for-Profit Entities",
        "Net assets are presented by donor restriction: with restriction and without restriction.",
    )
    NFP_AGENCY = _u(
        "958-20-25-1", "Not-for-Profit Entities",
        "An agency transaction is a liability to the specified beneficiary, not contribution revenue.",
    )
    BANK_INCOME_SPLIT = _u(
        "942-10-S45-1", "Financial Services -- Depository and Lending",
        "Interest income and noninterest income are presented separately.",
    )
    BANK_NONACCRUAL = _u(
        "942-310-35-2", "Financial Services -- Depository and Lending",
        "Interest accrual ceases on a nonaccrual loan.",
    )
    OIL_GAS_SCOPE = _u(
        "932-10", "Extractive Activities -- Oil and Gas",
        "Subtopic-level reference: upstream results are distinguished from downstream and from royalty interests.",
    )
    REALESTATE_INCIDENTAL = _u(
        "970-340-25-12", "Real Estate -- General",
        "Incidental operations during development reduce capitalized project cost rather than producing revenue.",
    )
    TIMESHARE_SAMPLER = _u(
        "978-330-35-3", "Real Estate -- Time-Sharing",
        "Sampler and mini-vacation programs are not time-sharing interval sales.",
    )
    NONMONETARY_BARTER = _u(
        "845-10", "Nonmonetary Transactions",
        "Subtopic-level reference: barter transactions are measured at fair value only where that value is determinable.",
    )
    MORTGAGE_ORIGINATION = _u(
        "948-10-05-7", "Financial Services -- Mortgage Banking",
        "Origination volume is not revenue; origination fees and servicing are.",
    )
    FRANCHISOR_SYSTEMWIDE = _u(
        "952-10-05-1", "Franchisors",
        "Franchisee system-wide sales are not franchisor revenue; royalties and fees are.",
    )
    INVESTCO_APPRECIATION = _u(
        "946-320-35-1", "Financial Services -- Investment Companies",
        "Realized gains and unrealized appreciation are presented separately from investment income.",
    )
    REGULATED_REFUNDABLE = _u(
        "980-405-25-1", "Regulated Operations",
        "A rate increase subject to refund is a liability until the contingency resolves.",
    )
    FEDERAL_TERMINATION = _u(
        "912-20-45-5", "Contractors -- Federal Government",
        "Termination claims are recognized only when realization is probable and measurable.",
    )
    FEDERAL_NO_COST = _u(
        "912-310-25-5", "Contractors -- Federal Government",
        "No-cost settlements and unpriced change orders are disclosed rather than recognized as revenue.",
    )
    PLAN_PARTICIPANT_LOANS = _u(
        "962-310-45-2", "Plan Accounting -- Defined Contribution Pension",
        "Participant loans are classified as notes receivable, not investments.",
    )


_INDEX: Dict[str, Citation] = {
    c.key: c
    for c in vars(ASC).values()
    if isinstance(c, Citation)
}


def cite(key: str) -> Citation:
    """Look up a citation by its ASC key, e.g. ``cite("606-10-32-31")``."""
    try:
        return _INDEX[key]
    except KeyError:
        raise KeyError(
            f"ASC {key} is not in the catalog. Add it to gaapai.core.asc "
            "rather than citing an unverified paragraph."
        ) from None


def topic_of(key: str) -> str:
    return cite(key).topic


def all_citations() -> List[Citation]:
    return sorted(_INDEX.values(), key=lambda c: c.key)
