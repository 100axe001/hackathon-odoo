"""Live margin on a quotation - PS section 4 B3."""

from decimal import ROUND_HALF_UP, Decimal


def margin_util_line_margin(
    unit_price: Decimal, cost_price: Decimal, qty: int, discount_pct: Decimal
) -> Decimal:
    """Margin on one line after its discount.

    Cost does not move with the discount, so discounting eats margin directly -
    which is the whole reason the ceilings exist.
    """
    net = (
        Decimal(str(unit_price))
        * Decimal(str(qty))
        * (Decimal("100") - Decimal(str(discount_pct)))
        / Decimal("100")
    )
    return net - Decimal(str(cost_price)) * Decimal(str(qty))


def margin_util_quotation(lines) -> tuple[Decimal, Decimal]:
    """Total margin and margin percentage for a quotation."""
    margin = sum(
        (
            margin_util_line_margin(
                line.unit_price, line.cost_price, line.qty, line.discount_pct
            )
            for line in lines
        ),
        Decimal("0"),
    )
    net = sum(
        (
            Decimal(str(line.unit_price))
            * Decimal(str(line.qty))
            * (Decimal("100") - Decimal(str(line.discount_pct)))
            / Decimal("100")
            for line in lines
        ),
        Decimal("0"),
    )
    pct = (margin / net * Decimal("100")) if net else Decimal("0")
    return (
        margin.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    )
