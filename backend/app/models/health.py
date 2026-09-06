"""Deal Health flags and the co-purchase pairs behind upsell suggestions."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class ProductPairing(Base):
    """Seeded co-purchase pairs.

    PS section 4 A6 describes pairings from historical co-purchase data. Real
    co-occurrence mining needs transaction history that does not exist yet, so
    these are seeded and ranked - which satisfies the panel in B5 without
    claiming a model we did not train.
    """

    __tablename__ = "product_pairings"
    __table_args__ = (UniqueConstraint("product_a_id", "product_b_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_a_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    product_b_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    rank: Mapped[int] = mapped_column(default=0)

    product_b: Mapped["Product"] = relationship(  # noqa: F821
        foreign_keys=[product_b_id]
    )


class DealHealthFlag(Base):
    """One raised flag. Advisory only - never feeds approval routing."""

    __tablename__ = "deal_health_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(30))
    severity: Mapped[str] = mapped_column(String(10))
    issue: Mapped[str] = mapped_column(String(200))

    # Only one of these is set, depending on type. Kept as columns rather than a
    # JSON blob so the dashboard can sort and filter on them.
    z_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    days_idle: Mapped[int | None] = mapped_column(nullable=True)
    days_slipped: Mapped[int | None] = mapped_column(nullable=True)

    flagged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    action_taken: Mapped[str | None] = mapped_column(String(20), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    quotation: Mapped["Quotation"] = relationship()  # noqa: F821
