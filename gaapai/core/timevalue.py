"""Present value machinery, in exact decimal arithmetic.

Used by ASC 842 lease measurement, ASC 606 significant financing components,
and ASC 326 discounted cash flow. Kept in one place so the discounting
convention (end-of-period vs beginning-of-period) is applied consistently --
annuity-due versus ordinary-annuity is a common source of lease liability
errors of a few percent.
"""

from __future__ import annotations

from decimal import Decimal, localcontext
from typing import Iterable, List, Sequence, Tuple

from .money import D, Money, WORKING_PRECISION

__all__ = [
    "discount_factor",
    "present_value",
    "pv_annuity",
    "implicit_rate",
    "periodic_rate",
    "effective_interest_schedule",
]


def periodic_rate(annual_rate: Decimal | float | str, periods_per_year: int) -> Decimal:
    """Convert an annual nominal rate to a periodic rate.

    Uses simple division (nominal convention), which is what ASC 842 discount
    rate practice assumes for monthly lease payments, not effective compounding.
    """
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive")
    with localcontext() as ctx:
        ctx.prec = WORKING_PRECISION
        return D(annual_rate) / Decimal(periods_per_year)


def discount_factor(rate: Decimal | float | str, period: int) -> Decimal:
    """1 / (1 + r)^n, exact."""
    r = D(rate)
    if r <= -1:
        raise ValueError("discount rate must exceed -100%")
    with localcontext() as ctx:
        ctx.prec = WORKING_PRECISION
        return Decimal(1) / ((Decimal(1) + r) ** period)


def present_value(
    cashflows: Sequence[Money | Decimal | float | str],
    rate: Decimal | float | str,
    *,
    due: bool = False,
    currency: str = "USD",
) -> Money:
    """Discount a sequence of period cash flows to time zero.

    ``due=False`` treats the first cash flow as occurring at the end of period 1
    (ordinary annuity). ``due=True`` treats it as occurring immediately at time
    zero (annuity due), which is the normal convention for lease payments made
    at the beginning of each month.
    """
    r = D(rate)
    total = Decimal(0)
    with localcontext() as ctx:
        ctx.prec = WORKING_PRECISION
        for i, cf in enumerate(cashflows):
            amount = cf.amount if isinstance(cf, Money) else D(cf)
            period = i if due else i + 1
            total += amount * discount_factor(r, period)
    return Money(total, currency)


def pv_annuity(
    payment: Money | Decimal | float | str,
    rate: Decimal | float | str,
    periods: int,
    *,
    due: bool = False,
    currency: str = "USD",
) -> Money:
    """Present value of a level annuity, closed form."""
    if periods < 0:
        raise ValueError("periods must be non-negative")
    amt = payment.amount if isinstance(payment, Money) else D(payment)
    cur = payment.currency if isinstance(payment, Money) else currency
    r = D(rate)
    with localcontext() as ctx:
        ctx.prec = WORKING_PRECISION
        if r == 0:
            pv = amt * periods
        else:
            factor = (Decimal(1) - discount_factor(r, periods)) / r
            if due:
                factor *= (Decimal(1) + r)
            pv = amt * factor
    return Money(pv, cur)


def implicit_rate(
    principal: Money,
    payments: Sequence[Money],
    *,
    due: bool = False,
    tolerance: str = "0.0000000001",
    max_iterations: int = 200,
) -> Decimal:
    """Solve for the periodic rate that equates payments to a principal.

    Bisection rather than Newton: slower, but it cannot diverge or land on a
    spurious root, and lease schedules are small enough that the extra
    iterations are free. Determinism matters more than speed here -- the same
    inputs must always produce the same rate, or the workpaper fingerprint
    changes between runs.
    """
    if not payments:
        raise ValueError("no payments supplied")
    if principal.amount <= 0:
        raise ValueError("principal must be positive")

    tol = D(tolerance)
    lo, hi = Decimal("-0.9999"), Decimal("10")

    def pv_at(r: Decimal) -> Decimal:
        return present_value(payments, r, due=due, currency=principal.currency).amount

    if pv_at(lo) < principal.amount:
        raise ValueError("no rate in range reproduces the principal; check the payment stream")

    with localcontext() as ctx:
        ctx.prec = WORKING_PRECISION
        for _ in range(max_iterations):
            mid = (lo + hi) / 2
            diff = pv_at(mid) - principal.amount
            if abs(diff) <= tol:
                return mid
            if diff > 0:
                lo = mid  # PV too high, need a bigger discount rate
            else:
                hi = mid
        return (lo + hi) / 2


def effective_interest_schedule(
    opening_balance: Money,
    payments: Sequence[Money],
    rate: Decimal | float | str,
    *,
    due: bool = False,
) -> List[dict]:
    """Amortise a liability using the effective interest method.

    Returns one row per period with opening balance, interest accreted, payment,
    principal reduction, and closing balance. This single routine backs the
    ASC 842 lease liability roll-forward and the ASC 606 financing component,
    because they are the same computation with different labels.

    For an annuity due the payment lands at the *start* of the period, so it
    reduces the balance before interest accrues on it. Getting that ordering
    wrong is the single most common lease schedule defect.
    """
    r = D(rate)
    balance = opening_balance.amount
    cur = opening_balance.currency
    rows: List[dict] = []

    with localcontext() as ctx:
        ctx.prec = WORKING_PRECISION
        for i, pmt in enumerate(payments, start=1):
            payment = pmt.amount if isinstance(pmt, Money) else D(pmt)
            opening = balance

            if due:
                after_payment = opening - payment
                interest = after_payment * r
                closing = after_payment + interest
                principal = payment
            else:
                interest = opening * r
                closing = opening + interest - payment
                principal = payment - interest

            rows.append({
                "period": i,
                "opening": Money(opening, cur),
                "interest": Money(interest, cur),
                "payment": Money(payment, cur),
                "principal": Money(principal, cur),
                "closing": Money(closing, cur),
            })
            balance = closing

    return rows
