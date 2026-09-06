"""Proration arithmetic.

Specification is docs/engineering/billing-proration.md. No HTTP, no database -
these pin the formula and its edges directly.
"""

from datetime import date
from decimal import Decimal

from app.utils.billing import (
    billing_util_cancellation_credit,
    billing_util_cycle_days,
    billing_util_invoice_status,
    billing_util_next_bill_date,
    billing_util_prorate,
)

SEPT = date(2026, 9, 15)  # a monthly period starting the 15th


def prorate(old, new, on, unit=Decimal("46"), cycle="Monthly", start=SEPT):
    return billing_util_prorate(
        unit_price=unit,
        old_qty=old,
        new_qty=new,
        cycle=cycle,
        period_start=start,
        on=on,
    )


class TestTheWorkedExample:
    def test_an_upgrade_halfway_through_charges_half(self) -> None:
        """$46/month, 1 seat to 3, on day 15 of 30."""
        result = prorate(1, 3, date(2026, 9, 30))

        assert result.price_delta == Decimal("92.00")
        assert (result.remaining_days, result.cycle_days) == (15, 30)
        assert result.amount == Decimal("46.00")

    def test_it_is_neither_nothing_nor_the_full_new_price(self) -> None:
        """Nothing gives two seats away free; $138 bills days they had one."""
        result = prorate(1, 3, date(2026, 9, 30))
        assert result.amount not in (Decimal("0"), Decimal("138.00"))


class TestDirection:
    def test_a_downgrade_produces_a_credit_from_the_same_formula(self) -> None:
        """A separate refund path is where the two drift apart."""
        result = prorate(3, 1, date(2026, 9, 30))

        assert result.amount == Decimal("-46.00")
        assert result.is_credit

    def test_no_change_costs_nothing(self) -> None:
        assert prorate(2, 2, date(2026, 9, 30)).amount == Decimal("0.00")


class TestEdgesOfThePeriod:
    def test_a_change_on_the_first_day_charges_the_whole_period(self) -> None:
        result = prorate(1, 2, SEPT)
        assert result.remaining_days == result.cycle_days
        assert result.amount == Decimal("46.00")

    def test_a_change_on_the_last_day_charges_almost_nothing(self) -> None:
        result = prorate(1, 2, date(2026, 10, 14))
        assert result.amount == Decimal("1.53")

    def test_a_date_past_the_period_end_never_goes_negative(self) -> None:
        """Otherwise an upgrade could bill a refund."""
        result = prorate(1, 5, date(2026, 12, 1))
        assert result.remaining_days == 0
        assert result.amount == Decimal("0.00")


class TestRealCalendarLengths:
    def test_february_is_not_thirty_days(self) -> None:
        assert billing_util_cycle_days("Monthly", date(2026, 2, 1)) == 28

    def test_a_plan_billed_on_the_31st_stays_on_month_ends(self) -> None:
        """relativedelta clamps rather than rolling into the next month."""
        assert billing_util_next_bill_date("Monthly", date(2026, 1, 31)) == date(
            2026, 2, 28
        )

    def test_each_cycle_has_its_own_length(self) -> None:
        """Quarterly from 15 Sept is 91 days: 15 + 31 + 30 + 15.

        The exact number depends on which months the period spans, which is the
        whole reason this is not a fixed 90.
        """
        assert billing_util_cycle_days("Weekly", SEPT) == 7
        assert billing_util_cycle_days("Quarterly", SEPT) == 91
        assert billing_util_cycle_days("Yearly", SEPT) == 365

    def test_the_same_quarter_length_differs_by_start_month(self) -> None:
        q1 = billing_util_cycle_days("Quarterly", date(2026, 1, 1))
        q2 = billing_util_cycle_days("Quarterly", date(2026, 4, 1))
        assert q1 != q2


class TestCancellation:
    def test_cancelling_mid_cycle_credits_the_unused_remainder(self) -> None:
        result = billing_util_cancellation_credit(
            current_charge=Decimal("46"),
            cycle="Monthly",
            period_start=SEPT,
            on=date(2026, 9, 30),
        )

        assert result.amount == Decimal("-23.00")
        assert result.is_credit

    def test_cancelling_at_the_end_credits_nothing(self) -> None:
        result = billing_util_cancellation_credit(
            current_charge=Decimal("46"),
            cycle="Monthly",
            period_start=SEPT,
            on=date(2026, 10, 15),
        )
        assert result.amount == Decimal("0.00")


class TestInvoiceStatus:
    def test_nothing_recorded_is_unpaid(self) -> None:
        assert billing_util_invoice_status(Decimal("100"), Decimal("0")) == "Unpaid"

    def test_part_of_the_total_is_partial(self) -> None:
        assert billing_util_invoice_status(Decimal("100"), Decimal("40")) == "Partial"

    def test_the_full_total_is_paid(self) -> None:
        assert billing_util_invoice_status(Decimal("100"), Decimal("100")) == "Paid"

    def test_an_overpayment_still_reads_as_paid(self) -> None:
        assert billing_util_invoice_status(Decimal("100"), Decimal("120")) == "Paid"
