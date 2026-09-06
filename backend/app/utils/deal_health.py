"""The three Deal Health detectors.

PS section 4 B9 asks for stalled deals, discount anomalies, and delivery
slippage. Two are date arithmetic; the third is a z-score. None is a model, and
none of them touches approval routing.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.enums import FlagType
from app.models.quotation import Quotation
from app.utils.anomaly import (
    anomaly_util_baseline,
    anomaly_util_is_anomalous,
    anomaly_util_severity,
    anomaly_util_z_score,
)

# "quotations inactive for more than a configured number of days" - PS 4 B9.
STALL_DAYS = 7


def health_util_effective_discount(quotation: Quotation) -> Decimal:
    """Quotation-level discount, as a share of list value.

    One number per quotation, so a rep's history is comparable across quotes of
    different shapes: (list - net) / list * 100.
    """
    list_value = sum(
        (
            Decimal(str(line.unit_price)) * Decimal(str(line.qty))
            for line in quotation.lines
        ),
        Decimal("0"),
    )
    if not list_value:
        return Decimal("0")

    net_value = sum(
        (
            Decimal(str(line.unit_price))
            * Decimal(str(line.qty))
            * (Decimal("100") - Decimal(str(line.discount_pct)))
            / Decimal("100")
            for line in quotation.lines
        ),
        Decimal("0"),
    )
    return (list_value - net_value) / list_value * Decimal("100")


def health_util_days_idle(quotation: Quotation) -> int:
    last = quotation.last_activity_at
    if last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    return (datetime.now(UTC) - last).days


def health_util_stalled(quotation: Quotation) -> dict | None:
    """Idle for longer than the configured window."""
    days = health_util_days_idle(quotation)
    if days < STALL_DAYS:
        return None

    return {
        "type": FlagType.STALLED,
        "severity": "HIGH" if days >= STALL_DAYS * 2 else "MEDIUM",
        "issue": f"No activity in {days} days",
        "days_idle": days,
    }


def health_util_anomaly(
    quotation: Quotation, rep_history: list[Decimal]
) -> dict | None:
    """Unusually high discount for this rep specifically.

    A rep who consistently discounts at 22% has a mean of 22, so a fresh 22%
    quote is not anomalous - correctly. That rep is caught by the business-rule
    engine, which asks the different question of whether it is allowed.
    """
    discount = health_util_effective_discount(quotation)
    rep_mean, rep_std = anomaly_util_baseline(rep_history)
    z = anomaly_util_z_score(discount, rep_mean, rep_std)

    if not anomaly_util_is_anomalous(z):
        return None

    return {
        "type": FlagType.DISCOUNT_ANOMALY,
        "severity": anomaly_util_severity(z),
        "issue": f"Discount {discount:.0f}% vs avg {rep_mean:.0f}%",
        "z_score": z.quantize(Decimal("0.01")),
    }


def health_util_slippage(quotation: Quotation) -> dict | None:
    """Expected delivery later than what was promised."""
    promised: date | None = quotation.promised_delivery_date
    expected: date | None = quotation.expected_delivery_date

    if promised is None or expected is None or expected <= promised:
        return None

    days = (expected - promised).days
    return {
        "type": FlagType.DELIVERY_SLIPPAGE,
        "severity": "HIGH" if days > 5 else "MEDIUM",
        "issue": f"Delivery expected {days} days after the promised date",
        "days_slipped": days,
    }


def health_util_compute_flags(session) -> list[dict]:
    """Run every detector over every open quotation.

    Shared by the Deal Health board and the dashboard's at-risk count. Having
    the dashboard count stored rows instead would show zero until someone
    happened to open the board.
    """
    from app.database.deal_health import (
        db_list_open_quotations,
        db_rep_discount_history,
    )

    payloads = []
    for quotation in db_list_open_quotations(session):
        history = db_rep_discount_history(session, quotation.rep_id, quotation.id)
        for detector in (
            health_util_stalled(quotation),
            health_util_anomaly(quotation, history),
            health_util_slippage(quotation),
        ):
            if detector:
                payloads.append({"quotation_id": quotation.id, **detector})
    return payloads
