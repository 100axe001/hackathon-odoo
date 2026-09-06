"""The customer-facing portal.

A genuinely separate, restricted surface. PS section 7 requires this to be "a
real, separate, restricted view, not just another internal screen with a
different label", so every route here demands the CUSTOMER role and every query
is scoped to the caller's own company.
"""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.portal import (
    db_add_negotiation_message,
    db_customer_allocations,
    db_customer_invoices,
    db_customer_orders,
    db_customer_subscriptions,
    db_get_portal_quotation,
    db_list_customer_quotations,
    db_list_negotiation,
)
from app.database.users import db_get_user_by_id
from app.logging.setup_logging import get_logger
from app.models.enums import AuditAction, DocType, QuoteStatus
from app.models.identity import User
from app.routes.dependencies import get_db, require_customer
from app.schemas.portal import (
    ConfirmData,
    ConfirmResponse,
    ErrorResponse,
    NegotiateData,
    NegotiateRequest,
    NegotiateResponse,
    PortalBillingData,
    PortalBillingResponse,
    PortalComment,
    PortalInvoice,
    PortalLine,
    PortalListResponse,
    PortalOrder,
    PortalOrdersResponse,
    PortalProfileData,
    PortalProfileResponse,
    PortalQuotationData,
    PortalQuotationResponse,
    PortalShipment,
    PortalSubscription,
    PortalSummary,
)
from app.utils.approval import (
    approval_util_build_chain,
    approval_util_needs_approval,
    record_audit,
)
from app.utils.quotation_pricing import pricing_util_explain, pricing_util_score

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


def _load(db: Session, quotation_id: str, user: User):
    quotation = db_get_portal_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        # Deliberately the same response whether the quotation does not exist or
        # belongs to another customer: the difference is not the caller's business.
        raise _not_found(f"No quotation {quotation_id}")
    return quotation


# The only states a customer may act on. A draft has not been sent to them, a
# Pending Approval quotation is with our own reviewers, and a confirmed or
# rejected one is finished. Confirming mid-approval was the dangerous case: it
# rebuilds the chain, which would silently erase a decision a manager had
# already made.
_CUSTOMER_ACTIONABLE = frozenset({QuoteStatus.APPROVED, QuoteStatus.NEGOTIATION})

_WHY_NOT = {
    QuoteStatus.DRAFT: "This quotation has not been sent to you yet.",
    QuoteStatus.PENDING_APPROVAL: (
        "This quotation is with our team for approval. We will come back to you "
        "as soon as it has been reviewed."
    ),
    QuoteStatus.CONFIRMED: "You have already confirmed this quotation.",
    QuoteStatus.REJECTED: (
        "This quotation was withdrawn. Your account manager can raise a new one."
    ),
}


def _blocked_reason(quotation) -> str | None:
    """None when the customer may act, otherwise the sentence explaining why."""
    if quotation.status in _CUSTOMER_ACTIONABLE:
        return None
    return _WHY_NOT.get(quotation.status, "This quotation cannot be changed right now.")


def _require_actionable(quotation) -> None:
    if quotation.status in _CUSTOMER_ACTIONABLE:
        return
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False,
            error="Conflict",
            message=_blocked_reason(quotation),
        ).model_dump(),
    )


def _line_amount(line) -> Decimal:
    return (
        Decimal(str(line.unit_price))
        * Decimal(str(line.qty))
        * (Decimal("100") - Decimal(str(line.discount_pct)))
        / Decimal("100")
    )


@router.get(
    "/quotations",
    response_model=PortalListResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def list_portal_quotations(
    db: Session = Depends(get_db), user: User = Depends(require_customer)
) -> PortalListResponse:
    """The caller's own quotations. Scoped by customer_id, never by a filter."""
    rows = []
    for quotation in db_list_customer_quotations(db, user):
        try:
            rows.append(
                PortalSummary(
                    id=f"q{quotation.id}",
                    number=quotation.number,
                    status=quotation.status,
                    total=float(
                        sum(
                            (_line_amount(ln) for ln in quotation.lines),
                            Decimal("0"),
                        )
                    ),
                )
            )
        except Exception as e:
            logger.warning("Skipping portal row %s: %s", quotation.id, e)

    return PortalListResponse(
        success=True,
        message=f"Successfully retrieved {len(rows)} quotations",
        data=rows,
    )


@router.get(
    "/quotations/{quotation_id}",
    response_model=PortalQuotationResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 404, 500)},
)
def get_portal_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_customer),
) -> PortalQuotationResponse:
    """The customer's own quotation, with the negotiation thread.

    Readable in any state - a customer should be able to look back at a deal
    they confirmed months ago. Acting on it is what is gated.
    """
    quotation = _load(db, quotation_id, user)

    lines = [
        PortalLine(
            id=f"l{line.id}",
            product=line.product.name,
            qty=line.qty,
            price=float(line.unit_price),
            discount_pct=float(line.discount_pct),
            amount=float(_line_amount(line)),
        )
        for line in quotation.lines
    ]

    comments = []
    for message in db_list_negotiation(db, quotation.id):
        author = db_get_user_by_id(db, message.author_id)
        comments.append(
            PortalComment(
                line=None,
                author=author.full_name if author else "Unknown",
                body=message.body,
                counter_discount_pct=(
                    float(message.counter_discount_pct)
                    if message.counter_discount_pct is not None
                    else None
                ),
                created_at=message.created_at.strftime("%b %d, %H:%M"),
            )
        )

    return PortalQuotationResponse(
        success=True,
        message="Quotation retrieved",
        data=PortalQuotationData(
            id=f"q{quotation.id}",
            number=quotation.number,
            customer=quotation.customer.name,
            status=quotation.status,
            total=float(
                sum((_line_amount(ln) for ln in quotation.lines), Decimal("0"))
            ),
            lines=lines,
            comments=comments,
            can_act=quotation.status in _CUSTOMER_ACTIONABLE,
            blocked_reason=_blocked_reason(quotation),
        ),
    )


