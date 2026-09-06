"""Upsell and cross-sell suggestions.

PS section 4 B5 wants a ranked list with the margin delta and any promotion tag.
Ranking comes from seeded co-purchase pairs rather than a trained model - see
the note on ProductPairing.
"""

from decimal import Decimal

from app.models.catalog import Product


def upsell_util_margin_delta(product: Product, qty: int = 1) -> Decimal:
    """Margin the quotation gains if this line is added.

    Requires cost_price. It was missing from every earlier draft of the data
    model, which made the live margin indicator in B3 unimplementable.
    """
    return (
        Decimal(str(product.unit_price)) - Decimal(str(product.cost_price))
    ) * Decimal(str(qty))


def upsell_util_promo_tag(product: Product) -> str | None:
    return "Promoted" if product.is_promoted else None


def upsell_util_margin_pct(product: Product) -> Decimal:
    """Margin as a percentage of list price, at no discount.

    The floor is expressed as a percentage so it stays meaningful across a
    $40 cable and a $1,200 laptop; an absolute figure would not.
    """
    price = Decimal(str(product.unit_price))
    if price <= 0:
        return Decimal("0")
    cost = Decimal(str(product.cost_price))
    return (price - cost) / price * Decimal("100")


def upsell_util_clears_floor(product: Product, min_margin_pct: Decimal) -> bool:
    """PS 4-A6: only healthy-margin products should ever surface."""
    return upsell_util_margin_pct(product) >= min_margin_pct
