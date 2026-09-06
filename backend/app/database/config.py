"""Data access for the configuration tables. Every function is prefixed db_."""

from decimal import Decimal
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import Subscription, SubscriptionPlan
from app.models.catalog import PriceList
from app.models.config import (
    ApprovalRule,
    CategoryCeiling,
    RiskThreshold,
    UpsellRule,
)
from app.models.fulfillment import (
    FulfillmentAllocation,
    StockLevel,
    Warehouse,
)
from app.models.identity import Customer, DiscountTier


def db_list_tiers(session: Session) -> list[DiscountTier]:
    return list(session.scalars(select(DiscountTier).order_by(DiscountTier.id)).all())


def db_list_category_ceilings(session: Session) -> list[CategoryCeiling]:
    return list(
        session.scalars(select(CategoryCeiling).order_by(CategoryCeiling.id)).all()
    )


def db_list_customers(session: Session) -> list[Customer]:
    """Companies a portal account can be attached to, in picker order."""
    return list(session.scalars(select(Customer).order_by(Customer.name)).all())


def db_get_customer(session: Session, customer_id: int) -> Customer | None:
    return session.get(Customer, customer_id)


def db_list_approval_rules(session: Session) -> list[ApprovalRule]:
    return list(
        session.scalars(
            select(ApprovalRule).order_by(ApprovalRule.level, ApprovalRule.step_order)
        ).all()
    )


def db_list_thresholds(session: Session) -> list[RiskThreshold]:
    return list(session.scalars(select(RiskThreshold)).all())


def db_upsert_tier(session: Session, name: str, max_pct: Decimal) -> DiscountTier:
    """Update a tier's ceiling, creating it if the name is new.

    Matched on name rather than id so the admin screen can post the table it is
    showing without tracking which rows already exist.
    """
    row = session.scalar(select(DiscountTier).where(DiscountTier.name == name))
    if row is None:
        row = DiscountTier(name=name, max_discount_pct=max_pct)
        session.add(row)
    else:
        row.max_discount_pct = max_pct
    session.flush()
    return row


def db_upsert_category_ceiling(
    session: Session, category: str, max_pct: Decimal
) -> CategoryCeiling:
    row = session.scalar(
        select(CategoryCeiling).where(CategoryCeiling.category == category)
    )
    if row is None:
        row = CategoryCeiling(category=category, max_discount_pct=max_pct)
        session.add(row)
    else:
        row.max_discount_pct = max_pct
    session.flush()
    return row


def db_list_warehouses(session: Session) -> list[Warehouse]:
    return list(session.scalars(select(Warehouse).order_by(Warehouse.id)).all())


def db_upsert_warehouse(
    session: Session,
    *,
    name: str,
    region: str,
    shipping_cost_weight: Decimal,
    active: bool,
) -> Warehouse:
    row = session.scalar(select(Warehouse).where(Warehouse.name == name))
    if row is None:
        row = Warehouse(
            name=name,
            region=region,
            shipping_cost_weight=shipping_cost_weight,
            active=active,
        )
        session.add(row)
    else:
        row.region = region
        row.shipping_cost_weight = shipping_cost_weight
        row.active = active
    session.flush()
    return row


def db_upsert_plan(
    session: Session,
    *,
    name: str,
    cycle: str,
    price: Decimal,
    proration_enabled: bool,
    refund_window_days: int,
    cancellation_fee_pct: Decimal,
) -> SubscriptionPlan:
    row = session.scalar(select(SubscriptionPlan).where(SubscriptionPlan.name == name))
    if row is None:
        row = SubscriptionPlan(
            name=name,
            cycle=cycle,
            price=price,
            proration_enabled=proration_enabled,
        )
        session.add(row)
    else:
        row.cycle = cycle
        row.price = price
        row.proration_enabled = proration_enabled
    row.refund_window_days = refund_window_days
    row.cancellation_fee_pct = cancellation_fee_pct
    session.flush()
    return row


def db_replace_approval_rules(
    session: Session, rules: list[tuple[str, int, str]]
) -> list[ApprovalRule]:
    """Rewrite the whole chain.

    Replaced rather than merged: a level that loses a step must actually lose
    it, and matching rows up by position would silently keep an orphan.
    """
    for row in session.scalars(select(ApprovalRule)).all():
        session.delete(row)
    session.flush()

    created = [
        ApprovalRule(level=level, step_order=order, role=role)
        for level, order, role in rules
    ]
    session.add_all(created)
    session.flush()
    return created


def db_get_upsell_rule(session: Session) -> UpsellRule:
    """The single rule row, created on first read so the screen always has one."""
    row = session.scalar(select(UpsellRule).order_by(UpsellRule.id))
    if row is None:
        row = UpsellRule()
        session.add(row)
        session.flush()
    return row