@router.post(
    "/quotations/{quotation_id}/negotiate",
    response_model=NegotiateResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 404, 500)},
)
def negotiate(
    quotation_id: str,
    payload: NegotiateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_customer),
) -> NegotiateResponse:
    """Record a change request and put the quotation under negotiation.

    A counter discount is applied to the lines as the proposed terms, because
    PS section 4 B8 says confirmation acts on "final terms" - the counter is
    what the customer is asking to confirm. Nothing is approved by this: the
    terms are only re-scored when they confirm.
    """
    quotation = _load(db, quotation_id, user)
    _require_actionable(quotation)

    db_add_negotiation_message(
        db,
        quotation_id=quotation.id,
        author_id=user.id,
        body=payload.note,
        counter_discount_pct=payload.counter_discount_pct,
        requested_delivery_date=payload.requested_delivery_date,
    )

    if payload.counter_discount_pct is not None:
        for line in quotation.lines:
            line.discount_pct = payload.counter_discount_pct
        pricing_util_score(db, quotation)

    if payload.requested_delivery_date:
        quotation.promised_delivery_date = payload.requested_delivery_date

    quotation.status = QuoteStatus.NEGOTIATION
    record_audit(
        db,
        quotation=quotation,
        user_id=user.id,
        action=AuditAction.NEGOTIATE,
        note=(
            f"Customer requested {payload.counter_discount_pct}%"
            if payload.counter_discount_pct is not None
            else (payload.note or "Customer comment")
        ),
    )
    db.commit()

    logger.info(
        "%s countered on %s at %s%%",
        user.full_name,
        quotation.number,
        payload.counter_discount_pct,
    )

    return NegotiateResponse(
        success=True,
        message="Request submitted",
        data=NegotiateData(
            status=quotation.status,
            counter_discount_pct=payload.counter_discount_pct,
            message="Your request has been sent to the deal desk.",
        ),
    )


@router.post(
    "/quotations/{quotation_id}/confirm",
    response_model=ConfirmResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 404, 500)},
)
def confirm(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_customer),
) -> ConfirmResponse:
    """Confirm the final terms.

    The governance moment: the same engine that scored the original quotation
    re-scores the negotiated one. If the customer talked the discount past a
    threshold, the quotation goes back into approval instead of confirming -
    PS section 4 B8, and step 7 of the brief's own test script.
    """
    quotation = _load(db, quotation_id, user)
    _require_actionable(quotation)

    result = pricing_util_score(db, quotation)
    reenters = approval_util_needs_approval(result.risk_level)

    if reenters:
        steps = approval_util_build_chain(db, quotation, result.risk_level)
        quotation.status = QuoteStatus.PENDING_APPROVAL
        required = [s.required_role for s in steps]
        quotation.submitted_at = datetime.now(UTC)
    else:
        for step in list(quotation.steps):
            db.delete(step)
        quotation.status = QuoteStatus.CONFIRMED
        required = []

    record_audit(
        db,
        quotation=quotation,
        user_id=user.id,
        action=AuditAction.CONFIRM,
        note=(
            f"Customer confirmed; terms re-entered approval ({result.risk_level})"
            if reenters
            else "Customer confirmed within limits"
        ),
    )
    db.commit()

    logger.info(
        "%s confirmed %s -> %s", user.full_name, quotation.number, quotation.status
    )

    return ConfirmResponse(
        success=True,
        message=(
            "Terms exceed approval thresholds - the quotation has re-entered approval"
            if reenters
            else "Quotation confirmed"
        ),
        data=ConfirmData(
            status=quotation.status,
            risk_level=result.risk_level,
            reentered_approval=reenters,
            required_approval=required,
            explanation=pricing_util_explain(result),
        ),
    )


