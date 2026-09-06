"""Data access for fulfillment. Every function is prefixed db_."""

from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import FulfilStatus, QuoteStatus
from app.models.fulfillment import FulfillmentAllocation, StockLevel, Warehouse
from app.models.quotation import Quotation, QuotationLine
from app.utils.fulfillment import WarehouseStock


def db_list_stock(session: Session) -> list[StockLevel]:
    return list(
        session.scalars(
            select(StockLevel)
            .options(
                selectinload(StockLevel.warehouse),
                selectinload(StockLevel.product),
            )
            .join(Warehouse)
            .order_by(Warehouse.name, StockLevel.product_id)
        ).all()
    )


def db_warehouse_stock(session: Session) -> list[WarehouseStock]:
    """Availability per active warehouse, in the shape the algorithm wants."""
    rows = session.scalars(
        select(StockLevel).join(Warehouse).where(Warehouse.active.is_(True))
    ).all()

    by_warehouse: dict[int, dict[int, int]] = {}
    for row in rows:
        by_warehouse.setdefault(row.warehouse_id, {})[row.product_id] = row.available

    warehouses = session.scalars(
        select(Warehouse).where(Warehouse.active.is_(True))
    ).all()

    return [
        WarehouseStock(
            warehouse_id=w.id,
            name=w.name,
            shipping_cost_weight=Decimal(str(w.shipping_cost_weight)),
            available=by_warehouse.get(w.id, {}),
        )
        for w in warehouses
    ]


def db_orders_awaiting_fulfillment(session: Session) -> list[Quotation]:
    """Approved or confirmed quotations that still need shipping."""
    return list(
        session.scalars(
            select(Quotation)
            .where(
                Quotation.status.in_([QuoteStatus.APPROVED, QuoteStatus.CONFIRMED]),
                Quotation.fulfillment_status != FulfilStatus.SHIPPED,
            )
            .options(
                selectinload(Quotation.customer),
                selectinload(Quotation.lines).selectinload(QuotationLine.product),
            )
            .order_by(Quotation.id)
        ).all()
    )


def db_list_allocations(
    session: Session, quotation_id: int
) -> list[FulfillmentAllocation]:
    return list(
        session.scalars(
            select(FulfillmentAllocation)
            .where(FulfillmentAllocation.quotation_id == quotation_id)
            .options(
                selectinload(FulfillmentAllocation.warehouse),
                selectinload(FulfillmentAllocation.product),
            )
            .order_by(FulfillmentAllocation.id)
        ).all()
    )


def db_replace_allocations(
    session: Session, quotation_id: int, rows: list[dict], *, is_override: bool = False
) -> list[FulfillmentAllocation]:
    """Store a plan, releasing anything the previous plan had reserved.

    Releasing first matters: overriding a split that already reserved stock
    would otherwise leak those units, and they would never come back.
    """
    for existing in db_list_allocations(session, quotation_id):
        if existing.warehouse_id is not None:
            db_release_stock(
                session, existing.warehouse_id, existing.product_id, existing.qty
            )
        session.delete(existing)
    session.flush()

    created = [
        FulfillmentAllocation(quotation_id=quotation_id, is_override=is_override, **row)
        for row in rows
    ]
    session.add_all(created)
    session.flush()
    return created


def db_get_stock_level(
    session: Session, warehouse_id: int, product_id: int
) -> StockLevel | None:
    return session.scalar(
        select(StockLevel).where(
            StockLevel.warehouse_id == warehouse_id,
            StockLevel.product_id == product_id,
        )
    )


def db_reserve_stock(
    session: Session, warehouse_id: int, product_id: int, qty: int
) -> None:
    level = db_get_stock_level(session, warehouse_id, product_id)
    if level is not None:
        level.qty_reserved += qty


def db_release_stock(
    session: Session, warehouse_id: int, product_id: int, qty: int
) -> None:
    level = db_get_stock_level(session, warehouse_id, product_id)
    if level is not None:
        level.qty_reserved = max(0, level.qty_reserved - qty)


def db_restock(session: Session, warehouse_id: int, product_id: int, qty: int) -> None:
    """Raise on-hand stock, opening the row if this warehouse has never held it.

    Without the create it silently did nothing for a product the warehouse had
    not carried before - which is exactly the case a restock is for, and it
    returned success while changing nothing.
    """
    level = db_get_stock_level(session, warehouse_id, product_id)
    if level is None:
        level = StockLevel(
            warehouse_id=warehouse_id, product_id=product_id, qty_on_hand=0
        )
        session.add(level)
    level.qty_on_hand += qty
    session.flush()


class ReservedBy(TypedDict):
    """One customer's claim on a warehouse/product row."""

    customer: str
    quotation: str
    qty: int


def db_reservations_by_row(
    session: Session,
) -> dict[tuple[int, int], list[ReservedBy]]:
    """Who the reserved units on each warehouse/product row belong to.

    The reserved figure on its own says stock is spoken for but not by whom,
    which is the question anyone looking at a fulfillment queue actually has.
    Keyed by (warehouse_id, product_id) so the caller can attach it per row.
    """
    # Joined explicitly: the allocation carries quotation_id but no relationship,
    # and adding one only for this read would widen the model for nothing.
    rows = session.execute(
        select(FulfillmentAllocation, Quotation)
        .join(Quotation, Quotation.id == FulfillmentAllocation.quotation_id)
        .where(FulfillmentAllocation.warehouse_id.is_not(None))
        .options(selectinload(Quotation.customer))
    ).all()

    claims: dict[tuple[int, int], dict[str, ReservedBy]] = {}
    for row, quotation in rows:
        key = (row.warehouse_id, row.product_id)
        # One line per quotation: an order with two lines of the same product
        # from the same warehouse is still one claim.
        by_quote = claims.setdefault(key, {})
        existing = by_quote.get(quotation.number)
        if existing:
            existing["qty"] += row.qty
        else:
            by_quote[quotation.number] = ReservedBy(
                customer=quotation.customer.name,
                quotation=quotation.number,
                qty=row.qty,
            )

    return {
        key: sorted(v.values(), key=lambda c: -c["qty"]) for key, v in claims.items()
    }


def db_stocked_product_ids(session: Session) -> set[int]:
    """Products that are held as inventory somewhere.

    A workshop or a cloud subscription is delivered, not shipped, so it has no
    stock row anywhere and must not create warehouse demand. Deriving that from
    the data rather than from a category name means it stays right when someone
    renames a category.
    """
    return set(session.scalars(select(StockLevel.product_id).distinct()).all())
