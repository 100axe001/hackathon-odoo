"""Discount anomaly detection.

Statistics, not machine learning, and deliberately so. PS section 4 B9 asks for
"a discount well above a rep's historical average", which is a z-score against
that rep's own baseline. The stall-prediction model was evaluated separately and
cut: at the data volume available it lost to a threshold rule.

This is advisory. It never influences approval routing - that stays with the
deterministic engine in blended.py.
"""

from decimal import Decimal
from statistics import mean, stdev

# A rep needs a real history before they get a personal baseline. Three points
# cannot estimate a spread: adding one quotation can swing a z-score from 9.9 to
# 2.3 for the same discount.
MIN_HISTORY = 5

# Floor on the spread, in percentage points. Without it a very consistent rep
# produces a near-zero denominator and an ordinary discount explodes into a
# double-digit z. A bare `or 1.0` does not cover this - it only catches exactly 0.
MIN_STD = Decimal("2.0")

PLATFORM_MEAN = Decimal("8.0")
PLATFORM_STD = Decimal("4.0")

MEDIUM_Z = Decimal("2.0")
HIGH_Z = Decimal("3.0")


def anomaly_util_baseline(history: list[Decimal]) -> tuple[Decimal, Decimal]:
    """Mean and spread of a rep's past effective quotation discounts.

    `history` holds one value per PAST quotation. The one being scored is
    excluded, otherwise it drags its own baseline toward itself and hides the
    anomaly.
    """
    if len(history) < MIN_HISTORY:
        return PLATFORM_MEAN, PLATFORM_STD

    values = [float(v) for v in history]

    # Sample standard deviation. The population form understates spread at small
    # n and inflates every z-score - about 22% at n=3.
    spread = Decimal(str(stdev(values)))
    return Decimal(str(mean(values))), max(spread, MIN_STD)


def anomaly_util_z_score(
    discount_pct: Decimal, rep_mean: Decimal, rep_std: Decimal
) -> Decimal:
    return (discount_pct - rep_mean) / rep_std


def anomaly_util_is_anomalous(z_score: Decimal) -> bool:
    """One-sided on purpose.

    A discount far BELOW a rep's average costs the company nothing, so abs()
    would be wrong here.
    """
    return z_score > MEDIUM_Z


def anomaly_util_severity(z_score: Decimal) -> str:
    if z_score > HIGH_Z:
        return "HIGH"
    if z_score > MEDIUM_Z:
        return "MEDIUM"
    return "LOW"
