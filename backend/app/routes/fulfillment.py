"""Fulfillment: live stock, the suggested split, and committing it."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.fulfillment import (
    db_list_allocations,
    db_list_stock,
    db_orders_awaiting_fulfillment,
    db_reservations_by_row,
    db_restock,
)
from app.logging.setup_logging import get_logger
from app.models.enums import FulfilStatus
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.fulfillment import (
    ErrorResponse,
    ListOrdersResponse,
    ListStockResponse,
    OrderRow,
    ReservedByRow,
    RestockRequest,
    StockRow,
)

logger = get_logger(__name__)
router = APIRouter()

# NONE.title() reads as "None", which looks like missing data rather than
# "nobody has split this yet".
_STATUS_LABEL = {
    FulfilStatus.NONE: "Awaiting split",
    FulfilStatus.SPLIT_SUGGESTED: "Split pending",
    FulfilStatus.SPLIT_ACCEPTED: "Split accepted",
    FulfilStatus.OVERRIDDEN: "Manual split",
    FulfilStatus.SHIPPED: "Shipped",
}


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


@router.get(
    "/stock",
    response_model=ListStockResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_stock(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListStockResponse:
    """Live stock per warehouse. Available is computed, never stored."""
    claims = db_reservations_by_row(db)
    rows = []
    for level in db_list_stock(db):
        try:
            rows.append(
                StockRow(
                    warehouse=level.warehouse.name,
                    product=level.product.name,
                    in_stock=level.qty_on_hand,
                    reserved=level.qty_reserved,
                    available=level.available,
                    reorder_point=level.reorder_point,
                    reorder_qty=level.reorder_qty,
                    # Measured against what is actually sellable, not what is on
                    # the shelf: stock already reserved cannot cover a new order.
                    needs_restock=level.reorder_point > 0
                    and level.available <= level.reorder_point,
                    reserved_for=[
                        ReservedByRow(**claim)
                        for claim in claims.get(
                            (level.warehouse_id, level.product_id), []
                        )
                    ],
                )
            )
        except (TypeError, ValueError, AttributeError) as e:
            logger.warning("Skipping stock row %s: %s", level.id, e)

    return ListStockResponse(
        success=True,
        message=f"Successfully retrieved {len(rows)} stock rows",
        data=rows,
    )


@router.get(
    "/orders",
    response_model=ListOrdersResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_orders(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListOrdersResponse:
    """Approved and confirmed quotations still waiting to ship."""
    rows = []
    for quotation in db_orders_awaiting_fulfillment(db):
        allocations = db_list_allocations(db, quotation.id)
        names = sorted(
            {a.warehouse.name for a in allocations if a.warehouse is not None}
        )
        has_backorder = any(a.warehouse_id is None for a in allocations)

        rows.append(
            OrderRow(
                id=f"q{quotation.id}",
                order=quotation.number,
                customer=quotation.customer.name,
                status=(
                    "Backorder"
                    if has_backorder
                    else _STATUS_LABEL.get(
                        quotation.fulfillment_status, quotation.fulfillment_status
                    )
                ),
                warehouses=" + ".join(names) if names else "Not yet split",
            )
        )

    return ListOrdersResponse(
        success=True, message=f"Successfully retrieved {len(rows)} orders", data=rows
    )


@router.post(
    "/restock",
    response_model=ListStockResponse,
    responses={500: {"model": ErrorResponse}},
)
def restock(
    payload: RestockRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> ListStockResponse:
    """Raise stock at a warehouse.

    Backs the Simulate Restock affordance: B6 wants the consolidation prompt to
    appear when stock arrives, and a demo cannot wait for a real delivery.
    """
    db_restock(db, payload.warehouse_id, payload.product_id, payload.qty)
    db.commit()
    return list_stock(db, user)
