"""Quotations, their lines, the approval chain, and the audit trail."""

from datetime import date, datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import FulfilStatus, LineType, QuoteStatus, StepStatus


class Quotation(Base):
    __tablename__ = "quotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))

    # Owner. Scopes what a rep sees, anchors the anomaly baseline, and backs the
    # Reports rep filter.
    rep_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    status: Mapped[str] = mapped_column(String(20), default=QuoteStatus.DRAFT)
    promised_delivery_date: Mapped[date | None] = mapped_column(nullable=True)

    # Derived from the fulfillment split once that exists. Delivery slippage is
    # the comparison of the two, so both have to be storable.
    expected_delivery_date: Mapped[date | None] = mapped_column(nullable=True)

    # Where the order is in shipping. Kept on the quotation rather than a
    # separate orders table: the wireframe calls it "Order Q-1042", so the
    # quotation number IS the order number.
    fulfillment_status: Mapped[str] = mapped_column(
        String(20), default=FulfilStatus.NONE
    )

    # --- risk engine output, all computed server-side ---
    risk_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    worst_line_excess_pt: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    blended_excess_pt: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    blended_score: Mapped[float | None] = mapped_column(Numeric(4, 3), nullable=True)
    violating_line_count: Mapped[int | None] = mapped_column(nullable=True)
    total_excess_value: Mapped[float | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    total_list_value: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total_net_value: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    # Bumped by record_audit, not by an ORM onupdate: activity means a person
    # acted, not that some column changed.
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    customer: Mapped["Customer"] = relationship()  # noqa: F821
    rep: Mapped["User"] = relationship()  # noqa: F821

    lines: Mapped[list["QuotationLine"]] = relationship(
        back_populates="quotation", cascade="all, delete-orphan"
    )
    steps: Mapped[list["ApprovalStep"]] = relationship(
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="ApprovalStep.step_order",
    )


class QuotationLine(Base):
    __tablename__ = "quotation_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[int] = mapped_column(default=1)

    # Both prices are snapshots. If a product is repriced later, an existing
    # quotation's margin must not silently change.
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2))

    discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)

    # min(tier, category), frozen at validation so the ceiling that was actually
    # in force stays auditable even if configuration changes afterwards.
    allowed_discount_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    excess_pt: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    line_type: Mapped[str] = mapped_column(String(20), default=LineType.ONE_TIME)

    quotation: Mapped[Quotation] = relationship(back_populates="lines")
    product: Mapped["Product"] = relationship()  # noqa: F821


class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    __table_args__ = (UniqueConstraint("quotation_id", "step_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE")
    )
    step_order: Mapped[int] = mapped_column()
    required_role: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default=StepStatus.PENDING)
    acted_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    quotation: Mapped[Quotation] = relationship(back_populates="steps")


class AuditLog(Base):
    """Append only. Never updated, never deleted.

    PS section 4 A3 requires user, timestamp and reason on every approval,
    rejection and edit. This table is what makes the governance claim checkable
    rather than decorative.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
