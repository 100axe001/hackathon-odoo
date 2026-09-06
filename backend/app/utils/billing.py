"""Proration and invoice status.

Specified in docs/engineering/billing-proration.md. No FastAPI imports.
"""

from dataclasses import dataclass, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta

from app.models.enums import BillingCycle, InvoiceStatus

_CYCLE_STEP = {
    BillingCycle.WEEKLY: relativedelta(weeks=1),
    BillingCycle.MONTHLY: relativedelta(months=1),
    BillingCycle.QUARTERLY: relativedelta(months=3),
    BillingCycle.YEARLY: relativedelta(years=1),
}


_ZERO = Decimal("0")


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Proration:
    amount: Decimal
    remaining_days: int
    cycle_days: int
    price_delta: Decimal

    # Set only when a policy changed the amount, so the route can say why the
    # figure is not simply the unused remainder.
    note: str | None = None

    @property
    def is_credit(self) -> bool:
        return self.amount < 0


def billing_util_cycle_bounds(cycle: str, period_start: date) -> tuple[date, date]:
    """Start and end of the period that begins on `period_start`.

    Uses relativedelta rather than a fixed day count, so a plan billed on the
    31st does not silently move to the 1st and February is 28 days, not 30.
    """
    step = _CYCLE_STEP.get(cycle, relativedelta(months=1))
    return period_start, period_start + step


def billing_util_cycle_days(cycle: str, period_start: date) -> int:
    start, end = billing_util_cycle_bounds(cycle, period_start)
    return (end - start).days


def billing_util_prorate(
    *,
    unit_price: Decimal,
    old_qty: int,
    new_qty: int,
    cycle: str,
    period_start: date,
    on: date,
) -> Proration:
    """Charge or credit for a mid-cycle quantity change.

    price_delta is the change in the periodic charge, not the new total. A
    downgrade produces a negative delta and therefore a negative amount, which
    is a credit note - one expression covers both directions, and a separate
    refund path is where the two drift apart.
    """
    start, end = billing_util_cycle_bounds(cycle, period_start)
    cycle_days = (end - start).days

    # Clamp: a change dated outside the period is charged for the whole of it
    # rather than producing a nonsensical negative remainder.
    remaining = max(0, min(cycle_days, (end - on).days))

    price_delta = (Decimal(new_qty) - Decimal(old_qty)) * Decimal(str(unit_price))
    amount = price_delta * Decimal(remaining) / Decimal(cycle_days)

    return Proration(
        amount=_q2(amount),
        remaining_days=remaining,
        cycle_days=cycle_days,
        price_delta=_q2(price_delta),
    )


def billing_util_cancellation_credit(
    *,
    current_charge: Decimal,
    cycle: str,
    period_start: date,
    on: date,
    started_at: date | None = None,
    refund_window_days: int = 365,
    cancellation_fee_pct: Decimal = _ZERO,
) -> Proration:
    """Credit for the unused remainder of a period already paid for.

    The policy comes from the plan (PS 4-A5), not from here. Past the refund
    window there is no credit at all; inside it, the fee is withheld from what
    would otherwise be refunded. Both default to the permissive case, so a plan
    that configures neither behaves exactly as it did before.
    """
    result = billing_util_prorate(
        unit_price=current_charge,
        old_qty=1,
        new_qty=0,
        cycle=cycle,
        period_start=period_start,
        on=on,
    )

    if started_at is not None and (on - started_at).days > refund_window_days:
        return replace(
            result,
            amount=_ZERO,
            note=(
                f"Cancelled {(on - started_at).days} days after starting, past the "
                f"{refund_window_days}-day refund window, so no credit is due."
            ),
        )

    fee_pct = Decimal(str(cancellation_fee_pct))
    if fee_pct <= _ZERO or result.amount == _ZERO:
        return result

    # amount is negative here - it is a credit - so the fee shrinks it toward
    # zero rather than growing the refund.
    withheld = (result.amount * fee_pct / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return replace(
        result,
        amount=_q2(result.amount - withheld),
        note=(
            f"A {fee_pct.normalize():f}% cancellation fee of ${abs(withheld)} "
            "is withheld from the credit."
        ),
    )


def billing_util_next_bill_date(cycle: str, from_date: date) -> date:
    return from_date + _CYCLE_STEP.get(cycle, relativedelta(months=1))


def billing_util_invoice_status(amount: Decimal, paid: Decimal) -> str:
    """Stored rather than derived, so a report can group on it directly."""
    amount, paid = Decimal(str(amount)), Decimal(str(paid))
    if paid <= 0:
        return InvoiceStatus.UNPAID
    if paid >= amount:
        return InvoiceStatus.PAID
    return InvoiceStatus.PARTIAL
