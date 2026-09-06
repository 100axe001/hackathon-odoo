"""Fulfillment endpoints that hang off a quotation URL.

Separate module from fulfillment.py because these mount under /quotations while
stock and the queue mount under /fulfillment. The paths are fixed by
docs/architecture/api-contract.md, which the frontend was written against.
"""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.fulfillment import (
    db_list_allocations,
    db_replace_allocations,
    db_reserve_stock,
    db_stocked_product_ids,
    db_warehouse_stock,
)
from app.database.quotations import db_get_quotation
from app.logging.setup_logging import get_logger
from app.models.enums import FulfilStatus
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.fulfillment import (
    BackorderRow,
    ErrorResponse,
    OverrideRequest,
    SplitData,
    SplitResponse,
    SplitRow,
    WarehouseLeg,
)
from app.utils.approval import AuditAction, record_audit
from app.utils.fulfillment import (
    fulfillment_util_shipment_cost,
    fulfillment_util_split,
)

logger = get_logger(__name__)
router = APIRouter()


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False, error="Conflict", message=message
        ).model_dump(),
    )


def _not_found(what: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorResponse(
            success=False, error="Not Found", message=what
        ).model_dump(),
    )


def _parse_id(raw: str) -> int:
    try:
        return int(raw[1:] if raw.startswith("q") else raw)
    except ValueError as e:
        raise _not_found(f"No quotation {raw}") from e


def _plan_for(db: Session, quotation) -> tuple[list[dict], int, Decimal, int]:
    """Run the algorithm against live availability."""
    # Only physical goods create demand. A service or subscription line has no
    # stock row anywhere, and counting it would put a workshop on permanent
    # backorder that no restock could ever clear.
    shippable = db_stocked_product_ids(db)
    demand: dict[int, int] = {}
    for line in quotation.lines:
        if line.product_id not in shippable:
            continue
        demand[line.product_id] = demand.get(line.product_id, 0) + line.qty

    plan = fulfillment_util_split(demand, db_warehouse_stock(db))

    # Shipping cost sits on the first row for each warehouse, so summing the
    # column gives the order total rather than counting a box twice.
    charged: set[int] = set()
    rows = []
    weights = {w.warehouse_id: w.shipping_cost_weight for w in db_warehouse_stock(db)}

    for allocation in plan.allocations:
        cost = Decimal("0")
        if (
            allocation.warehouse_id is not None
            and allocation.warehouse_id not in charged
        ):
            cost = fulfillment_util_shipment_cost(weights[allocation.warehouse_id])
            charged.add(allocation.warehouse_id)
        rows.append(
            {
                "product_id": allocation.product_id,
                "warehouse_id": allocation.warehouse_id,
                "qty": allocation.qty,
                "shipping_cost": cost,
            }
        )

    return rows, plan.shipments, plan.total_cost, plan.backordered


def _to_split_data(db: Session, quotation) -> SplitData:
    allocations = db_list_allocations(db, quotation.id)
    warehouses = sorted(
        {a.warehouse_id for a in allocations if a.warehouse_id is not None}
    )
    total_cost = sum((Decimal(str(a.shipping_cost)) for a in allocations), Decimal("0"))
    backordered = sum(a.qty for a in allocations if a.warehouse_id is None)
    fulfilled = sum(a.qty for a in allocations if a.warehouse_id is not None)
    # Shippable units only, so the progress figure compares like with like:
    # counting a workshop as an unshipped unit would never reach 100%.
    shippable = db_stocked_product_ids(db)
    ordered = sum(line.qty for line in quotation.lines if line.product_id in shippable)

    committed = quotation.fulfillment_status in (
        FulfilStatus.SPLIT_ACCEPTED,
        FulfilStatus.OVERRIDDEN,
    )
    shipped = quotation.fulfillment_status == FulfilStatus.SHIPPED
    outstanding = _backorder_rows(db, allocations)

    return SplitData(
        id=f"q{quotation.id}",
        number=quotation.number,
        customer=quotation.customer.name,
        status=quotation.fulfillment_status,
        warehouses=[
            SplitRow(
                warehouse_id=a.warehouse_id,
                product_id=a.product_id,
                warehouse=(
                    a.warehouse.name if a.warehouse is not None else "Backorder"
                ),
                product=a.product.name,
                qty_fulfilled=a.qty,
                est_shipments=1 if a.shipping_cost else 0,
                cost=float(a.shipping_cost),
            )
            for a in allocations
        ],
        total_shipments=len(warehouses),
        total_cost=float(total_cost),
        backordered=backordered,
        complete=backordered == 0,
        legs=_legs(allocations),
        backorder=outstanding,
        ordered_units=ordered,
        fulfilled_units=fulfilled,
        # Consolidating only makes sense once the split is committed and stock
        # has actually appeared somewhere - otherwise it would re-run against
        # the same empty shelves and change nothing.
        can_consolidate=committed
        and backordered > 0
        and any(row.available_now > 0 for row in outstanding),
        can_ship=committed and backordered == 0,
        shipped_at=_shipped_on(allocations) if shipped else None,
        # An order of nothing but services has no parcel to send. Saying so
        # beats an empty table that reads as a failed lookup.
        nothing_to_ship=ordered == 0,
    )


