"""Quotations: listing, the builder, live line validation, and submission."""

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.billing import db_invoices_for_quotation
from app.database.config import db_get_upsell_rule
from app.database.fulfillment import db_release_quotation_stock
from app.database.portal import db_add_negotiation_message, db_list_negotiation
from app.database.quotations import (
    db_billed_quotation_ids,
    db_create_quotation,
    db_delete_quotation,
    db_get_customer,
    db_get_line,
    db_get_product,
    db_get_quotation,
    db_list_quotations,
    db_set_quotation_status,
    db_upsell_candidates,
)
from app.database.users import db_get_user_by_id
from app.logging.setup_logging import get_logger
from app.models.enums import AuditAction, QuoteStatus, UserRole
from app.models.identity import User
from app.models.quotation import QuotationLine
from app.routes.dependencies import get_db, require_internal
from app.schemas.quotations import (
    AddLineRequest,
    AddLineResponse,
    CreateQuotationRequest,
    CreateQuotationResponse,
    DeleteQuotationResponse,
    ErrorResponse,
    JourneyData,
    JourneyResponse,
    JourneyStage,
    LineData,
    LineStatusData,
    ListQuotationsResponse,
    NextAction,
    PatchDiscountRequest,
    PatchDiscountResponse,
    QuotationDetailData,
    QuotationDetailResponse,
    QuotationSummary,
    ReplyRequest,
    StageChangeRequest,
    StageChangeResponse,
    SubmitData,
    SubmitResponse,
    ThreadMessage,
    ThreadResponse,
    UpsellResponse,
    UpsellSuggestion,
)
from app.utils.approval import (
    approval_util_build_chain,
    approval_util_current_step,
    approval_util_needs_approval,
    approval_util_returned_step,
    record_audit,
)
from app.utils.journey import journey_util_next, journey_util_stages
from app.utils.margin import margin_util_quotation
from app.utils.quotation_lifecycle import (
    lifecycle_util_can_delete,
    lifecycle_util_delete_block,
)
from app.utils.quotation_pricing import pricing_util_explain, pricing_util_score
from app.utils.upsell import (
    upsell_util_clears_floor,
    upsell_util_margin_delta,
    upsell_util_promo_tag,
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


def _internal_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ErrorResponse(
            success=False, error="Internal Server Error", message=message
        ).model_dump(),
    )


def _bad_request(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ErrorResponse(
            success=False, error="Bad Request", message=message
        ).model_dump(),
    )


def _forbidden(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ErrorResponse(
            success=False, error="Forbidden", message=message
        ).model_dump(),
    )


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False, error="Conflict", message=message
        ).model_dump(),
    )


# Statuses the governance engine owns, and the endpoint that owns entering and
# leaving each. Named in the refusal so a caller is told where the transition
# actually lives rather than just being told no.
_GOVERNED_BY = {
    QuoteStatus.PENDING_APPROVAL: (
        "POST /quotations/{id}/submit and POST /quotations/{id}/approve"
    ),
    QuoteStatus.APPROVED: (
        "POST /quotations/{id}/submit and POST /quotations/{id}/approve"
    ),
    QuoteStatus.CONFIRMED: "POST /portal/quotations/{id}/confirm",
    QuoteStatus.REJECTED: "POST /quotations/{id}/approve",
}

# What a drag on the kanban may do. Deliberately only the two moves no other
# endpoint owns: Draft and Negotiation are the pre-governance stages. Every
# other status is reached by scoring, an approver's decision, or the customer
# confirming, so letting a drop write it would route around the approval engine
# entirely. Being in one of these two is not on its own proof that no chain is
# live, so change_stage checks for an outstanding step as well.
_PIPELINE_MOVES = {
    (QuoteStatus.DRAFT, QuoteStatus.NEGOTIATION),
    (QuoteStatus.NEGOTIATION, QuoteStatus.DRAFT),
}

_STAGE_NAMES = frozenset(stage.value for stage in QuoteStatus)


def _refusal(current: str, target: str) -> str:
    blocked = target if target in _GOVERNED_BY else current
    owner = _GOVERNED_BY.get(blocked)
    reason = (
        f"{blocked} is decided by the approval engine - use {owner}."
        if owner
        else "That is not a pipeline move."
    )
    return f"Cannot drag from {current} to {target}. {reason}"


