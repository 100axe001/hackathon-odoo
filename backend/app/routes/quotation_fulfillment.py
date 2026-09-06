"""Fulfillment endpoints that hang off a quotation URL.

Separate module from fulfillment.py because these mount under /quotations while
stock and the queue mount under /fulfillment. The paths are fixed by
docs/architecture/api-contract.md, which the frontend was written against.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.fulfillment import (
    db_list_allocations,
    db_replace_allocations,
    db_reserve_stock,
    db_warehouse_stock,
)
from app.database.quotations import db_get_quotation
from app.logging.setup_logging import get_logger
from app.models.enums import FulfilStatus
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.fulfillment import (
    ErrorResponse,
    OverrideRequest,
    SplitData,
    SplitResponse,
    SplitRow,
)
from app.utils.fulfillment import (
    fulfillment_util_shipment_cost,
    fulfillment_util_split,
)

logger = get_logger(__name__)
router = APIRouter()


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
    demand: dict[int, int] = {}
    for line in quotation.lines:
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

    return SplitData(
        id=f"q{quotation.id}",
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
    )


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
    ):
        # Already committed - show what was agreed, not a fresh suggestion.
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
