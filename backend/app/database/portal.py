"""Data access for the customer portal. Every function is prefixed db_."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.billing import Invoice, Subscription
from app.models.enums import QuoteStatus
from app.models.fulfillment import FulfillmentAllocation
from app.models.identity import User
from app.models.negotiation import NegotiationMessage
from app.models.quotation import Quotation, QuotationLine


def db_get_portal_quotation(
    session: Session, quotation_id: int, user: User
) -> Quotation | None:
    """Fetch a quotation for a customer, scoped to their own company.

    The scoping is the point: a customer must never be able to read another
    customer's quotation by changing the id in the URL.
    """
    return session.scalar(
        select(Quotation)
        .where(
            Quotation.id == quotation_id,
            Quotation.customer_id == user.customer_id,
        )
        .options(
            selectinload(Quotation.lines).selectinload(QuotationLine.product),
            selectinload(Quotation.customer),
        )
    )


def db_list_customer_quotations(session: Session, user: User) -> list[Quotation]:
    """Every quotation belonging to the caller's company, newest first.

    The portal needs this so it can land the customer on their own quotation
    rather than a hardcoded id.
    """
    return list(
        session.scalars(
            select(Quotation)
            .where(Quotation.customer_id == user.customer_id)
            .options(selectinload(Quotation.lines))
            .order_by(Quotation.created_at.desc(), Quotation.id.desc())
        ).all()
    )


def db_list_negotiation(
    session: Session, quotation_id: int
) -> list[NegotiationMessage]:
    return list(
        session.scalars(
            select(NegotiationMessage)
            .where(NegotiationMessage.quotation_id == quotation_id)
            .order_by(NegotiationMessage.created_at, NegotiationMessage.id)
        ).all()
    )


def db_add_negotiation_message(
    session: Session,
    *,
    quotation_id: int,
    author_id: int,
    body: str | None,
    counter_discount_pct: float | None,
    requested_delivery_date=None,
    quotation_line_id: int | None = None,
) -> NegotiationMessage:
    message = NegotiationMessage(
        quotation_id=quotation_id,
        quotation_line_id=quotation_line_id,
        author_id=author_id,
        body=body,
        counter_discount_pct=counter_discount_pct,
        requested_delivery_date=requested_delivery_date,
    )
    session.add(message)
    session.flush()
    return message


def db_customer_orders(session: Session, user: User) -> list[Quotation]:
    """Deals the customer has agreed to, newest first.

    Only past the approval stage: a draft the rep is still building is not the
    customer's business, and showing it would leak internal work in progress.
    """
    return list(
        session.scalars(
            select(Quotation)
            .where(
                Quotation.customer_id == user.customer_id,
                Quotation.status.in_([QuoteStatus.APPROVED, QuoteStatus.CONFIRMED]),
            )
            .options(selectinload(Quotation.lines).selectinload(QuotationLine.product))
            .order_by(Quotation.id.desc())
        ).all()
    )


def db_customer_allocations(
    session: Session, quotation_ids: list[int]
) -> dict[int, list[FulfillmentAllocation]]:
    """Where each order is shipping from, keyed by quotation."""
    if not quotation_ids:
        return {}

    rows = session.scalars(
        select(FulfillmentAllocation)
        .where(FulfillmentAllocation.quotation_id.in_(quotation_ids))
        .options(selectinload(FulfillmentAllocation.warehouse))
    ).all()

    grouped: dict[int, list[FulfillmentAllocation]] = {}
    for row in rows:
        grouped.setdefault(row.quotation_id, []).append(row)
    return grouped


def db_customer_invoices(session: Session, user: User) -> list[Invoice]:
    """Every document raised against this company, newest first."""
    return list(
        session.scalars(
            select(Invoice)
            .where(Invoice.customer_id == user.customer_id)
            .options(selectinload(Invoice.quotation))
            .order_by(Invoice.id.desc())
        ).all()
    )


def db_customer_subscriptions(session: Session, user: User) -> list[Subscription]:
    """Recurring commitments, so a customer can see what bills again and when."""
    return list(
        session.scalars(
            select(Subscription)
            .where(Subscription.customer_id == user.customer_id)
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.id)
        ).all()
    )
