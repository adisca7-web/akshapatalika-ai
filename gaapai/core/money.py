"""Exact monetary arithmetic.

Accounting answers must be reproducible to the cent. Binary floating point is
not: ``0.1 + 0.2 != 0.3``, and a trial balance summed in float will drift out of
balance on a few hundred thousand rows. Every amount in this system is a
:class:`Money` backed by :class:`decimal.Decimal`.

Rounding follows ASC 105 materiality convention in practice: half-up at the
presentation scale, applied once at presentation time rather than at each
intermediate step. Intermediate values keep full precision so that a schedule
that amortises over 360 periods does not accumulate 360 rounding errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN, localcontext
from typing import Iterable, Union

__all__ = ["Money", "D", "money", "ZERO", "quantize", "allocate"]

Numeric = Union["Money", Decimal, int, str, float]

# Working precision. Wide enough that 40-year monthly schedules do not lose
# cents, narrow enough to stay fast.
WORKING_PRECISION = 34


def D(value: Numeric) -> Decimal:
    """Coerce to Decimal without going through binary float where avoidable.

    Floats are accepted but routed through ``repr`` so that ``0.1`` becomes
    ``Decimal("0.1")`` rather than the exact binary expansion. Callers should
    still prefer strings or ints for literals.
    """
    if isinstance(value, Money):
        return value.amount
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(repr(value))
    return Decimal(str(value).replace(",", "").strip())


@dataclass(frozen=True, order=False)
class Money:
    """An exact monetary amount in a single currency.

    Immutable and hashable. Arithmetic between different currencies raises
    rather than silently converting, because an implicit FX assumption is the
    kind of thing that quietly misstates a consolidated statement.
    """

    amount: Decimal
    currency: str = "USD"

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", D(self.amount))
        object.__setattr__(self, "currency", self.currency.upper())

    # -- construction ---------------------------------------------------

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        return cls(Decimal(0), currency)

    @classmethod
    def of(cls, value: Numeric, currency: str = "USD") -> "Money":
        if isinstance(value, Money):
            if value.currency != currency.upper():
                raise ValueError(
                    f"cannot reinterpret {value.currency} amount as {currency}"
                )
            return value
        return cls(D(value), currency)

    # -- guards ---------------------------------------------------------

    def _compat(self, other: Numeric) -> Decimal:
        if isinstance(other, Money):
            if other.currency != self.currency:
                raise ValueError(
                    f"currency mismatch: {self.currency} vs {other.currency}; "
                    "translate through ASC 830 before combining"
                )
            return other.amount
        return D(other)

    # -- arithmetic -----------------------------------------------------

    def __add__(self, other: Numeric) -> "Money":
        with localcontext() as ctx:
            ctx.prec = WORKING_PRECISION
            return Money(self.amount + self._compat(other), self.currency)

    __radd__ = __add__

    def __sub__(self, other: Numeric) -> "Money":
        with localcontext() as ctx:
            ctx.prec = WORKING_PRECISION
            return Money(self.amount - self._compat(other), self.currency)

    def __rsub__(self, other: Numeric) -> "Money":
        with localcontext() as ctx:
            ctx.prec = WORKING_PRECISION
            return Money(self._compat(other) - self.amount, self.currency)

    def __mul__(self, factor: Numeric) -> "Money":
        if isinstance(factor, Money):
            raise TypeError("money * money is not a meaningful quantity")
        with localcontext() as ctx:
            ctx.prec = WORKING_PRECISION
            return Money(self.amount * D(factor), self.currency)

    __rmul__ = __mul__

    def __truediv__(self, divisor: Numeric):
        """Money / Money yields a dimensionless ratio; Money / scalar yields Money."""
        with localcontext() as ctx:
            ctx.prec = WORKING_PRECISION
            if isinstance(divisor, Money):
                if divisor.currency != self.currency:
                    raise ValueError("currency mismatch in ratio")
                if divisor.amount == 0:
                    raise ZeroDivisionError("ratio denominator is zero")
                return self.amount / divisor.amount
            d = D(divisor)
            if d == 0:
                raise ZeroDivisionError("division of money by zero")
            return Money(self.amount / d, self.currency)

    def __neg__(self) -> "Money":
        return Money(-self.amount, self.currency)

    def __abs__(self) -> "Money":
        return Money(abs(self.amount), self.currency)

    # -- comparison -----------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Money):
            return self.currency == other.currency and self.amount == other.amount
        if isinstance(other, (int, Decimal, str, float)):
            return self.amount == D(other)
        return NotImplemented

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def __lt__(self, other: Numeric) -> bool:
        return self.amount < self._compat(other)

    def __le__(self, other: Numeric) -> bool:
        return self.amount <= self._compat(other)

    def __gt__(self, other: Numeric) -> bool:
        return self.amount > self._compat(other)

    def __ge__(self, other: Numeric) -> bool:
        return self.amount >= self._compat(other)

    def __bool__(self) -> bool:
        return self.amount != 0

    # -- presentation ---------------------------------------------------

    def round(self, places: int = 2, mode: str = ROUND_HALF_UP) -> "Money":
        """Quantize to ``places`` decimals. Applied at presentation, not per step."""
        return Money(quantize(self.amount, places, mode), self.currency)

    def is_zero(self, tolerance: Numeric = "0.005") -> bool:
        return abs(self.amount) <= abs(D(tolerance))

    def __str__(self) -> str:
        q = quantize(self.amount, 2)
        sign = "-" if q < 0 else ""
        return f"{sign}{self.currency} {abs(q):,.2f}"

    def __repr__(self) -> str:
        return f"Money('{self.amount}', '{self.currency}')"

    def __format__(self, spec: str) -> str:
        if not spec:
            return str(self)
        return format(quantize(self.amount, 2), spec)


def quantize(value: Numeric, places: int = 2, mode: str = ROUND_HALF_UP) -> Decimal:
    """Round a Decimal to a fixed number of decimal places."""
    exp = Decimal(1).scaleb(-places)
    return D(value).quantize(exp, rounding=mode)


def money(value: Numeric, currency: str = "USD") -> Money:
    """Shorthand constructor."""
    return Money.of(value, currency)


ZERO = Money.zero()


def allocate(total: Money, weights: Iterable[Numeric], places: int = 2) -> list[Money]:
    """Split ``total`` across ``weights`` so the parts sum back to the total exactly.

    Proportional allocation then rounding leaves a residual of a cent or two.
    ASC 606-10-32-31 requires the transaction price to be allocated *entirely*
    across performance obligations, so the residual cannot simply be dropped.
    This uses largest-remainder: round every share down, then hand the leftover
    cents out to the shares with the largest truncated remainder. Deterministic
    and the parts always tie to the whole.
    """
    ws = [D(w) for w in weights]
    if not ws:
        raise ValueError("cannot allocate across an empty set of weights")
    if any(w < 0 for w in ws):
        raise ValueError("allocation weights must be non-negative")
    denom = sum(ws)
    if denom == 0:
        raise ValueError("allocation weights sum to zero")

    with localcontext() as ctx:
        ctx.prec = WORKING_PRECISION
        exact = [total.amount * w / denom for w in ws]

    floors = [e.quantize(Decimal(1).scaleb(-places), rounding="ROUND_DOWN") for e in exact]
    residual = quantize(total.amount, places) - sum(floors)
    step = Decimal(1).scaleb(-places)

    # Hand out the residual one unit at a time, largest fractional part first.
    # Ties break on index so the result is stable across runs.
    order = sorted(
        range(len(ws)),
        key=lambda i: (-(exact[i] - floors[i]), i),
    )
    units = int((abs(residual) / step).to_integral_value())
    direction = step if residual > 0 else -step
    for k in range(units):
        floors[order[k % len(order)]] += direction

    return [Money(f, total.currency) for f in floors]
