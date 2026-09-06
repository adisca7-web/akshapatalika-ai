"""Semantic mapping: which columns mean what, and how to aggregate them in GAAP terms.

This layer answers the question the computation subskills cannot. *Before* any
arithmetic happens: which physical column in a warehouse is "revenue", what must
be excluded from it, and how does the answer change for the entity's industry.

Without this, an agent handed a data warehouse writes

    SELECT fiscal_year, SUM(amount) FROM fact_revenue GROUP BY fiscal_year

which is syntactically fine and, in accounting terms, meaningless. It may be
summing gross bookings for an agent, gaming handle instead of net win, written
premium instead of earned premium, franchisee system-wide sales instead of
royalties, or contributions of every restriction class in one figure. The SQL is
correct. The number is not, and nothing about the output says so.

So the mapping is deterministic and industry-aware, and its output is injected
into the code-generation prompt as an aggregation contract the model must honour.
Nothing here is inferred by a model: column bindings come from lexical rules over
column names, and the industry rules come from the ASC citations in the reference
pack.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

__all__ = [
    "Concept", "ColumnBinding", "AggregationRule", "RowRule", "IndustryProfile",
    "AggregationPlan", "PROFILES", "bind_columns", "plan_aggregation",
    "industries", "profile_for",
]


class Concept:
    """Canonical accounting concepts a physical column can carry."""

    GROSS_REVENUE = "gross_revenue"
    CONTRA_REVENUE = "contra_revenue"
    NET_REVENUE = "net_revenue"
    DEFERRED_REVENUE = "deferred_revenue"
    # Sales tax, VAT, and GST are collected on behalf of a taxing authority.
    # ASC 606-10-32-2A excludes them from the transaction price entirely -- they
    # are a liability, not revenue, and not merely a deduction from it.
    TAX_COLLECTED = "tax_collected"
    # Shipping charged to the customer is revenue when the entity is principal,
    # but it is a separate performance obligation from the goods and is
    # presented on its own line.
    SHIPPING_REVENUE = "shipping_revenue"
    COST_OF_REVENUE = "cost_of_revenue"
    OPERATING_EXPENSE = "operating_expense"
    RECEIVABLE = "receivable"
    PERIOD = "period"
    ENTITY = "entity"
    SEGMENT = "segment"
    CURRENCY = "currency"
    # A descriptive column -- a name, code, status, or identifier. It may read
    # like an amount concept ("Discount Code", "Tax 1 Name") but holds text, so
    # it must never enter an aggregation expression.
    LABEL = "label"
    UNKNOWN = "unknown"
    # A column that looks like revenue lexically but must never be summed as
    # revenue in this industry -- gaming handle, written premium, franchisee
    # system-wide sales. Warning about these is not enough; they are excluded
    # from the aggregation shape outright.
    FORBIDDEN = "forbidden_as_revenue"


# Lexical rules binding a column name to a concept. Order matters: the first
# match wins, so specific patterns precede general ones. Contra patterns must
# come before revenue patterns, or "sales_returns" binds as revenue and the
# deduction silently becomes an addition.
_RULES: List[tuple] = [
    # Currency precedes the label rule: "curr_code" ends in _code but names the
    # reporting currency, which downstream code needs.
    (Concept.CURRENCY, r"(^currency$|curr_code|^ccy$|currency_code)"),
    # Labels next. "Discount Code" and "Tax 1 Name" match the contra and tax
    # patterns respectively but hold text; summing them raises at runtime.
    (Concept.LABEL,
     r"(^name$|_name$|^id$|_id$|_code$|^code$|_status$|_method$|_reference$"
     r"|_level$|^tags$|^notes$|_province$|_country$|_city$|_zip$|_phone$"
     r"|_street$|_address\d?$|_sku$|^vendor$|^source$|^employee$|^location$)"),
    (Concept.CONTRA_REVENUE,
     r"(return|refund|allowance|chargeback|discount|rebate|markdown|concession"
     r"|promotional|comped|^ceded|_ceded)"),
    (Concept.DEFERRED_REVENUE,
     r"(deferred|unearned|contract_liab|billings_in_excess)"),
    # Tax must precede revenue: a "sales_tax" column contains "sales".
    (Concept.TAX_COLLECTED,
     r"(^tax|_tax$|taxes|sales_tax|vat_|_vat$|^gst|_gst$|duty_collected)"),
    (Concept.SHIPPING_REVENUE,
     r"(^shipping$|shipping_(revenue|income|charged|fee)|freight_billed"
     r"|delivery_fee)"),
    (Concept.NET_REVENUE,
     r"(^net_(revenue|sales|rev)|(revenue|sales)_net$|net_win)"),
    (Concept.GROSS_REVENUE,
     r"(revenue|sales|turnover|billings|premium|gmv|bookings|handle|drop"
     r"|fees_earned|royalt|^subtotal$|_subtotal$|merchandise)"),
    (Concept.COST_OF_REVENUE,
     r"(cogs|cost_of_(goods|sales|revenue|service)|claims_incurred|loss_and_lae"
     r"|film_cost|participation)"),
    (Concept.RECEIVABLE, r"(receivable|ar_balance|debtor)"),
    (Concept.OPERATING_EXPENSE, r"(opex|operating_expense|sga|admin_expense)"),
    (Concept.PERIOD,
     r"(fiscal_year|^fy$|^year$|period|month|quarter|^date$|posting_dt|_dt$"
     r"|_at$|_date$|^created|^paid_at$|order_date)"),
    (Concept.ENTITY, r"(entity|company|legal_entity|subsidiary)"),
    (Concept.SEGMENT, r"(segment|business_unit|^bu$|division|product_line|region)"),
    (Concept.CURRENCY, r"(currency|curr_code|^ccy$)"),
]


@dataclass
class ColumnBinding:
    """A physical column bound to an accounting concept."""

    column: str
    concept: str
    confidence: str      # "high" | "low"
    rationale: str

    def to_dict(self) -> dict:
        return {"column": self.column, "concept": self.concept,
                "confidence": self.confidence, "rationale": self.rationale}


@dataclass
class AggregationRule:
    """One accounting constraint on how a concept may be aggregated."""

    requirement: str
    citation: str
    severity: str = "must"   # "must" | "should" | "note"

    def render(self) -> str:
        mark = {"must": "MUST", "should": "SHOULD", "note": "NOTE"}[self.severity]
        return f"[{mark}] {self.requirement}  (ASC {self.citation})"


@dataclass
class RowRule:
    """A row-level exclusion or reclassification.

    Column binding cannot express every GAAP distinction. A gift card sale is
    not revenue -- it is a contract liability until redeemed (ASC 606-10-45-1)
    -- but no *column* says "gift card". The signal lives in the row: a line
    item named "Gift Card", or structurally, one that neither requires shipping
    nor attracts tax, because a gift card is not taxed at sale precisely because
    the sale is not the sale.

    Binding the right column and then summing the wrong rows produces exactly
    the same kind of confidently wrong number the column rules exist to prevent.
    """

    name: str
    match_column: str          # regex over normalised column names
    match_value: str           # regex the cell value must match
    becomes: str               # the Concept these rows carry instead
    citation: str
    requirement: str
    severity: str = "must"

    def render(self, present_columns: List[str]) -> str:
        mark = {"must": "MUST", "should": "SHOULD", "note": "NOTE"}[self.severity]
        cols = ", ".join(present_columns) if present_columns else "(column not found)"
        return (f"[{mark}] {self.requirement}  (ASC {self.citation})\n"
                f"         WHERE {cols} matches /{self.match_value}/ "
                f"-> treat as {self.becomes}")


@dataclass
class IndustryProfile:
    """How revenue behaves in one specialized-industry regime."""

    asc: str
    name: str
    revenue_caption: str
    rules: List[AggregationRule] = field(default_factory=list)
    row_rules: List[RowRule] = field(default_factory=list)
    common_wrong_column: str = ""
    skill_file: str = ""
    # Regex over normalised column names. A match is demoted to FORBIDDEN and
    # kept out of the aggregation shape, whatever the lexical rules concluded.
    forbidden: str = ""

    def render(self) -> str:
        out = [f"INDUSTRY: {self.name} (ASC {self.asc})",
               f"Revenue caption: {self.revenue_caption}"]
        if self.common_wrong_column:
            out.append(f"Frequently mistaken for revenue: {self.common_wrong_column}")
        for r in self.rules:
            out.append("  " + r.render())
        if self.skill_file:
            out.append(f"  Reference: {self.skill_file}")
        return "\n".join(out)


def _r(req: str, cite: str, sev: str = "must") -> AggregationRule:
    return AggregationRule(req, cite, sev)


# ---------------------------------------------------------------------------
# Industry profiles. Each states what revenue actually means in that regime and
# what a naive SUM gets wrong. Rules trace to the reference pack's citations.
# ---------------------------------------------------------------------------

PROFILES: Dict[str, IndustryProfile] = {
    "606": IndustryProfile(
        asc="606", name="General (contracts with customers)",
        revenue_caption="Revenue from contracts with customers",
        common_wrong_column="gross bookings or invoiced amount",
        skill_file="chapters/ch38-revenue-from-contracts-with-customers.md",
        forbidden=r"(gross_bookings|gmv|invoiced_amount)",
        rules=[
            _r("Report net of contra-revenue: returns, refunds, allowances, price concessions.",
               "606-10-32-2"),
            _r("Settle principal vs agent before summing. An agent reports only the net fee, "
               "never gross consideration.", "606-10-55-36"),
            _r("Exclude amounts billed but not yet earned; those are contract liabilities.",
               "606-10-45-1"),
            _r("Variable consideration must be constrained; unconstrained accruals overstate "
               "revenue.", "606-10-32-11", "should"),
        ],
    ),
    "retail": IndustryProfile(
        asc="606", name="Retail and e-commerce",
        revenue_caption="Net product revenue, with shipping shown separately",
        common_wrong_column="order Total (includes sales tax and shipping)",
        skill_file="chapters/ch38-revenue-from-contracts-with-customers.md",
        forbidden=r"(^total$|order_total|gross_total|grand_total|amount_charged)",
        rules=[
            _r("Sales tax collected is a liability, not revenue. Exclude it from the "
               "transaction price entirely.", "606-10-32-2A"),
            _r("Order Total includes tax and shipping. Use the merchandise subtotal "
               "as product revenue.", "606-10-32-2"),
            _r("Refunds and expected returns are contra-revenue; a refunded order "
               "carries no revenue.", "606-10-32-2"),
            _r("Shipping charged to the customer is a separate performance obligation; "
               "present it apart from product revenue.", "606-10-25-14"),
            _r("A line-item export repeats the order header on the first row only. "
               "Deduplicate to order level before summing order totals.",
               "606-10-32-2"),
            _r("Recognise on transfer of control (delivery), not on order placement "
               "or payment.", "606-10-25-23", "should"),
        ],
        row_rules=[
            RowRule(
                name="gift_card_sales",
                match_column=r"(lineitem_name|item_name|product_(name|title)|sku)",
                match_value=r"(?i)(gift\s?card|e-?gift|gift\s?certificate|voucher)",
                becomes=Concept.DEFERRED_REVENUE,
                citation="606-10-45-1",
                requirement=("Gift card sales are a CONTRACT LIABILITY, not revenue. "
                             "Revenue arises on redemption; unredeemed breakage under "
                             "ASC 606-10-55-46."),
            ),
            RowRule(
                name="gift_card_structural",
                match_column=r"(requires_shipping|taxable)",
                match_value=r"(?i)^(false|0|no)$",
                becomes=Concept.DEFERRED_REVENUE,
                citation="606-10-45-1",
                requirement=("A line that neither requires shipping nor attracts tax is "
                             "usually a gift card or service credit -- it is not taxed at "
                             "sale because the sale is not the sale. Confirm before "
                             "including in revenue."),
                severity="should",
            ),
            RowRule(
                name="cancelled_orders",
                match_column=r"(cancelled_at|canceled_at|void)",
                match_value=r".+",
                becomes=Concept.FORBIDDEN,
                citation="606-10-25-1",
                requirement="A cancelled order is not a contract; exclude it entirely.",
            ),
            RowRule(
                name="test_orders",
                match_column=r"(lineitem_name|item_name|product_(name|title))",
                match_value=r"(?i)^(test|demo|sample|custom item|placeholder)\b",
                becomes=Concept.FORBIDDEN,
                citation="606-10-25-1",
                requirement=("Test and placeholder line items are not contracts with "
                             "customers. Confirm whether these are live sales."),
                severity="should",
            ),
        ],
    ),
    "926": IndustryProfile(
        asc="926", name="Entertainment - Film",
        revenue_caption="Feature film and television revenue by market and territory",
        common_wrong_column="ultimate_revenue (a forecast denominator, not actual revenue)",
        skill_file="industries/asc926-entertainment-film.md",
        forbidden=r"(ultimate_revenue|ultimate_rev)",
        rules=[
            _r("Never sum ultimate revenue as actual revenue. It is the forecast denominator "
               "of the individual-film-forecast method.", "926-20-35-4"),
            _r("Exclude films not yet released; revenue and amortisation begin at release.",
               "926-20-35-1"),
            _r("Participation and residual costs are COST, not contra-revenue.", "926-10-20"),
            _r("Third-party advertising reimbursements offset exploitation cost, not revenue.",
               "926-20-35-5"),
            _r("Split by market and territory; ultimate revenue is includable only where "
               "evidence for that market exists.", "926-20-35-5", "should"),
        ],
    ),
    "944": IndustryProfile(
        asc="944", name="Financial Services - Insurance",
        revenue_caption="Premiums earned (not written)",
        common_wrong_column="written_premium or premium_billed",
        skill_file="industries/asc944-insurance.md",
        forbidden=r"(written_premium|premium_written|premium_billed|gross_written)",
        rules=[
            _r("Sum EARNED premium, not WRITTEN premium. Written premium is a billing metric.",
               "944-605-25-1"),
            _r("Split short-duration from long-duration contracts; they earn on different bases.",
               "944-605-25-1"),
            _r("Short-duration earns over the term in proportion to insurance provided; "
               "long-duration accrues as premiums become due.", "944-605-25-3"),
            _r("Report reinsurance recoverables as assets. Do NOT net them against premium.",
               "944-20"),
            _r("Where benefits run longer than the premium payment term, earn over the longer "
               "benefit period.", "944-605-25-3", "should"),
        ],
    ),
    "924": IndustryProfile(
        asc="924", name="Entertainment - Casinos",
        revenue_caption="Net win (gross gaming revenue less promotional allowances)",
        common_wrong_column="handle or drop (amounts wagered, not revenue)",
        skill_file="industries/asc924-casinos.md",
        forbidden=r"(handle|^drop$|_drop$|coin_in|wagered)",
        rules=[
            _r("Handle and drop are amounts wagered, not revenue. Use net win.", "924-10-05-3"),
            _r("Outstanding chips are a liability, not revenue.", "924-405-25-2"),
            _r("Fixed-odds wagering contracts are ASC 606 revenue, not ASC 815 derivatives.",
               "924-815-25-1"),
        ],
    ),
    "985": IndustryProfile(
        asc="985", name="Software",
        revenue_caption="Licence, post-contract support, and services revenue, separately",
        common_wrong_column="ARR or total contract value",
        skill_file="industries/asc985-software.md",
        forbidden=r"(^arr$|annual_recurring|total_contract_value|^tcv$|bookings)",
        rules=[
            _r("Split licence, post-contract support (PCS), and professional services; they "
               "transfer on different patterns.", "606-10-25-14"),
            _r("ARR and total contract value are bookings metrics, not GAAP revenue.",
               "606-10-32-2"),
            _r("Where significant customisation exists, delivering the software is not "
               "delivering the product; use a production-type model.", "985-605-25-2"),
            _r("Capitalised software cost is an asset; do not net its amortisation against "
               "revenue.", "985-20-35-1", "note"),
        ],
    ),
    "958": IndustryProfile(
        asc="958", name="Not-for-Profit Entities",
        revenue_caption="Contributions and exchange revenue, by donor restriction class",
        common_wrong_column="a single undifferentiated revenue total",
        skill_file="industries/asc958-not-for-profit.md",
        rules=[
            _r("Split net assets WITH donor restrictions from WITHOUT. A single total is not "
               "reportable.", "958-210-45-2"),
            _r("Exclude conditional contributions entirely; they are not yet revenue.",
               "958-605-25-5A"),
            _r("Restrictions affect classification only; conditions affect timing.",
               "958-605-25-2"),
            _r("Report revenues and expenses GROSS, not net.", "958-205"),
            _r("Where the entity is an agent for a donor-named beneficiary, the receipt is a "
               "liability, not revenue.", "958-20-25-1"),
        ],
    ),
    "942": IndustryProfile(
        asc="942", name="Financial Services - Depository and Lending",
        revenue_caption="Interest income and noninterest (fee) income, separately",
        common_wrong_column="a combined total_income",
        skill_file="industries/asc942-depository-and-lending.md",
        rules=[
            _r("Split interest income from noninterest (fee) income.", "942-10-S45-1"),
            _r("Loan origination fees are a yield adjustment, not fee income.", "942-310-25-3"),
            _r("Where accrual is suspended and collectibility is doubtful, payments reduce "
               "PRINCIPAL, not interest income.", "942-310-35-2"),
        ],
    ),
    "932": IndustryProfile(
        asc="932", name="Extractive Activities - Oil and Gas",
        revenue_caption="Oil, gas, and NGL revenue at net revenue interest",
        common_wrong_column="gross wellhead value (before royalty owners' share)",
        skill_file="industries/asc932-oil-and-gas.md",
        forbidden=r"(gross_wellhead|wellhead_gross|gross_production_value)",
        rules=[
            _r("Use net revenue interest; gross wellhead value includes the royalty owners' "
               "share.", "932-10"),
            _r("Split oil, gas, and natural gas liquids; they price independently.",
               "932-235", "should"),
            _r("Exclude refining, marketing, and transportation - outside the ASC 932 industry "
               "codification.", "932-10", "note"),
        ],
    ),
    "970": IndustryProfile(
        asc="970", name="Real Estate - General",
        revenue_caption="Real estate sales and rental revenue",
        common_wrong_column="contract sales value including unclosed contracts",
        skill_file="industries/asc970-real-estate-general.md",
        forbidden=r"(contract_sales_value|unclosed)",
        rules=[
            _r("Incidental operations during development REDUCE capitalised cost. They are "
               "never revenue.", "970-340-25-12"),
            _r("A partly occupied project's completed portions are separate projects.",
               "970-340-25-18", "should"),
        ],
    ),
    "978": IndustryProfile(
        asc="978", name="Real Estate - Time-Sharing",
        revenue_caption="Interval sales, net of expected cancellation",
        common_wrong_column="gross contract value before the default provision",
        skill_file="industries/asc978-real-estate-time-sharing.md",
        rules=[
            _r("Default is structural, not exceptional; provide for it up front.",
               "978-10-05-5"),
            _r("Incidental operations (sampler programs, minivacations) reduce inventory cost, "
               "never revenue.", "978-330-35-3"),
        ],
    ),
    "920": IndustryProfile(
        asc="920", name="Entertainment - Broadcasters",
        revenue_caption="Advertising revenue by daypart, plus network compensation",
        common_wrong_column="gross billings before agency commission",
        skill_file="industries/asc920-broadcasters.md",
        rules=[
            _r("Programme licence cost is an asset; its amortisation is cost, not "
               "contra-revenue.", "920-350-35-1"),
            _r("Split by daypart where the entity prices and manages on that basis.",
               "920-350-20", "should"),
        ],
    ),
    "948": IndustryProfile(
        asc="948", name="Financial Services - Mortgage Banking",
        revenue_caption="Gain on sale of loans, plus loan servicing fees",
        common_wrong_column="loan principal originated (a volume metric)",
        skill_file="industries/asc948-mortgage-banking.md",
        forbidden=r"(origination_volume|principal_originated|loan_volume|funded_volume)",
        rules=[
            _r("Origination volume is not revenue. Revenue is gain on sale plus servicing fees.",
               "948-10-05-7"),
            _r("Servicing fees accrue on outstanding principal; adjust the sale price where the "
               "stated rate differs materially from the normal servicing rate.", "948-10-05-7"),
        ],
    ),
    "952": IndustryProfile(
        asc="952", name="Franchisors",
        revenue_caption="Initial franchise fees and continuing royalty revenue",
        common_wrong_column="franchisee system-wide sales",
        skill_file="industries/asc952-franchisors.md",
        forbidden=r"(system_?wide|franchisee_sales|gross_system)",
        rules=[
            _r("System-wide franchisee sales are NOT franchisor revenue. The royalty on them is.",
               "952-10-05-1"),
            _r("Reverse revenue on repossession only where the fee was refunded.",
               "952-605-25-17"),
        ],
    ),
    "946": IndustryProfile(
        asc="946", name="Financial Services - Investment Companies",
        revenue_caption="Investment income and realised/unrealised appreciation, separately",
        common_wrong_column="change in net assets treated as revenue",
        skill_file="industries/asc946-investment-companies.md",
        rules=[
            _r("Report investment income separately from net appreciation and depreciation.",
               "946-320-35-1"),
            _r("Record dividend income on the EX-DIVIDEND date, not the record or payable date.",
               "946-320-25-4"),
            _r("Securities transactions are recorded on TRADE date.", "946-320-25-1"),
        ],
    ),
    "980": IndustryProfile(
        asc="980", name="Regulated Operations",
        revenue_caption="Regulated revenue, distinguishing alternative revenue programs",
        common_wrong_column="billed amounts including refundable rate increases",
        skill_file="industries/asc980-regulated-operations.md",
        rules=[
            _r("Rate increases collected to recover FUTURE costs are a liability (unearned "
               "revenue) until the condition is satisfied.", "980-405-25-1"),
            _r("Alternative revenue programs are recognised only once the billing events have "
               "occurred and three criteria are met.", "980-605-25-4"),
        ],
    ),
}

# ---------------------------------------------------------------------------
# Row-level rules, derived from the anti-pattern and decision-rule sections of
# the industry files in skills/wiley-gaap/industries/.
#
# These were written as prose in the reference pack first and executed nowhere,
# which is exactly how the gift-card miss happened: the rule existed, the agent
# could read it, and nothing in the pipeline enforced it. A rule that only lives
# in a document is a rule the aggregation will not honour.
#
# Attached after PROFILES is constructed so each rule sits next to its industry
# without making the profile literals unreadable.
# ---------------------------------------------------------------------------

def _rr(name, col, val, becomes, cite, req, sev="must") -> RowRule:
    return RowRule(name=name, match_column=col, match_value=val,
                   becomes=becomes, citation=cite, requirement=req, severity=sev)


_ROW_RULES: Dict[str, List[RowRule]] = {
    "606": [
        _rr("unsatisfied_obligations", r"(status|delivery_status|fulfil)",
            r"(?i)(pending|not.?delivered|undelivered|awaiting|backorder)",
            Concept.DEFERRED_REVENUE, "606-10-45-1",
            "Amounts billed before control transfers are contract liabilities, "
            "not revenue."),
        _rr("cancelled_contracts", r"(cancel|void|status)",
            r"(?i)(cancelled|canceled|voided)", Concept.FORBIDDEN, "606-10-25-1",
            "A cancelled arrangement is not a contract with a customer."),
    ],
    "926": [
        _rr("unreleased_films", r"(release_status|status|release_date)",
            r"(?i)(unreleased|not.?released|in.?production|development|pending)",
            Concept.FORBIDDEN, "926-20-35-1",
            "Films not yet released earn no revenue; recognition and amortisation "
            "both begin at release."),
        _rr("advertising_reimbursements", r"(item|type|category|description)",
            r"(?i)(advertis\w+ reimburse|co.?op advertis|promo reimburse)",
            Concept.CONTRA_REVENUE, "926-20-35-5",
            "Third-party advertising reimbursements offset exploitation cost. "
            "They are never revenue."),
        _rr("participation_costs", r"(item|type|category|description)",
            r"(?i)(participation|residual)", Concept.COST_OF_REVENUE, "926-10-20",
            "Participations and residuals are COST, not contra-revenue."),
    ],
    "944": [
        _rr("duration_split", r"(contract_type|duration|product_type|line_of_business)",
            r"(?i)(short.?duration|long.?duration)", Concept.GROSS_REVENUE,
            "944-605-25-1",
            "Short-duration and long-duration contracts earn on different bases "
            "and must be aggregated separately, never combined."),
        _rr("ceded_reinsurance", r"(item|type|category|treaty|description)",
            r"(?i)(ceded|reinsur)", Concept.CONTRA_REVENUE, "944-20",
            "Ceded premium reduces premium revenue; reinsurance RECOVERABLES are "
            "assets and are never netted against it."),
    ],
    "958": [
        _rr("conditional_contributions", r"(condition|status|restriction_type)",
            # (?<!un) is load-bearing: an UNconditional promise IS revenue, and
            # a bare /conditional/ would exclude it.
            r"(?i)((?<!un)conditional|condition.?not.?met|barrier|unmet)",
            Concept.FORBIDDEN, "958-605-25-5A",
            "A conditional contribution is NOT YET revenue. Exclude it entirely "
            "until the barriers are substantially met."),
        _rr("restriction_split", r"(restriction|donor_restriction|net_asset_class)",
            r"(?i)(with donor|without donor|restricted|unrestricted)",
            Concept.GROSS_REVENUE, "958-210-45-2",
            "Split net assets WITH donor restrictions from WITHOUT. A single "
            "undifferentiated revenue total is not reportable."),
        _rr("agency_transactions", r"(role|relationship|type)",
            r"(?i)(agent|intermediary|pass.?through|custodial)",
            Concept.FORBIDDEN, "958-20-25-1",
            "Assets received as agent for a donor-named beneficiary are a "
            "LIABILITY, not revenue."),
    ],
    "985": [
        _rr("element_split", r"(item|element|product_type|revenue_type|description)",
            r"(?i)(licen[cs]e|pcs|post.?contract|maintenance|support|service)",
            Concept.GROSS_REVENUE, "606-10-25-14",
            "Licence, post-contract support, and professional services transfer on "
            "different patterns and must be separated."),
        _rr("internal_use", r"(item|category|project_type|description)",
            r"(?i)(internal.?use)", Concept.FORBIDDEN, "350-40-15-2",
            "Internal-use software is ASC 350-40, not ASC 985-20, and generates no "
            "external revenue."),
    ],
    "924": [
        _rr("promotional_comps", r"(item|type|category|description)",
            r"(?i)(promotional|comp\b|comped|free.?play)", Concept.CONTRA_REVENUE,
            "924-10-05-3",
            "Promotional allowances and comps reduce gross gaming revenue to net win."),
        _rr("outstanding_chips", r"(item|type|category|description)",
            r"(?i)(chip|token|outstanding.?chip)", Concept.FORBIDDEN,
            "924-405-25-2",
            "Chips in patrons' hands are a LIABILITY, not revenue."),
    ],
    "942": [
        _rr("income_split", r"(income_type|category|revenue_type|description)",
            r"(?i)(interest|fee|noninterest|non.?interest)", Concept.GROSS_REVENUE,
            "942-10-S45-1",
            "Interest income and noninterest (fee) income are presented separately."),
        _rr("nonaccrual_loans", r"(accrual_status|loan_status|status)",
            r"(?i)(non.?accrual|suspended|impaired|doubtful)", Concept.FORBIDDEN,
            "942-310-35-2",
            "Where accrual is suspended and collectibility is doubtful, payments "
            "reduce PRINCIPAL, not interest income."),
    ],
    "932": [
        _rr("downstream_activities", r"(segment|activity|business_line|category)",
            r"(?i)(refin|marketing|transport|midstream|downstream)",
            Concept.FORBIDDEN, "932-10",
            "Refining, marketing, and transportation fall outside the ASC 932 "
            "extractive industry codification."),
        _rr("royalty_interest", r"(interest_type|working_interest|revenue_interest)",
            r"(?i)(royalty|overriding|orri)", Concept.CONTRA_REVENUE, "932-10",
            "Royalty owners' share is not the operator's revenue; report at net "
            "revenue interest."),
    ],
    "970": [
        _rr("incidental_operations", r"(item|type|category|description)",
            r"(?i)(incidental|interim.?rental|holding.?period)",
            Concept.CONTRA_REVENUE, "970-340-25-12",
            "Incidental operations during development REDUCE capitalised project "
            "cost. They are never revenue."),
        _rr("unclosed_contracts", r"(status|closing_status)",
            r"(?i)(unclosed|pending|not.?closed|in.?escrow)", Concept.FORBIDDEN,
            "606-10-25-23", "Revenue arises on transfer of control, not on contract "
            "signature."),
    ],
    "978": [
        _rr("sampler_programs", r"(item|type|program|category|description)",
            r"(?i)(sampler|minivacation|mini.?vacation|trial.?stay)",
            Concept.CONTRA_REVENUE, "978-330-35-3",
            "Sampler programs and minivacations are incidental operations: excess "
            "revenue reduces inventory cost, never income."),
    ],
    "952": [
        _rr("system_wide_sales", r"(item|type|metric|category|description)",
            r"(?i)(system.?wide|franchisee.?sales|gross.?system)",
            Concept.FORBIDDEN, "952-10-05-1",
            "Franchisee system-wide sales belong to the franchisee. Only the "
            "royalty on them is franchisor revenue."),
    ],
    "946": [
        _rr("appreciation_split", r"(income_type|category|description)",
            r"(?i)(appreciat|depreciat|unrealised|unrealized|realised gain|realized gain)",
            Concept.GROSS_REVENUE, "946-320-35-1",
            "Net appreciation and depreciation are reported separately from "
            "investment income."),
    ],
    "948": [
        _rr("origination_volume", r"(item|metric|type|category|description)",
            r"(?i)(origination.?volume|funded.?volume|principal.?originated)",
            Concept.FORBIDDEN, "948-10-05-7",
            "Origination volume is a production metric. Revenue is gain on sale "
            "plus servicing fees."),
    ],
    "912": [
        _rr("no_cost_settlements", r"(settlement_type|status|type|description)",
            r"(?i)(no.?cost.?settlement)", Concept.FORBIDDEN, "912-310-25-5",
            "A no-cost settlement involves no sale and no profit accrual."),
        _rr("termination_claims", r"(item|type|category|description)",
            r"(?i)(termination.?claim|convenience.?termination)",
            Concept.GROSS_REVENUE, "912-20-45-5",
            "Material termination claims are separately captioned in the revenues "
            "section, not merged into contract revenue.", "should"),
    ],
    "980": [
        _rr("refundable_rate_increases", r"(item|type|category|description)",
            r"(?i)(refundable|future.?cost.?recovery|provisional.?rate)",
            Concept.DEFERRED_REVENUE, "980-405-25-1",
            "Rate increases collected to recover FUTURE costs are unearned revenue "
            "until the condition is satisfied."),
    ],
    "920": [
        _rr("barter_trade", r"(item|type|category|payment|description)",
            r"(?i)(barter|trade.?out|non.?cash.?advertis)", Concept.GROSS_REVENUE,
            "845-10", "Barter advertising is a nonmonetary exchange under ASC 845; "
            "measure at fair value and disclose separately.", "should"),
    ],
    "960": [
        _rr("participant_loans", r"(item|asset_type|category|description)",
            r"(?i)(participant.?loan|loan.?to.?participant)", Concept.RECEIVABLE,
            "962-310-45-2",
            "Participant loans are NOTES RECEIVABLE at unpaid principal plus "
            "accrued interest, not investments at fair value."),
    ],
}

# Industries without a distinctive revenue-aggregation divergence still resolve
# to their reference file, so the agent can always reach the underlying rules.
_REFERENCE_ONLY: Dict[str, tuple] = {
    "912": ("Contractors - Federal Government",
            "industries/asc912-federal-government-contractors.md"),
    "922": ("Entertainment - Cable Television",
            "industries/asc922-cable-television.md"),
    "928": ("Entertainment - Music", "industries/asc928-music.md"),
    "950": ("Financial Services - Title Plant", "industries/asc950-title-plant.md"),
    "960": ("Plan Accounting", "industries/asc960-plan-accounting.md"),
    "976": ("Real Estate - Retail Land",
            "industries/asc976-real-estate-retail-land.md"),
}


# Attach row rules to their profiles.
#
# This runs *after* _REFERENCE_ONLY so an unattached key can be told apart from
# a mistyped one. Previously the loop was `if _code in PROFILES` and silently
# dropped anything else, which cost three rules -- ASC 912 termination claims
# and no-cost settlements, and ASC 962 participant loans -- that never fired on
# any query. A rule that does not apply must never fail quietly; that is the
# same fail-open behaviour the whole layer exists to prevent.
_unattached = sorted(set(_ROW_RULES) - set(PROFILES) - set(_REFERENCE_ONLY))
if _unattached:
    raise RuntimeError(
        f"_ROW_RULES defines rules for {_unattached}, which is neither an "
        "aggregation profile nor a reference-only industry. Rules keyed to an "
        "unknown industry can never fire. Add the profile or fix the key."
    )

for _code, _rules in _ROW_RULES.items():
    if _code in PROFILES:
        PROFILES[_code].row_rules.extend(_rules)
    # Reference-only codes have no standing profile object; profile_for()
    # builds one on demand and picks their rules up from _ROW_RULES directly.


def industries() -> List[str]:
    """Every industry code with an aggregation profile or a reference file."""
    return sorted(set(PROFILES) | set(_REFERENCE_ONLY))


def profile_for(industry: Optional[str]) -> IndustryProfile:
    """Resolve an industry code or name to a profile.

    Defaults to the ASC 606 baseline, which is the correct fallback: a general
    commercial entity still has to net contra-revenue and settle principal
    versus agent.
    """
    if not industry:
        return PROFILES["606"]
    key = re.sub(r"^asc\s*", "", str(industry).strip().lower())
    if key in PROFILES:
        return PROFILES[key]
    for prof in PROFILES.values():
        if key and key in prof.name.lower():
            return prof
    for code, (name, path) in _REFERENCE_ONLY.items():
        if key == code or (key and key in name.lower()):
            return IndustryProfile(
                asc=code, name=name,
                revenue_caption="See the reference file",
                skill_file=path,
                rules=list(PROFILES["606"].rules),
                # Carry the industry's own row rules too. Omitting these was the
                # second half of the same bug: even once attachment was fixed, a
                # reference-only industry would still have arrived here with an
                # empty row_rules list.
                row_rules=list(_ROW_RULES.get(code, [])),
            )
    return PROFILES["606"]


def bind_columns(columns: Sequence[str]) -> List[ColumnBinding]:
    """Bind physical column names to accounting concepts, lexically."""
    out: List[ColumnBinding] = []
    for col in columns:
        norm = re.sub(r"[^a-z0-9]+", "_", str(col).lower()).strip("_")
        bound = False
        for concept, pattern in _RULES:
            if re.search(pattern, norm):
                out.append(ColumnBinding(
                    column=str(col), concept=concept, confidence="high",
                    rationale=f"column name matches the {concept} pattern",
                ))
                bound = True
                break
        if not bound:
            out.append(ColumnBinding(
                column=str(col), concept=Concept.UNKNOWN, confidence="low",
                rationale="no lexical rule matched; confirm before aggregating",
            ))
    return out


@dataclass
class AggregationPlan:
    """The accounting contract for aggregating a concept from a real schema."""

    concept: str
    industry: IndustryProfile
    bindings: List[ColumnBinding]
    warnings: List[str] = field(default_factory=list)

    def columns_for(self, concept: str) -> List[str]:
        return [b.column for b in self.bindings if b.concept == concept]

    def applicable_row_rules(self):
        """Row rules whose trigger column actually exists in this schema.

        A rule about gift-card line items is noise on a schema with no line-item
        column, so only rules that can actually fire are surfaced.
        """
        out = []
        for rule in self.industry.row_rules:
            pat = re.compile(rule.match_column)
            hits = [b.column for b in self.bindings
                    if pat.search(re.sub(r"[^a-z0-9]+", "_", b.column.lower()).strip("_"))]
            if hits:
                out.append((rule, hits))
        return out

    @property
    def unknown_columns(self) -> List[str]:
        return self.columns_for(Concept.UNKNOWN)

    @property
    def blocked(self) -> bool:
        """True when no revenue column could be identified at all."""
        return not (self.columns_for(Concept.GROSS_REVENUE)
                    or self.columns_for(Concept.NET_REVENUE))

    def render(self) -> str:
        """The block injected into the code-generation prompt."""
        out = ["=== GAAP AGGREGATION CONTRACT ===", ""]
        out.append(self.industry.render())
        out.append("")
        out.append("COLUMN BINDINGS (derived from column names -- do not re-guess these):")
        for b in self.bindings:
            if b.concept != Concept.UNKNOWN:
                out.append(f"  {b.column:<30} -> {b.concept}")

        gross = self.columns_for(Concept.GROSS_REVENUE)
        contra = self.columns_for(Concept.CONTRA_REVENUE)
        net = self.columns_for(Concept.NET_REVENUE)
        deferred = self.columns_for(Concept.DEFERRED_REVENUE)
        period = self.columns_for(Concept.PERIOD)
        tax = self.columns_for(Concept.TAX_COLLECTED)
        shipping = self.columns_for(Concept.SHIPPING_REVENUE)

        out.append("")
        out.append("REQUIRED AGGREGATION SHAPE:")
        if net and not gross:
            out.append(f"  net revenue = SUM({net[0]})   (already net)")
        elif gross:
            expr = " + ".join(f"SUM({c})" for c in gross)
            if contra:
                expr += " - " + " - ".join(f"SUM({c})" for c in contra)
            out.append(f"  net revenue = {expr}")
        else:
            out.append("  NO revenue column identified. Ask which column carries revenue. "
                       "Do not select one by position or by guessing.")
        if contra:
            out.append(f"  Contra-revenue MUST be deducted: {', '.join(contra)}")
        if deferred:
            out.append(f"  EXCLUDE deferred/unearned columns: {', '.join(deferred)}")
        if tax:
            out.append(f"  EXCLUDE tax collected -- it is a liability, not revenue "
                       f"(ASC 606-10-32-2A): {', '.join(tax)}")
        if shipping:
            out.append(f"  PRESENT SEPARATELY, do not merge into product revenue: "
                       f"{', '.join(shipping)}")
        if period:
            out.append(f"  Group by period column: {period[0]}")

        applicable = self.applicable_row_rules()
        if applicable:
            out.append("")
            out.append("ROW-LEVEL RULES -- filter rows BEFORE aggregating. Binding the "
                       "right column and summing the wrong rows is the same error:")
            for rule, cols in applicable:
                out.append("  " + rule.render(cols))

        forbidden = self.columns_for(Concept.FORBIDDEN)
        if forbidden:
            out.append("")
            out.append(f"FORBIDDEN AS REVENUE under ASC {self.industry.asc} -- "
                       "these columns look like revenue but are not:")
            for c in forbidden:
                out.append(f"  {c}   NEVER include in a revenue total")

        if self.unknown_columns:
            out.append("")
            out.append("UNBOUND COLUMNS (do not aggregate without confirming):")
            out.append("  " + ", ".join(self.unknown_columns))

        if self.warnings:
            out.append("")
            out.append("WARNINGS:")
            for w in self.warnings:
                out.append(f"  ! {w}")

        out.append("")
        out.append("If any MUST rule cannot be satisfied with the available columns, say so "
                   "and stop. Do not produce a figure that violates one.")
        return "\n".join(out)

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "industry": {"asc": self.industry.asc, "name": self.industry.name},
            "bindings": [b.to_dict() for b in self.bindings],
            "warnings": self.warnings,
            "blocked": self.blocked,
        }


def plan_aggregation(
    columns: Sequence[str],
    industry: Optional[str] = None,
    concept: str = Concept.NET_REVENUE,
) -> AggregationPlan:
    """Build the aggregation contract for a schema and industry.

    Deterministic: the same columns and industry always produce the same plan.
    """
    prof = profile_for(industry)
    bindings = bind_columns(columns)
    warnings: List[str] = []

    # Demote industry-forbidden columns. A gaming handle column matches the
    # revenue pattern lexically and would otherwise land in the SUM; warning
    # about it is not enough, because the model has already been handed a
    # correct-looking aggregation expression containing it.
    if prof.forbidden:
        pat = re.compile(prof.forbidden)
        for b in bindings:
            norm = re.sub(r"[^a-z0-9]+", "_", b.column.lower()).strip("_")
            # UNKNOWN is included deliberately: a bookings metric like ARR or
            # TCV matches no revenue pattern, so it would otherwise pass through
            # as merely "unbound" rather than being named as forbidden.
            if b.concept in (Concept.GROSS_REVENUE, Concept.NET_REVENUE,
                             Concept.UNKNOWN) and pat.search(norm):
                b.concept = Concept.FORBIDDEN
                b.confidence = "high"
                b.rationale = (f"forbidden as revenue under ASC {prof.asc}: "
                               f"{prof.common_wrong_column or 'not a revenue measure'}")

    gross = [b for b in bindings if b.concept == Concept.GROSS_REVENUE]
    contra = [b for b in bindings if b.concept == Concept.CONTRA_REVENUE]
    net = [b for b in bindings if b.concept == Concept.NET_REVENUE]

    if not gross and not net:
        warnings.append("No revenue column identified. Ask the user which column carries "
                        "revenue rather than selecting one by position.")
    if gross and net:
        warnings.append("Both gross and net revenue columns are present. Summing both "
                        "double-counts; choose one basis and state which.")
    if gross and not contra:
        warnings.append("A gross revenue column exists with no contra-revenue column. "
                        "Confirm returns, refunds, and allowances are already deducted "
                        "(ASC 606-10-32-2).")
    if prof.common_wrong_column:
        warnings.append(f"For {prof.name}, verify the chosen column is not "
                        f"{prof.common_wrong_column}.")
    if not [b for b in bindings if b.concept == Concept.PERIOD]:
        warnings.append("No period column identified; a trend cannot be grouped reliably.")

    return AggregationPlan(concept=concept, industry=prof,
                           bindings=bindings, warnings=warnings)
