"""Data access for the product catalogue. Every function is prefixed db_."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.catalog import PriceList, Product
from app.models.fulfillment import StockLevel, Warehouse
from app.models.identity import DiscountTier


def db_list_products(session: Session) -> list[Product]:
    return list(session.scalars(select(Product).order_by(Product.id)).all())


def db_get_product(session: Session, product_id: int) -> Product | None:
    return session.get(Product, product_id)


def db_update_product(
    session: Session,
    product: Product,
    *,
    name: str,
    category: str,
    unit_price: Decimal,
    cost_price: Decimal,
    unit: str,
    tax_pct: Decimal,
    description: str | None,
    is_subscription: bool,
    recurring_cycle: str | None,
) -> Product:
    """Apply the editable catalogue fields to an existing product.

    Only these nine move: qty_on_hand is stock and `variants` is display-only,
    so neither belongs to the configuration screen that posts here.
    """
    product.name = name
    product.category = category
    product.unit_price = unit_price
    product.cost_price = cost_price
    product.unit = unit
    product.tax_pct = tax_pct
    product.description = description
    product.is_subscription = is_subscription
    product.recurring_cycle = recurring_cycle
    session.flush()
    return product


def db_list_price_lists(session: Session) -> list[tuple[PriceList, DiscountTier]]:
    """Configured price rules with the tier each one applies to.

    Joined rather than lazy-loaded so the product screen renders one query,
    and ordered by tier so the rules read cheapest-ceiling first.
    """
    return list(
        session.execute(
            select(PriceList, DiscountTier)
            .join(DiscountTier, PriceList.tier_id == DiscountTier.id)
            .order_by(DiscountTier.id)
        ).all()
    )


def db_product_stock(session: Session, product_id: int) -> list[StockLevel]:
    """This product's stock at every warehouse, active ones first.

    Inactive warehouses are still listed rather than hidden: stock sitting in a
    depot the split logic skips is exactly the thing a buyer needs to see, and
    silently omitting it makes the totals look wrong.
    """
    return list(
        session.scalars(
            select(StockLevel)
            .join(Warehouse, Warehouse.id == StockLevel.warehouse_id)
            .where(StockLevel.product_id == product_id)
            .options(selectinload(StockLevel.warehouse))
            .order_by(Warehouse.active.desc(), Warehouse.name)
        ).all()
    )


def db_create_product(
    session: Session,
    *,
    name: str,
    category: str,
    unit_price: Decimal,
    cost_price: Decimal,
    unit: str,
    tax_pct: Decimal,
    description: str | None,
    is_subscription: bool,
    recurring_cycle: str | None,
) -> Product:
    """Add a product to the catalogue. Stock is added per warehouse afterwards."""
    product = Product(
        name=name,
        category=category,
        unit_price=unit_price,
        cost_price=cost_price,
        unit=unit,
        tax_pct=tax_pct,
        description=description,
        is_subscription=is_subscription,
        recurring_cycle=recurring_cycle,
    )
    session.add(product)
    session.flush()
    return product
