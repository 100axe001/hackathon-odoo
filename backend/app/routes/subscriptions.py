"""Subscriptions and hybrid billing.

PS section 4 B7: one-time and recurring lines are shown separately within the
same order, with a forward billing schedule and prorated mid-cycle changes.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.billing import (
    db_add_schedule,
    db_create_invoice,
    db_get_subscription,
    db_list_subscriptions,
)
from app.logging.setup_logging import get_logger
from app.models.enums import DocType, LineType, SubStatus
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.billing import (
    BillingDetailData,
    BillingDetailResponse,
    BillingLine,
    CancelData,
    CancelResponse,
    ErrorResponse,
    ListSubscriptionsResponse,
    ModifyRequest,
    ModifyResponse,
    ProrationData,
    RecurringLine,
    ScheduleRow,
    SubscriptionRow,
)
from app.utils.billing import (
    billing_util_cancellation_credit,
    billing_util_prorate,
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


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False, error="Conflict", message=message
        ).model_dump(),
    )


def _parse_id(raw: str) -> int:
    try:
        return int(raw[1:] if raw.startswith("s") else raw)
    except ValueError as e:
        raise _not_found(f"No subscription {raw}") from e


def _load(db: Session, subscription_id: str):
    sub = db_get_subscription(db, _parse_id(subscription_id))
    if sub is None:
        raise _not_found(f"No subscription {subscription_id}")
    return sub


def _period_start(sub) -> date:
    """The period the current charge covers ends on next_bill_date."""
    step_back = {
        "Weekly": 7,
        "Monthly": 30,
        "Quarterly": 91,
        "Yearly": 365,
    }.get(sub.plan.cycle, 30)
    from datetime import timedelta

    return sub.next_bill_date - timedelta(days=step_back)


@router.get(
    "",
    response_model=ListSubscriptionsResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_subscriptions(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListSubscriptionsResponse:
    rows = []
    for sub in db_list_subscriptions(db):
        try:
            rows.append(
                SubscriptionRow(
                    id=f"s{sub.id}",
                    customer=sub.customer.name,
                    plan=sub.plan.name,
                    cycle=sub.plan.cycle,
                    next_bill=sub.next_bill_date.strftime("%b %d, %Y"),
                    status=sub.status,
                )
            )
        except (TypeError, ValueError, AttributeError) as e:
            logger.warning("Skipping subscription %s: %s", sub.id, e)

    return ListSubscriptionsResponse(
        success=True,
        message=f"Successfully retrieved {len(rows)} subscriptions",
        data=rows,
    )


@router.get(
    "/{subscription_id}/billing-detail",
    response_model=BillingDetailResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def billing_detail(
    subscription_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> BillingDetailResponse:
    """One-time and recurring lines, separately, plus what is coming."""
    sub = _load(db, subscription_id)

    # One-time lines come from the order the subscription originated on. They
    # are billed once; the plan below recurs. Mixing them on one document is
    # what B7 is guarding against.
    one_time = [
        BillingLine(
            product=line.product.name,
            qty=line.qty,
            amount=float(
                Decimal(str(line.unit_price))
                * Decimal(str(line.qty))
                * (Decimal("100") - Decimal(str(line.discount_pct)))
                / Decimal("100")
            ),
        )
        for line in sub.quotation.lines
        if line.line_type == LineType.ONE_TIME
    ]

    return BillingDetailResponse(
        success=True,
        message="Billing detail retrieved",
        data=BillingDetailData(
            id=f"s{sub.id}",
            customer=sub.customer.name,
            status=sub.status,
            one_time_lines=one_time,
            recurring_lines=[
                RecurringLine(
                    plan=sub.plan.name,
                    cycle=sub.plan.cycle,
                    next_bill=sub.next_bill_date.strftime("%b %d, %Y"),
                    amount=float(Decimal(str(sub.unit_price)) * Decimal(sub.qty)),
                    qty=sub.qty,
                )
            ],
            schedule=[
                ScheduleRow(
                    due_date=row.due_date.strftime("%b %d, %Y"),
                    amount=float(row.amount),
                    is_prorated=row.is_prorated,
                    note=row.note,
                )
                for row in sorted(sub.schedules, key=lambda r: r.due_date)
            ],
        ),
    )


@router.post(
    "/{subscription_id}/modify",
    response_model=ModifyResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 409, 500)},
)
def modify(
    subscription_id: str,
    payload: ModifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> ModifyResponse:
    """Change quantity mid-cycle, prorated for the remaining days."""
    sub = _load(db, subscription_id)
    if sub.status == SubStatus.CANCELLED:
        raise _conflict("This subscription is cancelled")

    result = billing_util_prorate(
        unit_price=Decimal(str(sub.unit_price)),
        old_qty=sub.qty,
        new_qty=payload.qty,
        cycle=sub.plan.cycle,
        period_start=_period_start(sub),
        on=date.today(),
    )

    old_qty = sub.qty
    sub.qty = payload.qty

    if result.amount != 0:
        db_add_schedule(
            db,
            subscription_id=sub.id,
            due_date=date.today(),
            amount=result.amount,
            is_prorated=True,
            note=(
                f"Quantity {old_qty} to {payload.qty}, "
                f"{result.remaining_days} of {result.cycle_days} days remaining"
            ),
        )

    # A negative adjustment is money owed back, so it is a credit note rather
    # than a charge - same formula, opposite sign.
    if result.is_credit:
        db_create_invoice(
            db,
            quotation_id=sub.quotation_id,
            customer_id=sub.customer_id,
            amount=result.amount,
            doc_type=DocType.CREDIT_NOTE,
            line_type=LineType.RECURRING,
            reason=f"Downgrade from {old_qty} to {payload.qty}",
        )

    db.commit()
    logger.info(
        "%s modified subscription %s: %s -> %s (%s)",
        user.full_name,
        sub.id,
        old_qty,
        payload.qty,
        result.amount,
    )

    verb = "credited" if result.is_credit else "charged"
    return ModifyResponse(
        success=True,
        message=f"Subscription modified, {verb} ${abs(result.amount)}",
        data=ProrationData(
            amount=float(result.amount),
            is_credit=result.is_credit,
            remaining_days=result.remaining_days,
            cycle_days=result.cycle_days,
            price_delta=float(result.price_delta),
            new_qty=payload.qty,
            explanation=(
                f"{result.remaining_days} of {result.cycle_days} days remain in this "
                f"period, so the ${abs(result.price_delta)} change is prorated to "
                f"${abs(result.amount)}."
            ),
        ),
    )


@router.post(
    "/{subscription_id}/cancel",
    response_model=CancelResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 409, 500)},
)
def cancel(
    subscription_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> CancelResponse:
    """Cancel and credit the unused remainder of the current period."""
    sub = _load(db, subscription_id)
    if sub.status == SubStatus.CANCELLED:
        # Otherwise cancelling twice issues a second credit for days already
        # refunded once.
        raise _conflict("This subscription is already cancelled")

    result = billing_util_cancellation_credit(
        current_charge=Decimal(str(sub.unit_price)) * Decimal(sub.qty),
        cycle=sub.plan.cycle,
        period_start=_period_start(sub),
        on=date.today(),
        # The refund policy is the plan's, not this route's - PS 4-A5.
        started_at=sub.started_at,
        refund_window_days=sub.plan.refund_window_days,
        cancellation_fee_pct=Decimal(str(sub.plan.cancellation_fee_pct)),
    )

    sub.status = SubStatus.CANCELLED
    sub.cancelled_at = date.today()

    note = None
    if result.amount != 0:
        credit = db_create_invoice(
            db,
            quotation_id=sub.quotation_id,
            customer_id=sub.customer_id,
            amount=result.amount,
            doc_type=DocType.CREDIT_NOTE,
            line_type=LineType.RECURRING,
            reason=f"Cancellation, {result.remaining_days} days unused",
        )
        note = credit.number

    db.commit()
    logger.info("%s cancelled subscription %s", user.full_name, sub.id)

    return CancelResponse(
        success=True,
        message="Subscription cancelled",
        data=CancelData(
            status=sub.status,
            credit_amount=float(result.amount),
            credit_note=note,
            explanation=(
                f"{result.remaining_days} of {result.cycle_days} days were unused, "
                f"so ${abs(result.amount)} has been credited."
                + (f" {result.note}" if result.note else "")
            ),
        ),
    )
