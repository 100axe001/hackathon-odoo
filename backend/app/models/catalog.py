"""Products and the price lists they are sold against."""

from sqlalchemy import JSON, Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(60))
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2))

    # Required for margin. Absent from every earlier draft of the spec, which
    # made the live margin indicator unimplementable.
    cost_price: Mapped[float] = mapped_column(Numeric(12, 2))

    unit: Mapped[str] = mapped_column(String(24), default="Each")
    tax_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    qty_on_hand: Mapped[int] = mapped_column(default=0)
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False)

    # Only meaningful when is_subscription. Screen 17 reveals the cadence field
    # once the subscription toggle is on.
    recurring_cycle: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Display-only on Screen 17 and never referenced by the quotation builder,
    # so a JSON column rather than a table: [{attribute, values, extra_price}].
    variants: Mapped[list | None] = mapped_column(JSON, nullable=True)
    is_promoted: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PriceList(Base):
    __tablename__ = "price_lists"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    tier_id: Mapped[int] = mapped_column(ForeignKey("discount_tiers.id"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    adjustment_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
