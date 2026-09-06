"""Warehouses, stock, and how an order is split across them."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base


class Warehouse(Base):
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    region: Mapped[str] = mapped_column(String(60), default="")

    # PS section 4 A4: the weighting the split logic uses. A multiplier on the
    # base shipment cost - a distant depot costs more per box.
    shipping_cost_weight: Mapped[float] = mapped_column(Numeric(8, 2), default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class StockLevel(Base):
    __tablename__ = "stock_levels"
    __table_args__ = (UniqueConstraint("warehouse_id", "product_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty_on_hand: Mapped[int] = mapped_column(default=0)

    # Already promised to another order. available = on_hand - reserved, and it
    # is computed rather than stored so the two can never drift apart.
    qty_reserved: Mapped[int] = mapped_column(default=0)

    # Replenishment rule (PS 4-A4). Below the reorder point the row is due for
    # restock; reorder_qty is how much a replenishment would bring in.
    reorder_point: Mapped[int] = mapped_column(default=0)
    reorder_qty: Mapped[int] = mapped_column(default=0)

    warehouse: Mapped[Warehouse] = relationship()
    product: Mapped["Product"] = relationship()  # noqa: F821

    @property
    def available(self) -> int:
        return max(0, self.qty_on_hand - self.qty_reserved)


class FulfillmentAllocation(Base):
    """One warehouse supplying one product for one quotation.

    A row with warehouse_id = NULL is a backorder: demand nothing could cover.
    Keeping it in the same table means one query returns the whole picture
    including the shortfall.
    """

    __tablename__ = "fulfillment_allocations"

    id: Mapped[int] = mapped_column(primary_key=True)
    quotation_id: Mapped[int] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    warehouse_id: Mapped[int | None] = mapped_column(
        ForeignKey("warehouses.id"), nullable=True
    )
    qty: Mapped[int] = mapped_column()
    shipping_cost: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    is_override: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    warehouse: Mapped[Warehouse | None] = relationship()
    product: Mapped["Product"] = relationship()  # noqa: F821