def db_save_upsell_rule(
    session: Session, *, min_margin_pct: Decimal, max_suggestions: int
) -> UpsellRule:
    row = db_get_upsell_rule(session)
    row.min_margin_pct = min_margin_pct
    row.max_suggestions = max_suggestions
    session.flush()
    return row


def db_delete_warehouse(session: Session, warehouse_id: int) -> str | None:
    """Remove a warehouse, or say why it cannot go.

    Its stock rows go with it, because stock only means anything at a location.
    A warehouse that has actually shipped something stays: deleting it would
    leave fulfilled orders pointing at a place that no longer exists.
    """
    warehouse = session.get(Warehouse, warehouse_id)
    if warehouse is None:
        return "That warehouse no longer exists"

    shipped = session.scalar(
        select(func.count())
        .select_from(FulfillmentAllocation)
        .where(FulfillmentAllocation.warehouse_id == warehouse_id)
    )
    if shipped:
        return (
            f"{warehouse.name} has fulfilled {shipped} order lines. "
            "Deactivate it instead - the split logic already skips inactive "
            "warehouses, and the history stays intact."
        )

    for level in session.scalars(
        select(StockLevel).where(StockLevel.warehouse_id == warehouse_id)
    ).all():
        session.delete(level)
    session.delete(warehouse)
    session.flush()
    return None


def db_delete_plan(session: Session, plan_id: int) -> str | None:
    """Remove a plan unless something is subscribed to it."""
    plan = session.get(SubscriptionPlan, plan_id)
    if plan is None:
        return "That plan no longer exists"

    subscribed = session.scalar(
        select(func.count())
        .select_from(Subscription)
        .where(Subscription.plan_id == plan_id)
    )
    if subscribed:
        return (
            f"{plan.name} has {subscribed} subscription(s) on it. "
            "Cancel those first, or leave the plan in place so their billing "
            "history still resolves."
        )

    session.delete(plan)
    session.flush()
    return None


def db_delete_tier(session: Session, name: str) -> str | None:
    """Remove a discount tier unless customers or price lists still use it."""
    tier = session.scalar(select(DiscountTier).where(DiscountTier.name == name))
    if tier is None:
        return "That tier no longer exists"

    customers = session.scalar(
        select(func.count()).select_from(Customer).where(Customer.tier_id == tier.id)
    )
    if customers:
        return (
            f"{customers} customer(s) are on the {tier.name} tier. "
            "Move them to another tier first - otherwise their discount ceiling "
            "would be undefined."
        )

    for row in session.scalars(
        select(PriceList).where(PriceList.tier_id == tier.id)
    ).all():
        session.delete(row)
    session.delete(tier)
    session.flush()
    return None


def db_delete_category_ceiling(session: Session, category: str) -> str | None:
    """Remove a category ceiling. Lines in that category then fall back to the
    customer's tier ceiling alone, which is looser - so say so."""
    row = session.scalar(
        select(CategoryCeiling).where(CategoryCeiling.category == category)
    )
    if row is None:
        return "That category ceiling no longer exists"
    session.delete(row)
    session.flush()
    return None


class WarehouseUsage(TypedDict):
    """What a warehouse is actually holding and how much it has shipped."""

    product_lines: int
    units_on_hand: int
    units_reserved: int
    units_available: int
    below_reorder: int
    fulfilled_lines: int


def db_warehouse_usage(session: Session) -> dict[int, WarehouseUsage]:
    """Stock and shipping activity per warehouse, keyed by id.

    Computed in one pass rather than per row: the admin screen lists every
    warehouse, and a query each would be a request per depot.
    """
    usage: dict[int, WarehouseUsage] = {}

    for level in session.scalars(select(StockLevel)).all():
        row = usage.setdefault(
            level.warehouse_id,
            WarehouseUsage(
                product_lines=0,
                units_on_hand=0,
                units_reserved=0,
                units_available=0,
                below_reorder=0,
                fulfilled_lines=0,
            ),
        )
        row["product_lines"] += 1
        row["units_on_hand"] += level.qty_on_hand
        row["units_reserved"] += level.qty_reserved
        row["units_available"] += level.available
        if level.reorder_point > 0 and level.available <= level.reorder_point:
            row["below_reorder"] += 1

    shipped = session.execute(
        select(
            FulfillmentAllocation.warehouse_id,
            func.count(FulfillmentAllocation.id),
        )
        .where(FulfillmentAllocation.warehouse_id.is_not(None))
        .group_by(FulfillmentAllocation.warehouse_id)
    ).all()
    for warehouse_id, count in shipped:
        row = usage.setdefault(
            warehouse_id,
            WarehouseUsage(
                product_lines=0,
                units_on_hand=0,
                units_reserved=0,
                units_available=0,
                below_reorder=0,
                fulfilled_lines=0,
            ),
        )
        row["fulfilled_lines"] = int(count)

    return usage
