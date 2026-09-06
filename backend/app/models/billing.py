"""Subscriptions, their billing schedule, and invoices."""

from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import DocType, InvoiceStatus, LineType, SubStatus


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    cycle: Mapped[str] = mapped_column(String(20))
    price: Mapped[float] = mapped_column(Numeric(12, 2))
    proration_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Cancellation policy (PS 4-A5). Unused days are refunded as a credit note
    # only inside the refund window, and the fee is withheld from that credit.
    refund_window_days: Mapped[int] = mapped_column(default=365)
    cancellation_fee_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("subscription_plans.id"))
    qty: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default=SubStatus.ACTIVE)
    started_at: Mapped[date] = mapped_column()
    next_bill_date: Mapped[date] = mapped_column()
    cancelled_at: Mapped[date | None] = mapped_column(nullable=True)

    customer: Mapped["Customer"] = relationship()  # noqa: F821
    plan: Mapped[SubscriptionPlan] = relationship()

    # The order this subscription came from. Billing detail shows that order's
    # one-time lines alongside the recurring plan, which is the B7 requirement.
    quotation: Mapped["Quotation"] = relationship()  # noqa: F821
    schedules: Mapped[list["BillingSchedule"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan"
    )


class BillingSchedule(Base):
    """A charge that has not happened yet.

    Stored rather than derived because B7 asks the screen to show what is
    coming, and a prorated adjustment needs somewhere to live with its flag.
    """

    __tablename__ = "billing_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True
    )
    due_date: Mapped[date] = mapped_column()
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    is_prorated: Mapped[bool] = mapped_column(Boolean, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoices.id"), nullable=True
    )

    subscription: Mapped[Subscription] = relationship(back_populates="schedules")


class Invoice(Base):
    """One-time and recurring never share a document - see B7.

    A credit note is this table with doc_type CREDIT_NOTE and a negative amount.
    Giving it a table of its own would duplicate every field and split the
    customer's balance across two places.
    """

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id"))
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    doc_type: Mapped[str] = mapped_column(String(20), default=DocType.INVOICE)
    line_type: Mapped[str] = mapped_column(String(20), default=LineType.ONE_TIME)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(20), default=InvoiceStatus.UNPAID)

    paid_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    issue_date: Mapped[date] = mapped_column()
    due_date: Mapped[date] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer: Mapped["Customer"] = relationship()  # noqa: F821
    quotation: Mapped["Quotation"] = relationship()  # noqa: F821

    # Who settled it. The id was already stored; without the relationship the
    # screen could only show that someone had, not who.
    recorder: Mapped["User | None"] = relationship(  # noqa: F821
        foreign_keys=[recorded_by]
    )
    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(String(200))
    qty: Mapped[int] = mapped_column(default=1)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