def _to_summary(quotation, *, can_delete: bool = False) -> QuotationSummary:
    # Computed from the lines rather than read from total_net_value. That column
    # is only written when a quotation is scored, so an unopened draft would
    # list as $0 - which is what the kanban and the list both showed.
    net = sum(
        (
            Decimal(str(line.unit_price))
            * Decimal(str(line.qty))
            * (Decimal("100") - Decimal(str(line.discount_pct)))
            / Decimal("100")
            for line in quotation.lines
        ),
        Decimal("0"),
    )
    return QuotationSummary(
        id=f"q{quotation.id}",
        customer_name=quotation.customer.name,
        amount=float(net),
        status=quotation.status,
        can_delete=can_delete,
    )


@router.get(
    "",
    response_model=ListQuotationsResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_quotations(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListQuotationsResponse:
    """Every quotation the caller may see. A rep sees only their own."""
    # One query for the whole page rather than one per row - the delete rule
    # needs to know which quotations have money against them.
    billed = db_billed_quotation_ids(db)

    rows = []
    for quotation in db_list_quotations(db, user):
        try:
            rows.append(
                _to_summary(
                    quotation,
                    can_delete=lifecycle_util_can_delete(
                        quotation, user, billed=quotation.id in billed
                    ),
                )
            )
        except (TypeError, ValueError, AttributeError) as e:
            # One unusable record must not 500 the listing and hide the rest.
            # Deliberately not a bare Exception: a broad catch here silently
            # turned a NameError into an empty list, which read as "this rep
            # owns nothing" rather than "the code is broken".
            logger.warning("Skipping quotation %s: %s", quotation.id, e)

    return ListQuotationsResponse(
        success=True,
        message=f"Successfully retrieved {len(rows)} quotations",
        data=rows,
    )


def _to_detail(session: Session, quotation, lines, user) -> QuotationDetailData:
    """Detail payload including live margin - PS section 4 B3."""
    margin, margin_pct = margin_util_quotation(quotation.lines)
    returned_by, returned_note = _returned_notice(session, quotation)
    can_delete = lifecycle_util_can_delete(
        quotation, user, billed=quotation.id in db_billed_quotation_ids(session)
    )
    return QuotationDetailData(
        id=f"q{quotation.id}",
        number=quotation.number,
        customer_name=quotation.customer.name,
        price_list=quotation.customer.tier.name,
        lines=lines,
        margin=float(margin),
        margin_pct=float(margin_pct),
        net_total=float(quotation.total_net_value or 0),
        status=quotation.status,
        risk_level=quotation.risk_level,
        returned_by=returned_by,
        returned_note=returned_note,
        can_delete=can_delete,
    )


def _returned_notice(session: Session, quotation) -> tuple[str | None, str | None]:
    """Who sent this quotation back and what they asked for, while it is back.

    Only meaningful on a Draft: once it is resubmitted the chain is rebuilt, and
    on anything further along the return is history rather than the thing the
    rep has to act on.
    """
    if quotation.status != QuoteStatus.DRAFT:
        return None, None
    step = approval_util_returned_step(quotation)
    if step is None:
        return None, None
    reviewer = db_get_user_by_id(session, step.acted_by)
    return (reviewer.full_name if reviewer else "A reviewer"), step.comment


def _line_rows(quotation) -> list[LineData]:
    return [
        LineData(
            id=f"l{line.id}",
            product=line.product.name,
            qty=line.qty,
            price=float(line.unit_price),
            discount_pct=float(line.discount_pct),
            limit_pct=float(line.allowed_discount_pct),
            status="OVER" if line.excess_pt > 0 else "OK",
        )
        for line in quotation.lines
    ]


def _parse_id(raw: str) -> int:
    """Accept both 'q12' and '12'; the frontend uses the prefixed form."""
    try:
        return int(raw[1:] if raw.startswith("q") else raw)
    except ValueError as e:
        raise _not_found(f"No quotation {raw}") from e


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateQuotationResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def create_quotation(
    payload: CreateQuotationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> CreateQuotationResponse:
    """Open an empty draft for a customer.

    The owner is the authenticated caller, never the payload: a rep who could
    name someone else would escape their own anomaly baseline and the row
    scoping that keeps a rep to their own pipeline.
    """
    customer = db_get_customer(db, payload.customer_id)
    if customer is None:
        raise _not_found(f"No customer {payload.customer_id}")

    quotation = db_create_quotation(db, customer_id=customer.id, rep_id=user.id)
    logger.info("%s opened %s for %s", user.email, quotation.number, customer.name)

    # Same shape as GET /quotations/{id} so the UI can navigate straight in.
    return CreateQuotationResponse(
        success=True,
        message=f"{quotation.number} created",
        data=_to_detail(db, quotation, [], user),
    )


@router.delete(
    "/{quotation_id}",
    response_model=DeleteQuotationResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 404, 409, 500)},
)
def delete_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> DeleteQuotationResponse:
    """Throw away a quotation you opened.

    Whoever created it may delete it, sales rep or admin alike - the same person
    who could add every line to it can drop the whole thing. Someone else's is
    not yours to remove, and neither is one that has been billed or confirmed.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    billed = quotation.id in db_billed_quotation_ids(db)
    block = lifecycle_util_delete_block(quotation, user, billed=billed)
    if block:
        # Not yours is a 403; yours but past the point of no return is a 409.
        # Collapsing both into one status would tell a rep to go and find the
        # owner of a quotation they already own.
        raise _forbidden(block) if quotation.rep_id != user.id else _conflict(block)

    # Snapshot before the row goes, so the caller gets back what it removed.
    removed = _to_summary(quotation, can_delete=True)
    number = quotation.number
    # Reservations are released first: the allocation rows cascade away with the
    # quotation, and reserved units with no row to release them are gone for good.
    db_release_quotation_stock(db, quotation)
    db_delete_quotation(db, quotation)

    logger.info("%s deleted %s", user.email, number)
    return DeleteQuotationResponse(
        success=True,
        message=f"{number} deleted",
        data=removed,
    )


@router.get(
    "/{quotation_id}",
    response_model=QuotationDetailResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def get_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> QuotationDetailResponse:
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    # Re-score on read so the builder always shows current ceilings, even if the
    # admin changed a limit since the quote was last touched.
    pricing_util_score(db, quotation)
    db.commit()

    lines = [
        LineData(
            id=f"l{line.id}",
            product=line.product.name,
            qty=line.qty,
            price=float(line.unit_price),
            discount_pct=float(line.discount_pct),
            limit_pct=float(line.allowed_discount_pct),
            status="OVER" if line.excess_pt > 0 else "OK",
        )
        for line in quotation.lines
    ]

    return QuotationDetailResponse(
        success=True,
        message="Quotation retrieved",
        data=_to_detail(db, quotation, lines, user),
    )


@router.patch(
    "/{quotation_id}/lines/{line_id}",
    response_model=PatchDiscountResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def patch_line_discount(
    quotation_id: str,
    line_id: str,
    payload: PatchDiscountRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> PatchDiscountResponse:
    """Validate one line's discount against its own ceiling.

    The builder calls this on every edit. The backend is authoritative: the
    frontend never decides a limit, it only renders what comes back.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    raw_line = line_id[1:] if line_id.startswith("l") else line_id
    line = db_get_line(db, int(raw_line))
    if line is None or line.quotation_id != quotation.id:
        raise _not_found(f"No line {line_id} on {quotation_id}")

    if payload.discount_pct is None and payload.qty is None:
        raise _bad_request("Send a discount_pct, a qty, or both")

    changes = []
    if payload.discount_pct is not None:
        line.discount_pct = payload.discount_pct
        changes.append(f"discount set to {payload.discount_pct}%")
    if payload.qty is not None:
        line.qty = payload.qty
        changes.append(f"quantity set to {payload.qty}")

    # Re-score after both edits, not after each: quantity moves the blended
    # weighting, so scoring a discount against a stale quantity would report a
    # risk level the quotation no longer has.
    pricing_util_score(db, quotation)
    margin, margin_pct = margin_util_quotation(quotation.lines)

    record_audit(
        db,
        quotation=quotation,
        user_id=user.id,
        action=AuditAction.DISCOUNT_EDIT,
        note=f"{line.product.name} {' and '.join(changes)}",
    )
    db.commit()

    return PatchDiscountResponse(
        success=True,
        message="Line validated",
        data=LineStatusData(
            status="OVER" if line.excess_pt > 0 else "OK",
            over_by_pct=float(line.excess_pt),
            allowed_discount_pct=float(line.allowed_discount_pct),
            qty=line.qty,
            line_total=float(
                Decimal(str(line.unit_price))
                * Decimal(line.qty)
                * (Decimal("100") - Decimal(str(line.discount_pct)))
                / Decimal("100")
            ),
            margin=float(margin),
            margin_pct=float(margin_pct),
        ),
    )


@router.post(
    "/{quotation_id}/submit",
    response_model=SubmitResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def submit_quotation(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> SubmitResponse:
    """Score the quotation and route it.

    The rep never asks for approval: the risk level decides, and the chain comes
    from the configured approval rules.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    result = pricing_util_score(db, quotation)
    needs = approval_util_needs_approval(result.risk_level)

    if needs:
        steps = approval_util_build_chain(db, quotation, result.risk_level)
        quotation.status = QuoteStatus.PENDING_APPROVAL
        required = [s.required_role for s in steps]
    else:
        for step in list(quotation.steps):
            db.delete(step)
        quotation.status = QuoteStatus.APPROVED
        required = []

    quotation.submitted_at = datetime.now(UTC)
    record_audit(
        db,
        quotation=quotation,
        user_id=user.id,
        action=AuditAction.SUBMIT,
        note=pricing_util_explain(result),
    )
    db.commit()

    logger.info(
        "Quotation %s submitted: %s via %s -> %s",
        quotation.number,
        result.risk_level,
        result.decided_by,
        required or "auto-approved",
    )

    return SubmitResponse(
        success=True,
        message=(
            "Routed for approval" if needs else "Auto-approved, no approval required"
        ),
        data=SubmitData(
            risk_level=result.risk_level,
            decided_by=result.decided_by,
            blended_score=float(result.blended_score),
            required_approval=required,
            status=quotation.status,
            explanation=pricing_util_explain(result),
        ),
    )


@router.get(
    "/{quotation_id}/upsell-suggestions",
    response_model=UpsellResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def upsell_suggestions(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> UpsellResponse:
    """Ranked cross-sell candidates with the margin each would add."""
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    # The margin floor is configuration, not a constant: suggesting a product
    # that erodes margin is worse than suggesting nothing.
    rule = db_get_upsell_rule(db)
    floor = Decimal(str(rule.min_margin_pct))
    suggestions = [
        UpsellSuggestion(
            product_id=product.id,
            product=product.name,
            margin_delta=float(upsell_util_margin_delta(product)),
            promo_tag=upsell_util_promo_tag(product),
        )
        for product in db_upsell_candidates(db, quotation)
        if upsell_util_clears_floor(product, floor)
    ][: rule.max_suggestions]

    return UpsellResponse(
        success=True,
        message=f"Successfully retrieved {len(suggestions)} suggestions",
        data=suggestions,
    )


@router.post(
    "/{quotation_id}/lines",
    status_code=status.HTTP_201_CREATED,
    response_model=AddLineResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def add_line(
    quotation_id: str,
    payload: AddLineRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> AddLineResponse:
    """Add a product to the quotation and re-score.

    Prices are snapshotted onto the line so a later reprice cannot silently
    change an existing quotation's margin.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    product = db_get_product(db, payload.product_id)
    if product is None:
        raise _not_found(f"No product {payload.product_id}")

    quotation.lines.append(
        QuotationLine(
            quotation_id=quotation.id,
            product_id=product.id,
            qty=payload.qty,
            unit_price=product.unit_price,
            cost_price=product.cost_price,
            discount_pct=0,
        )
    )
    db.flush()

    pricing_util_score(db, quotation)
    record_audit(
        db,
        quotation=quotation,
        user_id=user.id,
        action=AuditAction.DISCOUNT_EDIT,
        note=f"Added {product.name} to the quotation",
    )
    db.commit()

    return AddLineResponse(
        success=True,
        message=f"{product.name} added",
        data=_to_detail(db, quotation, _line_rows(quotation), user),
    )


@router.post(
    "/{quotation_id}/stage",
    response_model=StageChangeResponse,
    responses={code: {"model": ErrorResponse} for code in (400, 404, 500)},
)
def change_stage(
    quotation_id: str,
    payload: StageChangeRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> StageChangeResponse:
    """Move a deal between the two pipeline stages nothing else owns.

    No audit row is written: a drag is a pipeline gesture, not a governance
    action, and reusing NEGOTIATE here would put internal drags in the same
    trail as the customer's real counter-offers.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    target = payload.status
    if target not in _STAGE_NAMES:
        raise _bad_request(f"{target!r} is not a quotation stage")

    # The board merges this row into the card it just moved, so the flag has to
    # come back with it - defaulting it here made the delete action vanish from
    # every card that had been dragged.
    deletable = lifecycle_util_can_delete(
        quotation, user, billed=quotation.id in db_billed_quotation_ids(db)
    )

    # Dropping a card back on its own column is a no-op, not a failure.
    if target == quotation.status:
        return StageChangeResponse(
            success=True,
            message=f"Already in {target}",
            data=_to_summary(quotation, can_delete=deletable),
        )

    if (quotation.status, target) not in _PIPELINE_MOVES:
        raise _bad_request(_refusal(quotation.status, target))

    # Negotiation is not always chain-free: the portal's negotiate leaves the
    # pending steps in place, so a quote can sit in Negotiation mid-approval.
    # Dragging that back to Draft would leave a live chain on a Draft card,
    # which the approve endpoint would still act on.
    if approval_util_current_step(quotation) is not None:
        raise _bad_request(
            f"Cannot drag from {quotation.status} to {target} while an approval "
            "is outstanding - use POST /quotations/{id}/approve."
        )

    db_set_quotation_status(db, quotation, target)
    logger.info("%s moved %s to %s", user.email, quotation.number, quotation.status)

    return StageChangeResponse(
        success=True,
        message=f"Moved to {target}",
        data=_to_summary(quotation, can_delete=deletable),
    )


# ############################
# Conversation with the customer
# ############################


@router.get(
    "/{quotation_id}/messages",
    response_model=ThreadResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def read_thread(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> ThreadResponse:
    """The negotiation thread, as the rep sees it.

    The customer already had this on their side of the portal; without it here,
    a rep could read a counter-offer only as a number on the quotation and had
    nowhere to answer the question that came with it.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    return ThreadResponse(
        success=True,
        message="Thread retrieved",
        data=_thread(db, quotation.id),
    )


@router.post(
    "/{quotation_id}/messages",
    status_code=status.HTTP_201_CREATED,
    response_model=ThreadResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def reply_to_customer(
    quotation_id: str,
    payload: ReplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> ThreadResponse:
    """Answer the customer. PS section 3: a rep responds to negotiation requests.

    Carries no counter discount: a reply is an answer, and changing the terms is
    a line edit that has to go back through scoring.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    db_add_negotiation_message(
        db,
        quotation_id=quotation.id,
        author_id=user.id,
        body=payload.body,
        counter_discount_pct=None,
    )
    record_audit(
        db,
        quotation=quotation,
        user_id=user.id,
        action=AuditAction.NEGOTIATE,
        note="Replied to the customer",
    )
    db.commit()
    logger.info("%s replied on %s", user.email, quotation.number)

    return ThreadResponse(
        success=True,
        message="Reply sent",
        data=_thread(db, quotation.id),
    )


def _thread(db: Session, quotation_id: int) -> list[ThreadMessage]:
    """The conversation, oldest first, with each side labelled.

    The author is looked up per row rather than through a relationship, because
    NegotiationMessage stores author_id only - the same way the portal reads it.
    """
    rows = []
    for message in db_list_negotiation(db, quotation_id):
        author = db_get_user_by_id(db, message.author_id)
        rows.append(
            ThreadMessage(
                author=author.full_name if author else "Unknown",
                # A rep needs to tell the customer apart from their own
                # colleagues at a glance; the name alone does not do that.
                role=(
                    "Customer" if author and author.role == UserRole.CUSTOMER else "Us"
                ),
                body=message.body,
                counter_discount_pct=(
                    float(message.counter_discount_pct)
                    if message.counter_discount_pct is not None
                    else None
                ),
                created_at=message.created_at.strftime("%b %d, %Y %H:%M"),
            )
        )
    return rows


@router.get(
    "/{quotation_id}/journey",
    response_model=JourneyResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def journey(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> JourneyResponse:
    """Where this deal stands across quotation-to-cash, and the one next step.

    Every screen that touches a deal reads this, so the workspace stops being a
    set of tabs that each know their own step and nothing either side of it.
    """
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    invoices = db_invoices_for_quotation(db, quotation.id)
    stages = journey_util_stages(quotation, invoices)
    nxt = journey_util_next(quotation, invoices, stages)

    return JourneyResponse(
        success=True,
        message="Journey retrieved",
        data=JourneyData(
            number=quotation.number,
            customer=quotation.customer.name,
            stages=[
                JourneyStage(key=s.key, label=s.label, state=s.state, detail=s.detail)
                for s in stages
            ],
            next_action=(
                NextAction(label=nxt.label, path=nxt.path, role=nxt.role)
                if nxt
                else None
            ),
        ),
    )