# ############################
# After the deal is agreed
# ############################
#
# The brief's portal covers viewing and negotiating a quotation. Once a
# customer confirms, though, the questions change: where is my order, and what
# do I owe. Everything below is read-only and scoped to the caller's company.


@router.get(
    "/orders",
    response_model=PortalOrdersResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def list_orders(
    db: Session = Depends(get_db), user: User = Depends(require_customer)
) -> PortalOrdersResponse:
    """Agreed deals and where each one is shipping from."""
    orders = db_customer_orders(db, user)
    allocations = db_customer_allocations(db, [q.id for q in orders])

    rows = []
    for quotation in orders:
        shipments = [
            PortalShipment(
                warehouse=(row.warehouse.name if row.warehouse else None),
                product=row.product.name,
                qty=row.qty,
            )
            for row in allocations.get(quotation.id, [])
        ]
        rows.append(
            PortalOrder(
                id=f"q{quotation.id}",
                number=quotation.number,
                status=quotation.status,
                total=float(
                    sum(
                        Decimal(str(line.unit_price))
                        * line.qty
                        * (Decimal("100") - Decimal(str(line.discount_pct)))
                        / Decimal("100")
                        for line in quotation.lines
                    )
                ),
                fulfillment=_fulfillment_label(quotation, shipments),
                shipments=shipments,
            )
        )

    return PortalOrdersResponse(
        success=True, message=f"Successfully retrieved {len(rows)} orders", data=rows
    )


def _fulfillment_label(quotation, shipments: list[PortalShipment]) -> str:
    """Plain language, not the internal enum.

    A customer should not have to know what SPLIT_ACCEPTED means, and a row
    with no warehouse is a backorder - which is the one status they most need
    stated rather than implied.
    """
    if not shipments:
        return "Preparing your order"
    if any(s.warehouse is None for s in shipments):
        return "Partly on backorder"
    if len({s.warehouse for s in shipments}) > 1:
        return f"Shipping in {len({s.warehouse for s in shipments})} parts"
    return "Ready to ship"


@router.get(
    "/billing",
    response_model=PortalBillingResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def billing(
    db: Session = Depends(get_db), user: User = Depends(require_customer)
) -> PortalBillingResponse:
    """Invoices, credit notes and anything that bills again."""
    invoices = db_customer_invoices(db, user)
    subscriptions = db_customer_subscriptions(db, user)

    rows = [
        PortalInvoice(
            id=f"i{inv.id}",
            number=inv.number,
            document=(
                "Credit note" if inv.doc_type == DocType.CREDIT_NOTE else "Invoice"
            ),
            order=inv.quotation.number if inv.quotation else "-",
            amount=float(inv.amount),
            paid=float(inv.paid_amount),
            balance_due=float(
                max(
                    Decimal("0"),
                    Decimal(str(inv.amount)) - Decimal(str(inv.paid_amount)),
                )
            ),
            status=inv.status,
            issue_date=inv.issue_date.strftime("%b %d, %Y"),
            due_date=inv.due_date.strftime("%b %d, %Y"),
        )
        for inv in invoices
    ]

    return PortalBillingResponse(
        success=True,
        message=f"Successfully retrieved {len(rows)} documents",
        data=PortalBillingData(
            invoices=rows,
            subscriptions=[
                PortalSubscription(
                    plan=sub.plan.name,
                    cycle=sub.plan.cycle,
                    qty=sub.qty,
                    amount=float(Decimal(str(sub.unit_price)) * sub.qty),
                    next_bill=sub.next_bill_date.strftime("%b %d, %Y"),
                    status=sub.status,
                )
                for sub in subscriptions
            ],
            # Credit notes are negative, so they net off what is owed rather
            # than being counted as another debt.
            total_outstanding=float(
                sum(Decimal(str(r.balance_due)) for r in rows if r.amount > 0)
                - sum(abs(Decimal(str(r.amount))) for r in rows if r.amount < 0)
            ),
        ),
    )


@router.get(
    "/profile",
    response_model=PortalProfileResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def profile(
    db: Session = Depends(get_db), user: User = Depends(require_customer)
) -> PortalProfileResponse:
    """The company, its pricing tier, and a count of what is open."""
    quotations = db_list_customer_quotations(db, user)
    orders = db_customer_orders(db, user)
    invoices = db_customer_invoices(db, user)

    return PortalProfileResponse(
        success=True,
        message="Profile retrieved",
        data=PortalProfileData(
            company=user.customer.name if user.customer else "-",
            tier=user.customer.tier.name if user.customer else "-",
            contact_name=user.full_name,
            contact_email=user.email,
            open_quotations=sum(
                1 for q in quotations if q.status != QuoteStatus.CONFIRMED
            ),
            orders=len(orders),
            outstanding=float(
                sum(
                    max(
                        Decimal("0"),
                        Decimal(str(i.amount)) - Decimal(str(i.paid_amount)),
                    )
                    for i in invoices
                    if i.amount > 0
                )
            ),
        ),
    )
