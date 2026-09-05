"""Users, customers, and the tier a customer is priced against."""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import UserRole

_ROLES = ", ".join(f"'{r.value}'" for r in UserRole)


class DiscountTier(Base):
    __tablename__ = "discount_tiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    max_discount_pct: Mapped[float] = mapped_column(Numeric(5, 2))

    customers: Mapped[list["Customer"]] = relationship(back_populates="tier")


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    tier_id: Mapped[int] = mapped_column(ForeignKey("discount_tiers.id"))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tier: Mapped[DiscountTier] = relationship(back_populates="customers")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(f"role IN ({_ROLES})", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20))

    # Set only for a CUSTOMER, and it is what scopes them to their own quotes.
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer: Mapped[Customer | None] = relationship()
