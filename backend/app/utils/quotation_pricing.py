"""Scoring a stored quotation: resolve ceilings, then run the risk engine."""

from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.quotations import (
    db_get_category_ceiling,
    db_get_risk_thresholds,
)
from app.models.quotation import Quotation
from app.utils.blended import RiskResult, blended_util_score_quotation
from app.utils.discount import discount_util_excess_pt, discount_util_resolve_limit


def pricing_util_allowed_pct(
    session: Session, quotation: Quotation, category: str
) -> Decimal:
    """The ceiling for a line: the stricter of the customer tier and category."""
    tier_limit = Decimal(str(quotation.customer.tier.max_discount_pct))
    category_limit = db_get_category_ceiling(session, category)

    if category_limit is None:
        # An unconfigured category falls back to the tier ceiling rather than to
        # unlimited - an unknown category must not become a way to bypass policy.
        return tier_limit

    return discount_util_resolve_limit(tier_limit, category_limit)


def pricing_util_score(session: Session, quotation: Quotation) -> RiskResult:
    """Re-resolve every ceiling and re-score. Called on edit and on submit."""
    payload = []

    for line in quotation.lines:
        allowed = pricing_util_allowed_pct(session, quotation, line.product.category)
        discount = Decimal(str(line.discount_pct))

        # Freeze what was in force, so the audit trail stays truthful even if
        # configuration changes afterwards.
        line.allowed_discount_pct = allowed
        line.excess_pt = discount_util_excess_pt(discount, allowed)

        payload.append(
            {
                "product": line.product.name,
                "qty": line.qty,
                "unit_price": Decimal(str(line.unit_price)),
                "discount_pct": discount,
                "allowed_pct": allowed,
            }
        )

    result = blended_util_score_quotation(
        payload, thresholds=db_get_risk_thresholds(session)
    )

    quotation.risk_level = result.risk_level
    quotation.decided_by = result.decided_by
    quotation.worst_line_excess_pt = result.worst_line_excess_pt
    quotation.blended_excess_pt = result.blended_excess_pt
    quotation.blended_score = result.blended_score
    quotation.violating_line_count = result.violating_line_count
    quotation.total_excess_value = result.total_excess_value

    quotation.total_list_value = sum(
        (line.list_value for line in result.lines), Decimal("0")
    )
    quotation.total_net_value = sum(
        (
            Decimal(str(line.unit_price))
            * Decimal(str(line.qty))
            * (Decimal("100") - Decimal(str(line.discount_pct)))
            / Decimal("100")
            for line in quotation.lines
        ),
        Decimal("0"),
    )

    return result


def pricing_util_explain(result: RiskResult) -> str:
    """Plain-language reason, generated from the calculation.

    PS section 5 is explicit that this must not be hardcoded. It also has to
    work when there is no single culprit line, which is why decided_by exists.
    """
    if result.risk_level == "LOW":
        return "Every line is within its configured limit, so no approval is required."

    if result.decided_by == "BLENDED":
        return (
            f"{result.violating_line_count} lines exceed their configured limits. "
            f"No single line is severe, but the combined pattern puts the order "
            f"{result.blended_excess_pt}pt over policy overall, which produced a "
            f"{result.risk_level} blended risk."
        )

    worst = result.worst_line or "A line"
    base = (
        f"{worst} is {result.worst_line_excess_pt}pt over its own limit, "
        f"which triggered this review."
    )
    if result.violating_line_count > 1:
        base += (
            f" {result.violating_line_count} lines exceed their limits in total, "
            f"putting the order {result.blended_excess_pt}pt over policy."
        )
    return base
