"""Data access for subscriptions and invoices. Every function is prefixed db_."""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.billing import (
    BillingSchedule,
    Invoice,
    InvoiceLine,
    Subscription,
    SubscriptionPlan,
)
from app.models.enums import DocType, InvoiceStatus, LineType
from app.models.quotation import Quotation
from app.utils.billing import billing_util_invoice_status


def db_list_subscriptions(session: Session) -> list[Subscription]:
    return list(
        session.scalars(
            select(Subscription)
            .options(
                selectinload(Subscription.customer),
                selectinload(Subscription.plan),
            )
            .order_by(Subscription.id)
        ).all()
    )


def db_get_subscription(session: Session, subscription_id: int) -> Subscription | None:
    return session.scalar(
        select(Subscription)
        .where(Subscription.id == subscription_id)
        .options(
            selectinload(Subscription.customer),
            selectinload(Subscription.plan),
            selectinload(Subscription.schedules),
            selectinload(Subscription.quotation).selectinload(Quotation.lines),
        )
    )


def db_list_plans(session: Session) -> list[SubscriptionPlan]:
    return list(
        session.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.id)).all()
    )


def db_add_schedule(
    session: Session,
    *,
    subscription_id: int,
    due_date: date,
    amount: Decimal,
    is_prorated: bool = False,
    note: str | None = None,
) -> BillingSchedule:
    row = BillingSchedule(
        subscription_id=subscription_id,
        due_date=due_date,
        amount=amount,
        is_prorated=is_prorated,
        note=note,
    )
    session.add(row)
    session.flush()
    return row


def db_next_invoice_number(session: Session, prefix: str = "INV") -> str:
    count = session.scalar(select(func.count()).select_from(Invoice)) or 0
    return f"{prefix}-{3080 + count + 1}"


def db_create_invoice(
    session: Session,
    *,
    quotation_id: int,
    customer_id: int,
    amount: Decimal,
    line_type: str = LineType.ONE_TIME,
    doc_type: str = DocType.INVOICE,
    issue_date: date | None = None,
    due_date: date | None = None,
    reason: str | None = None,
    lines: list[dict] | None = None,
) -> Invoice:
    """Create an invoice, or a credit note when doc_type says so.

    A credit note is this table with a negative amount - see the note on the
    Invoice model for why it is not a table of its own.
    """
    issued = issue_date or date.today()
    invoice = Invoice(
        number=db_next_invoice_number(
            session, "CN" if doc_type == DocType.CREDIT_NOTE else "INV"
        ),
        quotation_id=quotation_id,
        customer_id=customer_id,
        doc_type=doc_type,
        line_type=line_type,
        amount=amount,
        status=(
            # A credit note is owed to the customer, not by them, so it is not
            # sitting unpaid on their account.
            InvoiceStatus.PAID
            if doc_type == DocType.CREDIT_NOTE
            else InvoiceStatus.UNPAID
        ),
        reason=reason,
        issue_date=issued,
        due_date=due_date or issued,
    )
    session.add(invoice)
    session.flush()

    for line in lines or []:
        session.add(InvoiceLine(invoice_id=invoice.id, **line))
    session.flush()
    return invoice


def db_list_invoices(session: Session) -> list[Invoice]:
    return list(
        session.scalars(
            select(Invoice).options(selectinload(Invoice.customer)).order_by(Invoice.id)
        ).all()
    )


def db_get_invoice(session: Session, invoice_id: int) -> Invoice | None:
    return session.scalar(
        select(Invoice)
        .where(Invoice.id == invoice_id)
        .options(
            selectinload(Invoice.customer),
            selectinload(Invoice.lines),
            selectinload(Invoice.quotation),
        )
    )


def db_record_payment(
    session: Session,
    invoice: Invoice,
    *,
    amount: Decimal,
    method: str,
    user_id: int,
) -> Invoice:
    """Record a payment and recompute the status.

    Payments accumulate rather than overwrite, so two part-payments reach PAID
    instead of the second one replacing the first.
    """
    invoice.paid_amount = Decimal(str(invoice.paid_amount)) + Decimal(str(amount))
    invoice.paid_method = method
    invoice.paid_at = datetime.now(UTC)
    invoice.recorded_by = user_id
    invoice.status = billing_util_invoice_status(
        Decimal(str(invoice.amount)), Decimal(str(invoice.paid_amount))
    )
    session.flush()
    return invoice


def db_invoices_for_quotation(session: Session, quotation_id: int) -> list[Invoice]:
    """Every document raised against one deal, for the journey strip."""
    return list(
        session.scalars(
            select(Invoice)
            .where(Invoice.quotation_id == quotation_id)
            .order_by(Invoice.id)
        ).all()
    )