def _shipped_on(allocations) -> str | None:
    """When the parcels went out. None when there were none to send."""
    stamps = [a.resolved_at for a in allocations if a.resolved_at]
    return max(stamps).strftime("%b %d, %Y") if stamps else None


def _legs(allocations) -> list[WarehouseLeg]:
    """Group the rows into parcels.

    A row is one product from one warehouse; a leg is everything that warehouse
    ships, which is what actually arrives at the customer as a box.
    """
    grouped: dict[int | None, list] = {}
    for a in allocations:
        grouped.setdefault(a.warehouse_id, []).append(a)

    legs = []
    for warehouse_id, rows in grouped.items():
        first = rows[0]
        legs.append(
            WarehouseLeg(
                warehouse_id=warehouse_id,
                warehouse=(
                    first.warehouse.name if first.warehouse is not None else "Backorder"
                ),
                region=(first.warehouse.region if first.warehouse is not None else ""),
                units=sum(r.qty for r in rows),
                product_lines=len(rows),
                cost=float(sum(Decimal(str(r.shipping_cost)) for r in rows)),
            )
        )
    # Real warehouses first, the backorder last: it is the exception, not a
    # shipping origin.
    return sorted(legs, key=lambda leg: (leg.warehouse_id is None, leg.warehouse))


def _backorder_rows(db: Session, allocations) -> list[BackorderRow]:
    """What is still outstanding, and which warehouses could cover it now."""
    stock = db_warehouse_stock(db)
    rows = []
    for a in allocations:
        if a.warehouse_id is not None:
            continue
        sources = [w.name for w in stock if w.available.get(a.product_id, 0) > 0]
        rows.append(
            BackorderRow(
                product_id=a.product_id,
                product=a.product.name,
                qty=a.qty,
                available_now=sum(w.available.get(a.product_id, 0) for w in stock),
                sources=sources,
            )
        )
    return rows


