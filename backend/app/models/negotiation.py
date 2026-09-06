"""Customer-facing negotiation on a live quotation."""

from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class NegotiationMessage(Base):
    """One request from the customer, or a reply from the rep.

    Line-scoped when quotation_line_id is set, order-level otherwise - PS
    section 4 B8 asks for a line level comment and change request tool.
    """

    __tablename__ = "negotiation_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), index=True
    )
    quotation_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("quotation_lines.id", ondelete="CASCADE"), nullable=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    counter_discount_pct: Mapped[float | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    requested_delivery_date: Mapped[date | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
