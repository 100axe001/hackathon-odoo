"""Per-line discount ceilings. No FastAPI imports."""

from decimal import Decimal


def discount_util_resolve_limit(
    tier_limit_pct: Decimal, category_limit_pct: Decimal
) -> Decimal:
    """The ceiling a line is actually held to.

    The stricter of the two wins. PS section 10: a Gold customer may be allowed
    15 percent overall, but a Services line capped at 10 percent still breaks
    its own limit at 18 - and that one line flags the whole quotation.
    """
    return min(tier_limit_pct, category_limit_pct)


def discount_util_excess_pt(discount_pct: Decimal, allowed_pct: Decimal) -> Decimal:
    """Percentage points over the ceiling, never negative.

    A line discounted below its ceiling contributes nothing; it does not offset
    a line that is over.
    """
    return max(Decimal("0"), discount_pct - allowed_pct)