@router.get(
    "/{quotation_id}/fulfillment-split",
    response_model=SplitResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def suggest_split(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> SplitResponse:
    """The recommended split.

    Only a suggestion: nothing is reserved until it is accepted, or merely
    opening a quotation would take stock out of circulation.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    if quotation.fulfillment_status in (
        FulfilStatus.SPLIT_ACCEPTED,
        FulfilStatus.OVERRIDDEN,
        FulfilStatus.SHIPPED,
    ):
        # Already committed - show what was agreed, not a fresh suggestion.
        # SHIPPED belongs here too: without it, merely opening a shipped order
        # re-planned it, reset its status and released the stock it had used.
        return SplitResponse(
            success=True, message="Split retrieved", data=_to_split_data(db, quotation)
        )

    rows, shipments, cost, backordered = _plan_for(db, quotation)
    db_replace_allocations(db, quotation.id, rows)
    quotation.fulfillment_status = FulfilStatus.SPLIT_SUGGESTED
    db.commit()

    logger.info(
        "Suggested split for %s: %d shipments, %d backordered",
        quotation.number,
        shipments,
        backordered,
    )
    return SplitResponse(
        success=True, message="Split suggested", data=_to_split_data(db, quotation)
    )


@router.post(
    "/{quotation_id}/fulfillment/accept",
    response_model=SplitResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def accept_split(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> SplitResponse:
    """Commit the suggested split and reserve the stock it uses."""
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    for allocation in db_list_allocations(db, quotation.id):
        if allocation.warehouse_id is not None:
            db_reserve_stock(
                db, allocation.warehouse_id, allocation.product_id, allocation.qty
            )

    quotation.fulfillment_status = FulfilStatus.SPLIT_ACCEPTED
    db.commit()
    logger.info("%s accepted the split for %s", user.full_name, quotation.number)

    return SplitResponse(
        success=True, message="Split accepted", data=_to_split_data(db, quotation)
    )


@router.post(
    "/{quotation_id}/fulfillment/override",
    response_model=SplitResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def override_split(
    quotation_id: str,
    payload: OverrideRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> SplitResponse:
    """Replace the split with numbers a human chose."""
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    weights = {w.warehouse_id: w.shipping_cost_weight for w in db_warehouse_stock(db)}
    charged: set[int] = set()
    rows = []
    for line in payload.allocations:
        cost = Decimal("0")
        if line.warehouse_id not in charged:
            cost = fulfillment_util_shipment_cost(
                weights.get(line.warehouse_id, Decimal("1"))
            )
            charged.add(line.warehouse_id)
        rows.append(
            {
                "product_id": line.product_id,
                "warehouse_id": line.warehouse_id,
                "qty": line.qty,
                "shipping_cost": cost,
            }
        )

    db_replace_allocations(db, quotation.id, rows, is_override=True)
    for line in payload.allocations:
        db_reserve_stock(db, line.warehouse_id, line.product_id, line.qty)

    quotation.fulfillment_status = FulfilStatus.OVERRIDDEN
    db.commit()
    logger.info("%s overrode the split for %s", user.full_name, quotation.number)

    return SplitResponse(
        success=True, message="Manual split saved", data=_to_split_data(db, quotation)
    )


@router.post(
    "/{quotation_id}/fulfillment/consolidate",
    response_model=SplitResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 409, 500)},
)
def consolidate_backorder(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> SplitResponse:
    """Cover what is still outstanding, now that stock has arrived.

    PS section 4 B6: when stock arrives mid-fulfillment the remaining backorder
    should be consolidated rather than left. Only the outstanding rows are
    re-planned - what has already been reserved stays where it is, because
    moving a committed allocation would release stock a warehouse is holding.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    if quotation.fulfillment_status not in (
        FulfilStatus.SPLIT_ACCEPTED,
        FulfilStatus.OVERRIDDEN,
    ):
        raise _conflict("Accept a split before consolidating what it could not cover")

    allocations = db_list_allocations(db, quotation.id)
    outstanding = {a.product_id: a.qty for a in allocations if a.warehouse_id is None}
    if not outstanding:
        raise _conflict("Nothing is on backorder for this order")

    plan = fulfillment_util_split(outstanding, db_warehouse_stock(db))
    covered = [a for a in plan.allocations if a.warehouse_id is not None]
    if not covered:
        raise _conflict(
            "No warehouse can cover the backorder yet. Restock first, then consolidate."
        )

    # Keep every committed row, replace the backorder rows with the new plan.
    weights = {w.warehouse_id: w.shipping_cost_weight for w in db_warehouse_stock(db)}
    already_charged = {
        a.warehouse_id for a in allocations if a.warehouse_id and a.shipping_cost
    }
    rows = [
        {
            "product_id": a.product_id,
            "warehouse_id": a.warehouse_id,
            "qty": a.qty,
            "shipping_cost": Decimal(str(a.shipping_cost)),
        }
        for a in allocations
        if a.warehouse_id is not None
    ]

    for allocation in plan.allocations:
        cost = Decimal("0")
        if (
            allocation.warehouse_id is not None
            and allocation.warehouse_id not in already_charged
        ):
            # A warehouse already shipping this order adds no second parcel.
            cost = fulfillment_util_shipment_cost(
                weights.get(allocation.warehouse_id, Decimal("1"))
            )
            already_charged.add(allocation.warehouse_id)
        rows.append(
            {
                "product_id": allocation.product_id,
                "warehouse_id": allocation.warehouse_id,
                "qty": allocation.qty,
                "shipping_cost": cost,
            }
        )

    db_replace_allocations(db, quotation.id, rows)
    for allocation in covered:
        db_reserve_stock(
            db, allocation.warehouse_id, allocation.product_id, allocation.qty
        )
    db.commit()

    filled = sum(a.qty for a in covered)
    logger.info(
        "%s consolidated %d unit(s) on %s", user.full_name, filled, quotation.number
    )
    return SplitResponse(
        success=True,
        message=f"Consolidated {filled} unit(s) from newly arrived stock",
        data=_to_split_data(db, quotation),
    )


@router.post(
    "/{quotation_id}/fulfillment/ship",
    response_model=SplitResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 409, 500)},
)
def mark_shipped(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> SplitResponse:
    """Close fulfillment.

    Without this the order never left the queue: everything downstream keys off
    SHIPPED and nothing ever set it. Refused while anything is on backorder -
    you cannot ship what no warehouse is holding.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    if quotation.fulfillment_status not in (
        FulfilStatus.SPLIT_ACCEPTED,
        FulfilStatus.OVERRIDDEN,
    ):
        raise _conflict("Accept or override the split before shipping")

    allocations = db_list_allocations(db, quotation.id)
    outstanding = sum(a.qty for a in allocations if a.warehouse_id is None)
    if outstanding:
        raise _conflict(
            f"{outstanding} unit(s) are still on backorder. Consolidate them first."
        )

    shipped_at = datetime.now(UTC)
    for allocation in allocations:
        allocation.resolved_at = shipped_at

    quotation.fulfillment_status = FulfilStatus.SHIPPED
    record_audit(
        db,
        quotation=quotation,
        user_id=user.id,
        action=AuditAction.CONFIRM,
        note=f"Shipped in {len({a.warehouse_id for a in allocations})} parcel(s)",
    )
    db.commit()
    logger.info("%s shipped %s", user.full_name, quotation.number)

    return SplitResponse(
        success=True,
        message="Marked as shipped",
        data=_to_split_data(db, quotation),
    )
