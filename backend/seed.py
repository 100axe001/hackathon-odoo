"""Deterministic demo data.

Never enter demo data through the UI - reset_db.py drops everything, and a
record created by clicking around will not survive it.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.billing import db_add_schedule, db_create_invoice
from app.database.connection import SessionLocal
from app.logging.setup_logging import get_logger
from app.models.billing import Subscription, SubscriptionPlan
from app.models.catalog import PriceList, Product
from app.models.config import (
    ApprovalRule,
    CategoryCeiling,
    RiskThreshold,
    UpsellRule,
)
from app.models.enums import (
    BillingCycle,
    DocType,
    FulfilStatus,
    InvoiceStatus,
    LineType,
    QuoteStatus,
    RiskLevel,
    RuleType,
    SubStatus,
    UserRole,
)
from app.models.fulfillment import StockLevel, Warehouse
from app.models.health import ProductPairing
from app.models.identity import Customer, DiscountTier, User
from app.models.quotation import Quotation, QuotationLine
from app.utils.approval import (
    AuditAction,
    approval_util_build_chain,
    approval_util_needs_approval,
    record_audit,
)
from app.utils.billing import billing_util_next_bill_date
from app.utils.quotation_pricing import pricing_util_score
from app.utils.security import security_util_hash_password

logger = get_logger(__name__)

PASSWORD = "dealflow123"

TIERS = [("Bronze", 5), ("Silver", 10), ("Gold", 15)]

# PS section 10: Services are capped tighter than Hardware because their margins
# are thin. This is what makes the headline example work.
CATEGORY_CEILINGS = [("Hardware", 15), ("Services", 10), ("Subscription", 10)]

# risk-engine-and-ml.md 3.5. Any violation needs a manager; 5pt on one line, or
# 3pt across the order, needs Finance too.
THRESHOLDS = [
    (RuleType.WORST_LINE, RiskLevel.MEDIUM, "0.01"),
    (RuleType.WORST_LINE, RiskLevel.HIGH, "5"),
    (RuleType.BLENDED, RiskLevel.MEDIUM, "1"),
    (RuleType.BLENDED, RiskLevel.HIGH, "3"),
]

APPROVAL_RULES = [
    (RiskLevel.MEDIUM, 1, UserRole.SALES_MANAGER),
    (RiskLevel.HIGH, 1, UserRole.SALES_MANAGER),
    (RiskLevel.HIGH, 2, UserRole.FINANCE),
]

#                name                    category     price   cost  promoted
PRODUCTS = [
    ("Laptop Pro 14", "Hardware", 1200, 780, False),
    ("Onsite Setup Service", "Services", 450, 160, False),
    ("Extended Warranty", "Hardware", 180, 60, True),
    ("Docking Station", "Hardware", 320, 190, False),
    ("Care Plan 2yr", "Subscription", 46, 12, True),
]

#              name              region        weight  active
WAREHOUSES = [
    ("Main Warehouse", "US-West", 1.0, True),
    ("East Depot", "US-East", 1.4, True),
    ("EU Transit Hub", "EU-Central", 2.1, False),
]

# Stock is set so Q-1042 cannot ship from one warehouse: Main is two laptops
# short, which is the wireframe's split and the spec's worked example.
#            warehouse         product                 on_hand  reserved
# on_hand, reserved, reorder_point, reorder_qty. The reorder points are set so
# East Depot's laptops already sit below theirs - the replenishment rule has
# something to report the moment the screen opens.
STOCK = [
    ("Main Warehouse", "Laptop Pro 14", 40, 39, 10, 50),
    ("Main Warehouse", "Onsite Setup Service", 100, 0, 0, 0),
    ("Main Warehouse", "Extended Warranty", 60, 10, 15, 40),
    ("Main Warehouse", "Docking Station", 65, 12, 20, 60),
    ("East Depot", "Laptop Pro 14", 10, 6, 8, 30),
    ("East Depot", "Extended Warranty", 25, 5, 10, 25),
    ("East Depot", "Docking Station", 18, 2, 12, 30),
    ("EU Transit Hub", "Laptop Pro 14", 200, 0, 25, 100),
]

#          name              cycle                    price  proration
# name, cycle, price, proration, refund_window_days, cancellation_fee_pct.
# Support SLA is the strict one: a 90-day refund window and a 10% fee, so the
# cancellation policy visibly differs between plans instead of being uniform.
PLANS = [
    ("Care Plan 2yr", BillingCycle.MONTHLY, 46, True, 365, 0),
    ("Support SLA", BillingCycle.QUARTERLY, 300, True, 90, 10),
    ("Care Plan 1yr", BillingCycle.MONTHLY, 28, False, 180, 5),
]

# Seeded co-purchase pairs, highest rank first. A laptop pulls the accessories
# and the cover; a setup service pulls the care plan.
# tier, currency, adjustment off list. What a tier pays before any rep
# discount, which is a different lever from the discount ceiling.
PRICE_LISTS = [
    ("Bronze", "USD", 0),
    ("Silver", "USD", 3),
    ("Gold", "USD", 7),
]

# Margins run Laptop 35%, Docking 40.6%, Setup 64.4%, Warranty 66.7%, Care Plan
# 73.9%. A floor of 38 therefore excludes the laptop and nothing else - the
# thinnest-margin product, and a poor cross-sell on a quote that already has one.
UPSELL_MIN_MARGIN_PCT = 38
UPSELL_MAX_SUGGESTIONS = 5

PAIRINGS = [
    ("Laptop Pro 14", "Docking Station", 30),
    ("Laptop Pro 14", "Extended Warranty", 20),
    ("Laptop Pro 14", "Care Plan 2yr", 10),
    ("Onsite Setup Service", "Care Plan 2yr", 25),
]

CUSTOMERS = [
    ("Acme Corp", "Gold"),
    ("Beta Industries", "Silver"),
    ("Delta LLC", "Bronze"),
]

# Two reps, deliberately: the discount anomaly baseline needs more than one
# distribution to compare against, and the Reports rep filter needs something
# to filter.
# Real-looking domains on purpose: EmailStr rejects RFC 2606 reserved TLDs such
# as .test, so seeded accounts must not use them.
USERS = [
    ("rep@dealflow360.com", "Alex Turner", UserRole.SALES_REP, None),
    ("rep2@dealflow360.com", "Jordan Rao", UserRole.SALES_REP, None),
    ("rep3@dealflow360.com", "Priya Nair", UserRole.SALES_REP, None),
    ("manager@dealflow360.com", "Maya Shah", UserRole.SALES_MANAGER, None),
    ("finance@dealflow360.com", "Riya Iyer", UserRole.FINANCE, None),
    ("admin@dealflow360.com", "Sam Okafor", UserRole.ADMIN, None),
    ("customer@acmecorp.com", "Devon Cole", UserRole.CUSTOMER, "Acme Corp"),
]


# ---------------------------------------------------------------------------
# Volume. Everything below is added on top of the fixtures above, never in
# place of them: Q-1042, the health scenarios and the Laptop Pro 14 stock
# arrangement are what the tests and the demo depend on, so they stay exactly
# as they are. New rows use new customers, new products and new warehouses.
# ---------------------------------------------------------------------------

MORE_CUSTOMERS = [
    ("Northwind Traders", "Gold"),
    ("Contoso Manufacturing", "Gold"),
    ("Fabrikam Logistics", "Silver"),
    ("Tailspin Aviation", "Silver"),
    ("Wide World Importers", "Bronze"),
    ("Litware Consulting", "Bronze"),
    ("Proseware Health", "Silver"),
]

#                 name                     category        price  cost  promoted
MORE_PRODUCTS = [
    ("Desktop Workstation", "Hardware", 1850, 1240, False),
    ("Ultrawide Monitor 34", "Hardware", 740, 430, True),
    ("Mechanical Keyboard", "Hardware", 145, 62, False),
    ("Conference Room Kit", "Hardware", 2400, 1560, False),
    ("Network Switch 48p", "Hardware", 980, 620, False),
    ("Rugged Tablet 10", "Hardware", 860, 545, True),
    ("Data Migration", "Services", 3200, 1180, False),
    ("Staff Training Day", "Services", 1400, 520, False),
    ("Security Audit", "Services", 2750, 990, True),
    ("Custom Integration", "Services", 5400, 2100, False),
    ("Priority Support", "Subscription", 120, 34, False),
    ("Cloud Backup 1TB", "Subscription", 65, 18, True),
    ("Device Management", "Subscription", 88, 25, False),
]

#                name                region        weight  active
MORE_WAREHOUSES = [
    ("South Hub", "US-South", 1.2, True),
    ("Central Depot", "US-Central", 1.6, True),
]

MORE_PLANS = [
    ("Priority Support Annual", BillingCycle.YEARLY, 1290, True, 60, 15),
    ("Cloud Backup Monthly", BillingCycle.MONTHLY, 65, True, 30, 0),
    ("Device Management Quarterly", BillingCycle.QUARTERLY, 255, False, 120, 8),
]

MORE_PAIRINGS = [
    ("Desktop Workstation", "Ultrawide Monitor 34", 28),
    ("Desktop Workstation", "Mechanical Keyboard", 22),
    ("Ultrawide Monitor 34", "Mechanical Keyboard", 18),
    ("Conference Room Kit", "Staff Training Day", 26),
    ("Network Switch 48p", "Security Audit", 15),
    ("Rugged Tablet 10", "Device Management", 20),
    ("Data Migration", "Priority Support", 24),
    ("Custom Integration", "Priority Support", 19),
]

# number, customer, rep key, status, [(product, qty, discount)]
# Spread across every stage so each pipeline column, filter and dropdown has
# something in it. Assigned to rep2 and rep3, never to rep: Alex Turner's
# discount history is the anomaly baseline and adding to it would move the mean.
VOLUME_QUOTATIONS = [
    (
        "Q-1101",
        "Northwind Traders",
        "rep2",
        QuoteStatus.DRAFT,
        [("Desktop Workstation", 4, 6), ("Ultrawide Monitor 34", 4, 5)],
    ),
    (
        "Q-1102",
        "Contoso Manufacturing",
        "rep2",
        QuoteStatus.DRAFT,
        [("Conference Room Kit", 2, 9), ("Staff Training Day", 1, 4)],
    ),
    (
        "Q-1103",
        "Fabrikam Logistics",
        "rep3",
        QuoteStatus.DRAFT,
        [("Rugged Tablet 10", 12, 8)],
    ),
    (
        "Q-1104",
        "Tailspin Aviation",
        "rep3",
        QuoteStatus.DRAFT,
        [("Network Switch 48p", 3, 7), ("Security Audit", 1, 6)],
    ),
    (
        "Q-1105",
        "Wide World Importers",
        "rep2",
        QuoteStatus.PENDING_APPROVAL,
        [("Data Migration", 1, 18), ("Staff Training Day", 2, 12)],
    ),
    (
        "Q-1106",
        "Litware Consulting",
        "rep3",
        QuoteStatus.PENDING_APPROVAL,
        [("Custom Integration", 1, 22)],
    ),
    (
        "Q-1107",
        "Proseware Health",
        "rep2",
        QuoteStatus.PENDING_APPROVAL,
        [("Security Audit", 2, 16), ("Priority Support", 6, 11)],
    ),
    (
        "Q-1108",
        "Northwind Traders",
        "rep3",
        QuoteStatus.APPROVED,
        [("Mechanical Keyboard", 40, 12), ("Ultrawide Monitor 34", 10, 9)],
    ),
    (
        "Q-1109",
        "Contoso Manufacturing",
        "rep2",
        QuoteStatus.APPROVED,
        [("Desktop Workstation", 8, 11)],
    ),
    (
        "Q-1110",
        "Fabrikam Logistics",
        "rep3",
        QuoteStatus.APPROVED,
        [("Conference Room Kit", 1, 5), ("Data Migration", 1, 8)],
    ),
    (
        "Q-1111",
        "Tailspin Aviation",
        "rep2",
        QuoteStatus.NEGOTIATION,
        [("Network Switch 48p", 6, 13), ("Custom Integration", 1, 9)],
    ),
    (
        "Q-1112",
        "Wide World Importers",
        "rep3",
        QuoteStatus.NEGOTIATION,
        [("Rugged Tablet 10", 20, 14)],
    ),
    (
        "Q-1113",
        "Litware Consulting",
        "rep2",
        QuoteStatus.NEGOTIATION,
        [("Staff Training Day", 3, 10), ("Cloud Backup 1TB", 12, 6)],
    ),
    (
        "Q-1114",
        "Proseware Health",
        "rep3",
        QuoteStatus.CONFIRMED,
        [("Desktop Workstation", 3, 7), ("Priority Support", 3, 5)],
    ),
    (
        "Q-1115",
        "Northwind Traders",
        "rep2",
        QuoteStatus.CONFIRMED,
        [("Security Audit", 1, 4)],
    ),
    (
        "Q-1116",
        "Contoso Manufacturing",
        "rep3",
        QuoteStatus.CONFIRMED,
        [("Conference Room Kit", 4, 8), ("Device Management", 8, 3)],
    ),
    (
        "Q-1117",
        "Fabrikam Logistics",
        "rep2",
        QuoteStatus.CONFIRMED,
        [("Ultrawide Monitor 34", 6, 6)],
    ),
    (
        "Q-1118",
        "Tailspin Aviation",
        "rep3",
        QuoteStatus.CONFIRMED,
        [("Data Migration", 1, 11), ("Cloud Backup 1TB", 24, 7)],
    ),
    (
        "Q-1119",
        "Wide World Importers",
        "rep2",
        QuoteStatus.REJECTED,
        [("Custom Integration", 2, 31)],
    ),
    (
        "Q-1120",
        "Litware Consulting",
        "rep3",
        QuoteStatus.DRAFT,
        [("Mechanical Keyboard", 15, 3), ("Cloud Backup 1TB", 6, 2)],
    ),
]


def seed(session: Session) -> None:
    tiers = {}
    for name, pct in TIERS:
        tier = DiscountTier(name=name, max_discount_pct=pct)
        session.add(tier)
        tiers[name] = tier
    session.flush()

    customers = {}
    for name, tier_name in CUSTOMERS:
        customer = Customer(name=name, tier_id=tiers[tier_name].id)
        session.add(customer)
        customers[name] = customer
    session.flush()

    # Hash once: bcrypt is deliberately slow, and every seeded account shares
    # the same demo password.
    password_hash = security_util_hash_password(PASSWORD)

    for email, full_name, role, customer_name in USERS:
        session.add(
            User(
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role=role,
                customer_id=customers[customer_name].id if customer_name else None,
            )
        )

    for category, pct in CATEGORY_CEILINGS:
        session.add(CategoryCeiling(category=category, max_discount_pct=pct))

    for rule_type, level, pct in THRESHOLDS:
        session.add(RiskThreshold(rule_type=rule_type, level=level, min_excess_pt=pct))

    for level, order, role in APPROVAL_RULES:
        session.add(ApprovalRule(level=level, step_order=order, role=role))

    products = {}
    for name, category, price, cost, promoted in PRODUCTS:
        product = Product(
            name=name,
            category=category,
            unit_price=price,
            cost_price=cost,
            is_promoted=promoted,
            recurring_cycle=(
                BillingCycle.MONTHLY if category == "Subscription" else None
            ),
            is_subscription=category == "Subscription",
            variants=(
                [
                    {
                        "attribute": "Colour",
                        "values": "Silver, Space Grey",
                        "extra_price": 0,
                    },
                    {"attribute": "RAM", "values": "16GB, 32GB", "extra_price": 240},
                ]
                if name == "Laptop Pro 14"
                else None
            ),
        )
        session.add(product)
        products[name] = product
    session.flush()

    warehouses = {}
    for name, region, weight, active in WAREHOUSES:
        warehouse = Warehouse(
            name=name, region=region, shipping_cost_weight=weight, active=active
        )
        session.add(warehouse)
        warehouses[name] = warehouse
    session.flush()

    for warehouse_name, product_name, on_hand, reserved, point, qty in STOCK:
        session.add(
            StockLevel(
                warehouse_id=warehouses[warehouse_name].id,
                product_id=products[product_name].id,
                qty_on_hand=on_hand,
                qty_reserved=reserved,
                reorder_point=point,
                reorder_qty=qty,
            )
        )

    for tier_name, currency, adjustment in PRICE_LISTS:
        session.add(
            PriceList(
                name=f"{tier_name} {currency}",
                tier_id=tiers[tier_name].id,
                currency=currency,
                adjustment_pct=adjustment,
            )
        )

    session.add(
        UpsellRule(
            min_margin_pct=UPSELL_MIN_MARGIN_PCT,
            max_suggestions=UPSELL_MAX_SUGGESTIONS,
        )
    )

    for a, b, rank in PAIRINGS:
        session.add(
            ProductPairing(
                product_a_id=products[a].id,
                product_b_id=products[b].id,
                rank=rank,
            )
        )

    rep = session.query(User).filter_by(email="rep@dealflow360.com").one()

    # Scenario A from risk-engine-and-ml.md 12, and the wireframe's Q-1042.
    # Setup Service at 18% against a 10% ceiling is 8pt over, which must route
    # HIGH on the worst-line path even though it is a small share of the order.
    quotation = Quotation(
        number="Q-1042",
        customer_id=customers["Acme Corp"].id,
        rep_id=rep.id,
        status=QuoteStatus.DRAFT,
    )
    session.add(quotation)
    session.flush()

    for name, qty, discount in [
        ("Laptop Pro 14", 2, 12),
        ("Onsite Setup Service", 1, 18),
        ("Extended Warranty", 1, 10),
    ]:
        product = products[name]
        session.add(
            QuotationLine(
                quotation_id=quotation.id,
                product_id=product.id,
                qty=qty,
                unit_price=product.unit_price,
                cost_price=product.cost_price,
                discount_pct=discount,
            )
        )

    plans = {}
    for name, cycle, price, proration, window, fee in PLANS:
        plan = SubscriptionPlan(
            name=name,
            cycle=cycle,
            price=price,
            proration_enabled=proration,
            refund_window_days=window,
            cancellation_fee_pct=fee,
        )
        session.add(plan)
        plans[name] = plan
    session.flush()

    _seed_health_scenarios(session, products, customers, rep)
    _seed_hybrid_order(session, products, customers, plans, rep)
    _seed_volume(session, tiers, products, customers, plans)

    session.commit()
    logger.info(
        "Seeded %d tiers, %d customers, %d users",
        len(TIERS),
        len(CUSTOMERS),
        len(USERS),
    )
    logger.info(
        "Seeded %d products, %d category ceilings, and quotation Q-1042",
        len(PRODUCTS),
        len(CATEGORY_CEILINGS),
    )
    logger.info("Seeded %d warehouses and %d stock rows", len(WAREHOUSES), len(STOCK))


def _seed_health_scenarios(session, products, customers, rep) -> None:
    """Quotations that trigger each Deal Health flag deliberately.

    A demo must not depend on a detector happening to fire. Each of these exists
    to make one flag appear, so the dashboard is never empty on stage.
    """
    now = datetime.now(UTC)

    # Stalled: untouched for well past the 7-day window.
    stalled = Quotation(
        number="Q-1039",
        customer_id=customers["Beta Industries"].id,
        rep_id=rep.id,
        status=QuoteStatus.NEGOTIATION,
        last_activity_at=now - timedelta(days=12),
    )
    session.add(stalled)
    session.flush()
    session.add(
        QuotationLine(
            quotation_id=stalled.id,
            product_id=products["Laptop Pro 14"].id,
            qty=4,
            unit_price=products["Laptop Pro 14"].unit_price,
            cost_price=products["Laptop Pro 14"].cost_price,
            discount_pct=8,
        )
    )

    # Delivery slippage: expected three days after what was promised.
    slipping = Quotation(
        number="Q-1041",
        customer_id=customers["Delta LLC"].id,
        rep_id=rep.id,
        status=QuoteStatus.APPROVED,
        promised_delivery_date=date.today() + timedelta(days=7),
        expected_delivery_date=date.today() + timedelta(days=10),
    )
    session.add(slipping)
    session.flush()
    session.add(
        QuotationLine(
            quotation_id=slipping.id,
            product_id=products["Docking Station"].id,
            qty=6,
            unit_price=products["Docking Station"].unit_price,
            cost_price=products["Docking Station"].cost_price,
            discount_pct=7,
        )
    )

    # Backorder: eight laptops against five available across the active
    # warehouses, so the split cannot complete. The wireframe shows exactly this
    # state on the fulfillment list.
    backordered = Quotation(
        number="Q-1030",
        customer_id=customers["Delta LLC"].id,
        rep_id=rep.id,
        status=QuoteStatus.APPROVED,
    )
    session.add(backordered)
    session.flush()
    session.add(
        QuotationLine(
            quotation_id=backordered.id,
            product_id=products["Laptop Pro 14"].id,
            qty=8,
            unit_price=products["Laptop Pro 14"].unit_price,
            cost_price=products["Laptop Pro 14"].cost_price,
            discount_pct=6,
        )
    )

    # Discount anomaly: this rep normally discounts around 7-9%, so a 30% quote
    # is well outside their own pattern. Needs MIN_HISTORY past quotes to score.
    #
    # Dated back across the year rather than all stamped today. That is what a
    # baseline actually looks like, and it gives the reporting period filter
    # something real to narrow: 30 days excludes all six, 90 days keeps three.
    history_ages = [21, 45, 80, 140, 220, 300]
    for i, (pct, age) in enumerate(
        zip([7, 8, 9, 8, 7, 8], history_ages, strict=False), start=1
    ):
        past = Quotation(
            number=f"Q-10{10 + i}",
            customer_id=customers["Acme Corp"].id,
            rep_id=rep.id,
            status=QuoteStatus.CONFIRMED,
            created_at=now - timedelta(days=age),
            last_activity_at=now - timedelta(days=age),
        )
        session.add(past)
        session.flush()
        session.add(
            QuotationLine(
                quotation_id=past.id,
                product_id=products["Laptop Pro 14"].id,
                qty=2,
                unit_price=products["Laptop Pro 14"].unit_price,
                cost_price=products["Laptop Pro 14"].cost_price,
                discount_pct=pct,
            )
        )

    outlier = Quotation(
        number="Q-1044",
        customer_id=customers["Delta LLC"].id,
        rep_id=rep.id,
        status=QuoteStatus.DRAFT,
    )
    session.add(outlier)
    session.flush()
    session.add(
        QuotationLine(
            quotation_id=outlier.id,
            product_id=products["Laptop Pro 14"].id,
            qty=3,
            unit_price=products["Laptop Pro 14"].unit_price,
            cost_price=products["Laptop Pro 14"].cost_price,
            discount_pct=30,
        )
    )


def _seed_hybrid_order(session, products, customers, plans, rep) -> None:
    """One order carrying both a one-time product and a recurring plan.

    PS section 9 step 6 checks these are billed correctly and separately, so the
    demo needs an order that actually mixes them.
    """
    order = Quotation(
        number="Q-1050",
        customer_id=customers["Acme Corp"].id,
        rep_id=rep.id,
        status=QuoteStatus.CONFIRMED,
        fulfillment_status=FulfilStatus.SPLIT_ACCEPTED,
    )
    session.add(order)
    session.flush()

    for name, qty, line_type in [
        ("Laptop Pro 14", 2, LineType.ONE_TIME),
        ("Onsite Setup Service", 1, LineType.ONE_TIME),
        ("Care Plan 2yr", 1, LineType.RECURRING),
    ]:
        product = products[name]
        session.add(
            QuotationLine(
                quotation_id=order.id,
                product_id=product.id,
                qty=qty,
                unit_price=product.unit_price,
                cost_price=product.cost_price,
                discount_pct=5,
                line_type=line_type,
            )
        )

    plan = plans["Care Plan 2yr"]
    subscription = Subscription(
        customer_id=customers["Acme Corp"].id,
        quotation_id=order.id,
        plan_id=plan.id,
        qty=1,
        unit_price=plan.price,
        started_at=date.today() - timedelta(days=15),
        next_bill_date=date.today() + timedelta(days=15),
    )
    session.add(subscription)
    session.flush()

    # The forward schedule PS 4-B7 asks the billing screen to show. Written at
    # seed time rather than generated on read, so what the customer is committing
    # to across the term is a stored fact the invoice run can bill against.
    due = subscription.next_bill_date
    for _ in range(6):
        db_add_schedule(
            session,
            subscription_id=subscription.id,
            due_date=due,
            amount=Decimal(str(plan.price)) * subscription.qty,
        )
        due = billing_util_next_bill_date(plan.cycle, due)

    # The one-time invoice for this order. Recurring is billed separately from
    # the schedule, never on the same document.
    session.flush()
    one_time_total = sum(
        line.unit_price * line.qty * Decimal("0.95")
        for line in order.lines
        if line.line_type == LineType.ONE_TIME
    )
    db_create_invoice(
        session,
        quotation_id=order.id,
        customer_id=customers["Acme Corp"].id,
        amount=one_time_total,
        line_type=LineType.ONE_TIME,
        due_date=date.today() + timedelta(days=30),
        lines=[
            {
                "description": f"{line.product.name} x{line.qty}",
                "qty": line.qty,
                "amount": line.unit_price * line.qty * Decimal("0.95"),
                "is_recurring": False,
            }
            for line in order.lines
            if line.line_type == LineType.ONE_TIME
        ],
        sent=True,
    )


def main() -> None:
    session = SessionLocal()
    try:
        seed(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()


def _seed_volume(session: Session, tiers, products, customers, plans) -> None:
    """Depth, so every list, dropdown and pipeline column has real content.

    Kept separate from the fixtures above because those are load-bearing: the
    tests and the demo script depend on Q-1042 and the health scenarios being
    exactly what they are. Everything here is additive.
    """
    for name, tier_name in MORE_CUSTOMERS:
        customer = Customer(name=name, tier_id=tiers[tier_name].id)
        session.add(customer)
        customers[name] = customer

    for name, category, price, cost, promoted in MORE_PRODUCTS:
        product = Product(
            name=name,
            category=category,
            unit_price=price,
            cost_price=cost,
            is_promoted=promoted,
            recurring_cycle=(
                BillingCycle.MONTHLY if category == "Subscription" else None
            ),
            is_subscription=category == "Subscription",
            qty_on_hand=120,
        )
        session.add(product)
        products[name] = product

    warehouses = {w.name: w for w in session.scalars(select(Warehouse)).all()}
    for name, region, weight, active in MORE_WAREHOUSES:
        warehouse = Warehouse(
            name=name, region=region, shipping_cost_weight=weight, active=active
        )
        session.add(warehouse)
        warehouses[name] = warehouse

    for name, cycle, price, proration, window, fee in MORE_PLANS:
        plan = SubscriptionPlan(
            name=name,
            cycle=cycle,
            price=price,
            proration_enabled=proration,
            refund_window_days=window,
            cancellation_fee_pct=fee,
        )
        session.add(plan)
        plans[name] = plan
    session.flush()

    # Stock for the new products only. Laptop Pro 14 is deliberately untouched:
    # its scarcity at Main Warehouse is what forces Q-1042 to split across two
    # warehouses, and stocking it anywhere else would quietly break that.
    stocked = [name for name, cat, *_ in MORE_PRODUCTS if cat != "Subscription"]
    for w_index, warehouse_name in enumerate(
        ["Main Warehouse", "East Depot", "South Hub", "Central Depot"]
    ):
        for p_index, product_name in enumerate(stocked):
            on_hand = 30 + (p_index * 17 + w_index * 23) % 90
            reserved = (p_index * 7 + w_index * 5) % 12
            point = 15 if p_index % 3 else 0
            session.add(
                StockLevel(
                    warehouse_id=warehouses[warehouse_name].id,
                    product_id=products[product_name].id,
                    qty_on_hand=on_hand,
                    qty_reserved=reserved,
                    reorder_point=point,
                    reorder_qty=point * 3,
                )
            )

    for a, b, rank in MORE_PAIRINGS:
        session.add(
            ProductPairing(
                product_a_id=products[a].id,
                product_b_id=products[b].id,
                rank=rank,
            )
        )
    session.flush()

    reps = {
        "rep2": session.scalar(
            select(User).where(User.email == "rep2@dealflow360.com")
        ),
        "rep3": session.scalar(
            select(User).where(User.email == "rep3@dealflow360.com")
        ),
    }

    # Spread the created dates across the last four months so the reporting
    # period filter has something to narrow, and so the pipeline does not look
    # like every deal was opened on the same afternoon.
    now = datetime.now(UTC)
    built = []
    for index, (number, customer, rep_key, status, lines) in enumerate(
        VOLUME_QUOTATIONS
    ):
        age = 3 + index * 6
        quotation = Quotation(
            number=number,
            customer_id=customers[customer].id,
            rep_id=reps[rep_key].id,
            status=status,
            created_at=now - timedelta(days=age),
            last_activity_at=now - timedelta(days=max(0, age - 2)),
        )
        session.add(quotation)
        session.flush()

        for product_name, qty, discount in lines:
            product = products[product_name]
            session.add(
                QuotationLine(
                    quotation_id=quotation.id,
                    product_id=product.id,
                    qty=qty,
                    unit_price=product.unit_price,
                    cost_price=product.cost_price,
                    discount_pct=discount,
                )
            )
        built.append((quotation, status))
    session.flush()

    # Score every volume quotation through the real engine, and build a real
    # approval chain for the ones sitting in Pending Approval. Seeding that
    # status without the steps behind it would give the approvals queue rows
    # whose detail screen has an empty stepper.
    for quotation, status in built:
        result = pricing_util_score(session, quotation)
        if status == QuoteStatus.PENDING_APPROVAL:
            level = (
                result.risk_level
                if approval_util_needs_approval(result.risk_level)
                else RiskLevel.MEDIUM
            )
            approval_util_build_chain(session, quotation, level)
            record_audit(
                session,
                quotation=quotation,
                user_id=quotation.rep_id,
                action=AuditAction.SUBMIT,
                note="Submitted for approval",
            )
    session.flush()

    _seed_volume_billing(session, customers, plans, built)


def _seed_volume_billing(session: Session, customers, plans, built) -> None:
    """Subscriptions and invoices for the confirmed deals.

    Only confirmed quotations get billed, because billing something that was
    never agreed is exactly the kind of thing this system exists to prevent.
    """
    plan_cycle = [
        plans["Priority Support Annual"],
        plans["Cloud Backup Monthly"],
        plans["Device Management Quarterly"],
        plans["Support SLA"],
    ]
    confirmed = [q for q, status in built if status == QuoteStatus.CONFIRMED]

    for index, quotation in enumerate(confirmed):
        plan = plan_cycle[index % len(plan_cycle)]
        started = date.today() - timedelta(days=20 + index * 11)
        subscription = Subscription(
            customer_id=quotation.customer_id,
            quotation_id=quotation.id,
            plan_id=plan.id,
            qty=1 + index % 4,
            unit_price=plan.price,
            status=SubStatus.CANCELLED if index == 3 else SubStatus.ACTIVE,
            started_at=started,
            next_bill_date=billing_util_next_bill_date(plan.cycle, started),
            cancelled_at=date.today() - timedelta(days=2) if index == 3 else None,
        )
        session.add(subscription)
        session.flush()

        due = subscription.next_bill_date
        for _ in range(4):
            db_add_schedule(
                session,
                subscription_id=subscription.id,
                due_date=due,
                amount=Decimal(str(plan.price)) * subscription.qty,
            )
            due = billing_util_next_bill_date(plan.cycle, due)

    # Invoices across every status the screen can show, so the filters and the
    # status pills are not all one colour.
    for index, quotation in enumerate(confirmed):
        net = sum(
            Decimal(str(line.unit_price))
            * line.qty
            * (Decimal("100") - Decimal(str(line.discount_pct)))
            / Decimal("100")
            for line in quotation.lines
        )
        invoice = db_create_invoice(
            session,
            quotation_id=quotation.id,
            customer_id=quotation.customer_id,
            amount=net.quantize(Decimal("0.01")),
            line_type=LineType.ONE_TIME,
            due_date=date.today() + timedelta(days=14 + index * 7),
            lines=[
                {
                    "description": f"{line.product.name} x{line.qty}",
                    "qty": line.qty,
                    "amount": Decimal(str(line.unit_price))
                    * line.qty
                    * (Decimal("100") - Decimal(str(line.discount_pct)))
                    / Decimal("100"),
                    "is_recurring": False,
                }
                for line in quotation.lines
            ],
            sent=True,
        )
        # One paid, one part-paid, the rest outstanding.
        if index == 0:
            invoice.paid_amount = invoice.amount
            invoice.status = InvoiceStatus.PAID
        elif index == 1:
            invoice.paid_amount = (invoice.amount / 2).quantize(Decimal("0.01"))
            invoice.status = InvoiceStatus.PARTIAL

    # One credit note, so the document type is not uniformly "invoice".
    if confirmed:
        db_create_invoice(
            session,
            quotation_id=confirmed[-1].id,
            customer_id=confirmed[-1].customer_id,
            amount=Decimal("-240.00"),
            doc_type=DocType.CREDIT_NOTE,
            line_type=LineType.RECURRING,
            reason="Goodwill credit, delayed delivery",
            sent=True,
        )
    session.flush()
