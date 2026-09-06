"""Configuration that drives the risk engine.

Nothing here is hardcoded in the engine: Screen 18 edits these tables and the
routing changes with them. That is the point of the admin screen.
"""

from sqlalchemy import Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


class CategoryCeiling(Base):
    __tablename__ = "category_ceilings"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(60), unique=True)
    max_discount_pct: Mapped[float] = mapped_column(Numeric(5, 2))


class RiskThreshold(Base):
    """Cut-points for the two-path engine. See risk-engine-and-ml.md 3.5."""

    __tablename__ = "risk_thresholds"
    __table_args__ = (UniqueConstraint("rule_type", "level"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_type: Mapped[str] = mapped_column(String(20))
    level: Mapped[str] = mapped_column(String(10))
    min_excess_pt: Mapped[float] = mapped_column(Numeric(5, 2))


class ApprovalRule(Base):
    """Which roles review a quotation at each risk level, and in what order."""

    __tablename__ = "approval_rules"
    __table_args__ = (UniqueConstraint("level", "step_order"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(10))
    step_order: Mapped[int] = mapped_column()
    role: Mapped[str] = mapped_column(String(20))


class UpsellRule(Base):
    """The margin floor a suggestion must clear before a rep ever sees it.

    One row. PS 4-A6 asks for a configurable threshold so only healthy-margin
    products surface; keeping it in a table means the admin screen can move it
    without a deploy, like every other rule the engine reads.
    """

    __tablename__ = "upsell_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    min_margin_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    max_suggestions: Mapped[int] = mapped_column(default=5)
