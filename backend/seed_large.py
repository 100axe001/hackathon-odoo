"""Large demo dataset, for stress-testing lists, filters, sorting and paging.

This is a bigger sibling of `seed.py`, not a replacement for it. `seed.py` is
the demo: it carries Q-1042, the Deal Health scenarios and the stock arrangement
the tests depend on. This script carries volume instead - forty distinct
companies, sixty products and eighty quotations spread across the past year, so
every screen has enough rows to page through and every filter has something to
narrow.

Not idempotent by accumulation: it **wipes every table first** (via
`wipe_data.wipe`) and then loads, so running it twice leaves the same dataset
rather than two copies. The schema is created if it is missing, so it runs
standalone against an empty database:

    ./.venv/bin/python seed_large.py

To go back to the normal demo afterwards, run `./.venv/bin/python reset_db.py`.

Row counts it produces - 793 rows in total, and it prints this same table on
exit so the claim stays checkable:

    customers              40      products               60
    users                  16      warehouses              8
    discount_tiers          3      stock_levels          149
    price_lists             3      product_pairings       20
    category_ceilings       3      subscription_plans      8
    risk_thresholds         4      subscriptions          25
    approval_rules          3      billing_schedules      99
    upsell_rules            1      invoices               30
    quotations             80      invoice_lines          41
    quotation_lines       159      approval_steps         27
                                   audit_logs             14

The 80 quotations cover all six QuoteStatus values and all three risk levels,
touch all 40 customers and all 5 reps, and their created dates run back roughly
eleven months. The 30 documents mix Paid, Partial and Unpaid across invoices and
credit notes, one-time and recurring.

Deal Health flags, fulfillment allocations and negotiation messages are left
empty on purpose, exactly as `seed.py` leaves them: those are produced by the
detector and the split engine at read time, not seeded.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.models  # noqa: F401  registers every model on Base.metadata
from app.database.billing import db_add_schedule, db_create_invoice
from app.database.connection import Base, SessionLocal, engine
from app.logging.setup_logging import get_logger, setup_logging
from app.models.billing import Invoice, Subscription, SubscriptionPlan
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
from wipe_data import count_rows, print_counts, wipe

logger = get_logger(__name__)

PASSWORD = "dealflow123"

TIERS = [("Bronze", 5), ("Silver", 10), ("Gold", 15)]

# Same governance configuration as seed.py. The volume here is only meaningful
# if it is scored by the rules the demo actually runs on.
CATEGORY_CEILINGS = [("Hardware", 15), ("Services", 10), ("Subscription", 10)]

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

# tier, currency, adjustment off list.
PRICE_LISTS = [
    ("Bronze", "USD", 0),
    ("Silver", "USD", 3),
    ("Gold", "USD", 7),
]

UPSELL_MIN_MARGIN_PCT = 40
UPSELL_MAX_SUGGESTIONS = 5

# Forty accounts, deliberately drawn from unrelated industries with no shared
# stems: a stress-test list is useless if half the rows read as the same company
# and a reviewer skims past them. name, tier.
CUSTOMERS = [
    ("Brightwater Logistics", "Gold"),
    ("Kestrel Aerospace", "Gold"),
    ("Ironvale Steelworks", "Gold"),
    ("Maplecrest Dental Group", "Silver"),
    ("Solstice Renewables", "Gold"),
    ("Halloran Freight Lines", "Silver"),
    ("Cobalt Ridge Mining", "Gold"),
    ("Thornbury Publishing", "Bronze"),
    ("Verdant Agritech", "Silver"),
    ("Pinewood Hospitality", "Bronze"),
    ("Quarry Lane Aggregates", "Bronze"),
    ("Silverline Diagnostics", "Gold"),
    ("Harbourpoint Marine", "Silver"),
    ("Redstone Legal Partners", "Bronze"),
    ("Juniper Biosciences", "Gold"),
    ("Falconbridge Insurance", "Silver"),
    ("Willowbrook Textiles", "Bronze"),
    ("Granite Peak Outfitters", "Silver"),
    ("Lumen Optics", "Gold"),
    ("Ferrous Bay Shipyard", "Silver"),
    ("Oakhurst Property Group", "Bronze"),
    ("Nightingale Home Care", "Silver"),
    ("Copperfield Brewing", "Bronze"),
    ("Sable Creek Winery", "Bronze"),
    ("Trilith Semiconductor", "Gold"),
    ("Marlowe Architects", "Bronze"),
    ("Kingsford Automotive", "Silver"),
    ("Bluepeak Analytics", "Gold"),
    ("Aurora Grain Cooperative", "Silver"),
    ("Dunmore Pharmaceuticals", "Gold"),
    ("Whitfield Security Services", "Bronze"),
    ("Emberline Ceramics", "Bronze"),
    ("Northgate Rail Systems", "Gold"),
    ("Palisade Water Utilities", "Silver"),
    ("Vantage Point Media", "Bronze"),
    ("Crestmark Financial", "Gold"),
    ("Hollowell Instruments", "Silver"),
    ("Bramblewood Foods", "Bronze"),
    ("Zenith Turbine Works", "Gold"),
    ("Larkspur Interiors", "Silver"),
]

# email, full name, role, customer for a portal login. Real-looking domains on
# purpose: EmailStr rejects RFC 2606 reserved TLDs such as .test.
USERS = [
    ("hbennett@dealflow360.com", "Harriet Bennett", UserRole.SALES_REP, None),
    ("dokonkwo@dealflow360.com", "Daniel Okonkwo", UserRole.SALES_REP, None),
    ("lmarchetti@dealflow360.com", "Lucia Marchetti", UserRole.SALES_REP, None),
    ("tnakamura@dealflow360.com", "Toshiro Nakamura", UserRole.SALES_REP, None),
    ("erasmussen@dealflow360.com", "Elin Rasmussen", UserRole.SALES_REP, None),
    ("gvasquez@dealflow360.com", "Gabriel Vasquez", UserRole.SALES_MANAGER, None),
    ("nadeyemi@dealflow360.com", "Ngozi Adeyemi", UserRole.SALES_MANAGER, None),
    ("pkowalski@dealflow360.com", "Piotr Kowalski", UserRole.SALES_MANAGER, None),
    ("aferreira@dealflow360.com", "Ana Ferreira", UserRole.FINANCE, None),
    ("mhaddad@dealflow360.com", "Mariam Haddad", UserRole.FINANCE, None),
    ("rlindqvist@dealflow360.com", "Rasmus Lindqvist", UserRole.ADMIN, None),
    (
        "procurement@brightwaterlogistics.com",
        "Cora Ainsworth",
        UserRole.CUSTOMER,
        "Brightwater Logistics",
    ),
    (
        "buying@kestrelaerospace.com",
        "Marcus Delahaye",
        UserRole.CUSTOMER,
        "Kestrel Aerospace",
    ),
    (
        "accounts@juniperbiosciences.com",
        "Fenella Adeyinka",
        UserRole.CUSTOMER,
        "Juniper Biosciences",
    ),
    (
        "it@trilithsemiconductor.com",
        "Anya Petrova",
        UserRole.CUSTOMER,
        "Trilith Semiconductor",
    ),
    (
        "ops@crestmarkfinancial.com",
        "Bernard Nkemdirim",
        UserRole.CUSTOMER,
        "Crestmark Financial",
    ),
]

# Sixty catalogue lines: 28 Hardware, 16 Services, 16 Subscription. Product
# names are as distinct as the company names and for the same reason - a
# quotation builder dropdown of near-identical entries cannot be tested.
#                name                          category    price  cost  promoted
PRODUCTS = [
    ("Titan X9 Workstation", "Hardware", 2450, 1580, False),
    ("Meridian 4K Desk Display", "Hardware", 620, 355, True),
    ("Halyard Rugged Laptop", "Hardware", 1980, 1290, False),
    ("Vector Mechanical Keyboard", "Hardware", 165, 68, False),
    ("Orbit Wireless Mouse", "Hardware", 72, 24, False),
    ("Cascade Docking Hub", "Hardware", 340, 195, True),
    ("Beacon 48-Port Switch", "Hardware", 1120, 700, False),
    ("Sentry Firewall Appliance", "Hardware", 3400, 2150, False),
    ("Pinnacle Rack Server", "Hardware", 6800, 4400, False),
    ("Stratus NAS 40TB", "Hardware", 4250, 2680, True),
    ("Nimbus Wireless Access Point", "Hardware", 410, 230, False),
    ("Forge Label Printer", "Hardware", 890, 520, False),
    ("Quarry Barcode Scanner", "Hardware", 275, 118, False),
    ("Anvil Industrial Tablet", "Hardware", 1150, 745, True),
    ("Lantern Conference Camera", "Hardware", 980, 560, False),
    ("Chorus Ceiling Microphone", "Hardware", 540, 300, False),
    ("Ridgeline UPS 3000VA", "Hardware", 1480, 940, False),
    ("Copperhead Cable Kit", "Hardware", 95, 32, False),
    ("Summit Standing Desk Frame", "Hardware", 720, 410, False),
    ("Ledger POS Terminal", "Hardware", 1340, 830, False),
    ("Aperture Document Scanner", "Hardware", 1050, 620, False),
    ("Kiln 3D Printer Pro", "Hardware", 5600, 3600, True),
    ("Tundra Cold Storage Sensor", "Hardware", 310, 140, False),
    ("Compass GPS Fleet Tracker", "Hardware", 230, 98, False),
    ("Bastion Door Controller", "Hardware", 760, 445, False),
    ("Prism Video Wall Panel", "Hardware", 3900, 2500, False),
    ("Harbor Thin Client", "Hardware", 480, 265, False),
    ("Trellis Cable Management Rack", "Hardware", 640, 380, False),
    ("Data Centre Migration", "Services", 12500, 4900, False),
    ("Network Readiness Audit", "Services", 3800, 1420, True),
    ("Onsite Installation Day", "Services", 950, 340, False),
    ("Endpoint Rollout Programme", "Services", 7400, 2900, False),
    ("Disaster Recovery Rehearsal", "Services", 4600, 1750, False),
    ("Compliance Gap Assessment", "Services", 5200, 1980, True),
    ("Custom API Integration", "Services", 9800, 3850, False),
    ("Staff Enablement Workshop", "Services", 2100, 780, False),
    ("Cabling and Fit-Out", "Services", 6300, 2450, False),
    ("Legacy Data Extraction", "Services", 8100, 3150, False),
    ("Penetration Test Engagement", "Services", 7900, 2980, True),
    ("Quarterly Health Review", "Services", 1800, 640, False),
    ("Executive Briefing Session", "Services", 1250, 430, False),
    ("Warehouse Survey Visit", "Services", 1600, 590, False),
    ("Firmware Hardening Service", "Services", 3300, 1240, False),
    ("Emergency Callout Cover", "Services", 2400, 880, False),
    ("Sentinel Threat Monitoring", "Subscription", 240, 68, True),
    ("Vaultkeeper Cloud Backup", "Subscription", 130, 36, False),
    ("Atlas Device Management", "Subscription", 95, 27, False),
    ("Pulse Uptime Monitoring", "Subscription", 78, 21, False),
    ("Ledger Expense Sync", "Subscription", 145, 41, False),
    ("Beacon Analytics Suite", "Subscription", 320, 92, True),
    ("Courier Route Optimiser", "Subscription", 265, 74, False),
    ("Harbour Asset Registry", "Subscription", 110, 31, False),
    ("Signal Helpdesk Seats", "Subscription", 58, 16, False),
    ("Quarry Fleet Telemetry", "Subscription", 185, 52, False),
    ("Lantern Meeting Rooms", "Subscription", 88, 25, False),
    ("Prism Digital Signage", "Subscription", 125, 35, False),
    ("Trellis Patch Automation", "Subscription", 210, 60, True),
    ("Compass Field Service App", "Subscription", 160, 45, False),
    ("Kiln Print Fleet Care", "Subscription", 99, 28, False),
    ("Bastion Access Control Cloud", "Subscription", 275, 78, False),
]

# Screen 17 reveals the variant panel per product, so a couple of rows carry one
# rather than leaving that panel empty everywhere.
VARIANTS = {
    "Titan X9 Workstation": [
        {"attribute": "RAM", "values": "32GB, 64GB, 128GB", "extra_price": 480},
        {"attribute": "GPU", "values": "Integrated, Discrete", "extra_price": 950},
    ],
    "Halyard Rugged Laptop": [
        {"attribute": "Screen", "values": "14in, 16in", "extra_price": 160},
        {"attribute": "Warranty", "values": "1yr, 3yr", "extra_price": 220},
    ],
}

# name, region, shipping cost weight, active. The weight is a Numeric column, so
# it is carried as a string and converted rather than sitting in a float.
WAREHOUSES = [
    ("Portland Distribution Centre", "US-West", "1.00", True),
    ("Newark Cross-Dock", "US-East", "1.35", True),
    ("Savannah Port Depot", "US-South", "1.20", True),
    ("Kansas City Rail Yard", "US-Central", "1.50", True),
    ("Phoenix Desert Annex", "US-Southwest", "1.65", True),
    ("Toronto Bonded Store", "CA-East", "1.90", True),
    ("Rotterdam Transit Hub", "EU-West", "2.30", True),
    ("Reno Overflow Store", "US-West", "1.10", False),
]

# name, cycle, price, proration, refund window days, cancellation fee pct. Every
# BillingCycle value appears so the proration maths is exercised on all four.
PLANS = [
    ("Sentinel Threat Monitoring", BillingCycle.MONTHLY, 240, True, 365, 0),
    ("Vaultkeeper Cloud Backup", BillingCycle.MONTHLY, 130, True, 180, 5),
    ("Atlas Device Management", BillingCycle.QUARTERLY, 285, True, 120, 8),
    ("Beacon Analytics Suite", BillingCycle.YEARLY, 3450, True, 60, 15),
    ("Pulse Uptime Monitoring", BillingCycle.MONTHLY, 78, False, 30, 0),
    ("Courier Route Optimiser", BillingCycle.QUARTERLY, 780, True, 90, 10),
    ("Signal Helpdesk Seats", BillingCycle.WEEKLY, 15, True, 14, 0),
    ("Bastion Access Control Cloud", BillingCycle.YEARLY, 2970, False, 45, 12),
]

# Seeded co-purchase pairs, highest rank first - the same arrangement seed.py
# uses, widened so the upsell panel has a suggestion on most quotations.
PAIRINGS = [
    ("Titan X9 Workstation", "Meridian 4K Desk Display", 32),
    ("Titan X9 Workstation", "Vector Mechanical Keyboard", 27),
    ("Titan X9 Workstation", "Sentinel Threat Monitoring", 14),
    ("Halyard Rugged Laptop", "Cascade Docking Hub", 30),
    ("Halyard Rugged Laptop", "Atlas Device Management", 21),
    ("Meridian 4K Desk Display", "Summit Standing Desk Frame", 18),
    ("Beacon 48-Port Switch", "Network Readiness Audit", 24),
    ("Beacon 48-Port Switch", "Copperhead Cable Kit", 19),
    ("Sentry Firewall Appliance", "Penetration Test Engagement", 29),
    ("Pinnacle Rack Server", "Disaster Recovery Rehearsal", 26),
    ("Pinnacle Rack Server", "Ridgeline UPS 3000VA", 23),
    ("Stratus NAS 40TB", "Vaultkeeper Cloud Backup", 31),
    ("Lantern Conference Camera", "Chorus Ceiling Microphone", 28),
    ("Lantern Conference Camera", "Lantern Meeting Rooms", 17),
    ("Anvil Industrial Tablet", "Compass Field Service App", 22),
    ("Compass GPS Fleet Tracker", "Quarry Fleet Telemetry", 25),
    ("Bastion Door Controller", "Bastion Access Control Cloud", 20),
    ("Prism Video Wall Panel", "Prism Digital Signage", 16),
    ("Kiln 3D Printer Pro", "Kiln Print Fleet Care", 15),
    ("Data Centre Migration", "Beacon Analytics Suite", 13),
]

# status, how many, discount band. The bands are what make each column of the
# pipeline believable: drafts and confirmed deals sit inside policy, whereas the
# rejected ones are far enough outside it that the engine routes them HIGH.
QUOTATION_MIX = [
    (QuoteStatus.DRAFT, 18, 2, 9),
    (QuoteStatus.PENDING_APPROVAL, 14, 11, 24),
    (QuoteStatus.APPROVED, 13, 8, 16),
    (QuoteStatus.NEGOTIATION, 11, 10, 20),
    (QuoteStatus.CONFIRMED, 16, 3, 12),
    (QuoteStatus.REJECTED, 8, 22, 38),
]

QUOTATION_COUNT = sum(count for _, count, _, _ in QUOTATION_MIX)

# Coprime with QUOTATION_COUNT, so stepping by it visits every quotation exactly
# once. That interleaves the statuses instead of leaving the pipeline sorted by
# stage, which would make the date spread below meaningless.
_STATUS_STRIDE = 7

SUBSCRIPTION_COUNT = 25

# One in seven paused and one in nine cancelled, so the subscription filters are
# not looking at a single status.
SUB_STATUS_CYCLE = [
    SubStatus.ACTIVE,
    SubStatus.ACTIVE,
    SubStatus.ACTIVE,
    SubStatus.PAUSED,
    SubStatus.ACTIVE,
    SubStatus.ACTIVE,
    SubStatus.CANCELLED,
]

RECURRING_INVOICE_COUNT = 10
CREDIT_NOTE_COUNT = 4

PAYMENT_METHODS = ["Bank Transfer", "Credit Card", "Cheque"]


def _next_due_on_or_after(cycle: str, started: date, floor: date) -> date:
    """Roll a billing date forward until it stops being in the past.

    A subscription that began ten months ago has already been billed nine times;
    the screen wants the bill that is coming, not the one it opened with.
    """
    due = billing_util_next_bill_date(cycle, started)
    while due < floor:
        due = billing_util_next_bill_date(cycle, due)
    return due


def _seed_governance(session: Session) -> dict[str, DiscountTier]:
    """Tiers, ceilings, thresholds, routing rules and price lists."""
    tiers: dict[str, DiscountTier] = {}
    for name, pct in TIERS:
        tier = DiscountTier(name=name, max_discount_pct=pct)
        session.add(tier)
        tiers[name] = tier
    session.flush()

    for category, pct in CATEGORY_CEILINGS:
        session.add(CategoryCeiling(category=category, max_discount_pct=pct))

    for rule_type, level, pct in THRESHOLDS:
        session.add(RiskThreshold(rule_type=rule_type, level=level, min_excess_pt=pct))

    for level, order, role in APPROVAL_RULES:
        session.add(ApprovalRule(level=level, step_order=order, role=role))

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
    return tiers


def _seed_people(
    session: Session, tiers: dict[str, DiscountTier]
) -> dict[str, Customer]:
    """Customers, then the accounts that log in against them."""
    customers: dict[str, Customer] = {}
    now = datetime.now(UTC)
    for index, (name, tier_name) in enumerate(CUSTOMERS):
        # Accounts opened across the year, so the customer list sorts by
        # something other than insertion order.
        customer = Customer(
            name=name,
            tier_id=tiers[tier_name].id,
            created_at=now - timedelta(days=350 - index * 8),
        )
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
    session.flush()
    return customers


def _seed_catalogue(session: Session) -> dict[str, Product]:
    products: dict[str, Product] = {}
    for index, (name, category, price, cost, promoted) in enumerate(PRODUCTS):
        product = Product(
            name=name,
            category=category,
            unit_price=price,
            cost_price=cost,
            is_promoted=promoted,
            is_subscription=category == "Subscription",
            recurring_cycle=(
                BillingCycle.MONTHLY if category == "Subscription" else None
            ),
            tax_pct=[0, 5, 12, 18][index % 4],
            qty_on_hand=40 + (index * 13) % 260,
            variants=VARIANTS.get(name),
        )
        session.add(product)
        products[name] = product
    session.flush()
    return products


def _seed_fulfillment(session: Session, products: dict[str, Product]) -> None:
    """Warehouses and the stock rows behind the split engine.

    Only physical goods are stocked - a service or a subscription has no depot,
    and giving it one would put nonsense rows in front of the split logic.
    """
    warehouses: list[Warehouse] = []
    for name, region, weight, active in WAREHOUSES:
        warehouse = Warehouse(
            name=name,
            region=region,
            shipping_cost_weight=Decimal(weight),
            active=active,
        )
        session.add(warehouse)
        warehouses.append(warehouse)
    session.flush()

    hardware = [p for p in products.values() if p.category == "Hardware"]
    for w_index, warehouse in enumerate(warehouses):
        for p_index, product in enumerate(hardware):
            # A gap in every third slot, so no warehouse carries the whole
            # catalogue and the split engine has to reach across sites.
            if (w_index + p_index) % 3 == 0:
                continue
            on_hand = 12 + (p_index * 17 + w_index * 29) % 140
            session.add(
                StockLevel(
                    warehouse_id=warehouse.id,
                    product_id=product.id,
                    qty_on_hand=on_hand,
                    qty_reserved=(p_index * 7 + w_index * 5) % 14,
                    reorder_point=[0, 15, 25, 40][p_index % 4],
                    reorder_qty=[0, 45, 75, 120][p_index % 4],
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
    session.flush()


def _seed_plans(session: Session) -> list[SubscriptionPlan]:
    plans: list[SubscriptionPlan] = []
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
        plans.append(plan)
    session.flush()
    return plans


def _seed_quotations(
    session: Session,
    customers: dict[str, Customer],
    products: dict[str, Product],
) -> list[tuple[Quotation, str]]:
    """Eighty quotations, scored by the real engine.

    Composed rather than written out as eighty literal tuples: what matters for
    a stress test is the spread - every status, every rep, every customer, a
    year of dates - and a table that long would hide it rather than show it.
    """
    reps = list(
        session.scalars(
            select(User).where(User.role == UserRole.SALES_REP).order_by(User.id)
        ).all()
    )
    customer_list = list(customers.values())
    product_list = list(products.values())

    plan = [
        (status, low, high)
        for status, count, low, high in QUOTATION_MIX
        for _ in range(count)
    ]
    ordered = [plan[(i * _STATUS_STRIDE) % QUOTATION_COUNT] for i in range(len(plan))]

    now = datetime.now(UTC)
    built: list[tuple[Quotation, str]] = []

    for index, (status, low, high) in enumerate(ordered):
        age = 8 + index * 4
        created = now - timedelta(days=age)
        quotation = Quotation(
            number=f"QL-{2001 + index}",
            customer_id=customer_list[(index * 3) % len(customer_list)].id,
            rep_id=reps[index % len(reps)].id,
            status=status,
            created_at=created,
            last_activity_at=created + timedelta(days=min(age, 2 + index % 9)),
            submitted_at=(created if status != QuoteStatus.DRAFT else None),
            promised_delivery_date=(
                created.date() + timedelta(days=21)
                if status in (QuoteStatus.APPROVED, QuoteStatus.CONFIRMED)
                else None
            ),
            expected_delivery_date=(
                # Every fourth order runs late, which is what the slippage
                # detector is looking for.
                created.date() + timedelta(days=21 + (5 if index % 4 == 0 else -1))
                if status in (QuoteStatus.APPROVED, QuoteStatus.CONFIRMED)
                else None
            ),
        )
        session.add(quotation)
        session.flush()

        for k in range(1 + index % 3):
            product = product_list[(index * 7 + k * 13) % len(product_list)]
            session.add(
                QuotationLine(
                    quotation_id=quotation.id,
                    product_id=product.id,
                    qty=1 + (index + k) % 12,
                    unit_price=product.unit_price,
                    cost_price=product.cost_price,
                    discount_pct=low + (index * 5 + k * 3) % (high - low + 1),
                    line_type=(
                        LineType.RECURRING
                        if product.is_subscription
                        else LineType.ONE_TIME
                    ),
                )
            )
        built.append((quotation, status))
    session.flush()

    # Score through the real engine, and give the pending ones a real chain:
    # seeding Pending Approval without the steps behind it leaves the approvals
    # queue full of rows whose detail screen has an empty stepper.
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
    return built


def _seed_subscriptions(
    session: Session,
    plans: list[SubscriptionPlan],
    built: list[tuple[Quotation, str]],
) -> list[Subscription]:
    """Recurring contracts, only ever off a confirmed order.

    Billing something that was never agreed is exactly what this system exists
    to prevent, so the confirmed deals are cycled over rather than reaching for
    a quotation that is still in flight.
    """
    confirmed = [q for q, status in built if status == QuoteStatus.CONFIRMED]
    today = date.today()
    subscriptions: list[Subscription] = []

    for index in range(SUBSCRIPTION_COUNT):
        quotation = confirmed[index % len(confirmed)]
        plan = plans[index % len(plans)]
        started = today - timedelta(days=15 + index * 13)
        status = SUB_STATUS_CYCLE[index % len(SUB_STATUS_CYCLE)]
        subscription = Subscription(
            customer_id=quotation.customer_id,
            quotation_id=quotation.id,
            plan_id=plan.id,
            qty=1 + index % 5,
            unit_price=plan.price,
            status=status,
            started_at=started,
            next_bill_date=_next_due_on_or_after(plan.cycle, started, today),
            cancelled_at=(
                today - timedelta(days=3 + index)
                if status == SubStatus.CANCELLED
                else None
            ),
        )
        session.add(subscription)
        session.flush()

        due = subscription.next_bill_date
        for _ in range(3 + index % 3):
            db_add_schedule(
                session,
                subscription_id=subscription.id,
                due_date=due,
                amount=Decimal(str(plan.price)) * subscription.qty,
                is_prorated=False,
            )
            due = billing_util_next_bill_date(plan.cycle, due)
        subscriptions.append(subscription)

    session.flush()
    return subscriptions


def _net_total(quotation: Quotation) -> Decimal:
    return sum(
        (
            Decimal(str(line.unit_price))
            * line.qty
            * (Decimal("100") - Decimal(str(line.discount_pct)))
            / Decimal("100")
            for line in quotation.lines
        ),
        Decimal("0"),
    ).quantize(Decimal("0.01"))


def _seed_invoices(
    session: Session,
    built: list[tuple[Quotation, str]],
    subscriptions: list[Subscription],
) -> None:
    """One-time invoices, recurring invoices and credit notes, mixed statuses.

    A demo where every document is Unpaid tells you nothing about whether the
    status pills, the ageing column or the paid-by filter work.
    """
    confirmed = [q for q, status in built if status == QuoteStatus.CONFIRMED]
    finance = session.scalar(
        select(User).where(User.role == UserRole.FINANCE).order_by(User.id)
    )
    today = date.today()

    for index, quotation in enumerate(confirmed):
        invoice = db_create_invoice(
            session,
            quotation_id=quotation.id,
            customer_id=quotation.customer_id,
            amount=_net_total(quotation),
            line_type=LineType.ONE_TIME,
            issue_date=today - timedelta(days=60 - index * 3),
            due_date=today + timedelta(days=index * 5 - 20),
            lines=[
                {
                    "description": f"{line.product.name} x{line.qty}",
                    "qty": line.qty,
                    "amount": (
                        Decimal(str(line.unit_price))
                        * line.qty
                        * (Decimal("100") - Decimal(str(line.discount_pct)))
                        / Decimal("100")
                    ).quantize(Decimal("0.01")),
                    "is_recurring": False,
                }
                for line in quotation.lines
            ],
            sent=True,
        )
        _apply_payment(invoice, index, finance)

    for index, subscription in enumerate(subscriptions[:RECURRING_INVOICE_COUNT]):
        amount = (Decimal(str(subscription.plan.price)) * subscription.qty).quantize(
            Decimal("0.01")
        )
        invoice = db_create_invoice(
            session,
            quotation_id=subscription.quotation_id,
            customer_id=subscription.customer_id,
            amount=amount,
            line_type=LineType.RECURRING,
            issue_date=today - timedelta(days=30 - index * 2),
            due_date=today + timedelta(days=index * 4 - 10),
            lines=[
                {
                    "description": (
                        f"{subscription.plan.name} "
                        f"({subscription.plan.cycle}) x{subscription.qty}"
                    ),
                    "qty": subscription.qty,
                    "amount": amount,
                    "is_recurring": True,
                }
            ],
            sent=True,
        )
        _apply_payment(invoice, index + 1, finance)

    # Credit notes, so the document type is not uniformly "invoice". They carry
    # a negative amount on the same table - see the note on the Invoice model.
    for index in range(CREDIT_NOTE_COUNT):
        quotation = confirmed[index * 3 % len(confirmed)]
        db_create_invoice(
            session,
            quotation_id=quotation.id,
            customer_id=quotation.customer_id,
            amount=Decimal(f"-{180 + index * 145}.00"),
            doc_type=DocType.CREDIT_NOTE,
            line_type=LineType.ONE_TIME if index % 2 else LineType.RECURRING,
            issue_date=today - timedelta(days=12 + index * 9),
            reason=[
                "Goodwill credit, delayed delivery",
                "Cancelled within refund window",
                "Duplicate charge reversed",
                "Agreed post-sale price adjustment",
            ][index],
            sent=True,
        )
    session.flush()


def _apply_payment(invoice: Invoice, index: int, finance: User | None) -> None:
    """Settle every third invoice fully, the next partly, leave the rest open."""
    if index % 3 == 0:
        invoice.paid_amount = invoice.amount
        invoice.status = InvoiceStatus.PAID
    elif index % 3 == 1:
        invoice.paid_amount = (Decimal(str(invoice.amount)) / 2).quantize(
            Decimal("0.01")
        )
        invoice.status = InvoiceStatus.PARTIAL
    else:
        return

    invoice.paid_method = PAYMENT_METHODS[index % len(PAYMENT_METHODS)]
    invoice.paid_at = datetime.now(UTC) - timedelta(days=index)
    invoice.recorded_by = finance.id if finance else None


def seed_large(session: Session) -> dict[str, int]:
    """Wipe, then load the whole dataset. Returns the resulting row counts."""
    wipe(session)

    tiers = _seed_governance(session)
    customers = _seed_people(session, tiers)
    products = _seed_catalogue(session)
    _seed_fulfillment(session, products)
    plans = _seed_plans(session)
    built = _seed_quotations(session, customers, products)
    subscriptions = _seed_subscriptions(session, plans, built)
    _seed_invoices(session, built, subscriptions)

    session.commit()
    return count_rows(session)


def main() -> None:
    # Runs standalone against an empty database, so create anything missing
    # rather than requiring reset_db.py to have been run first.
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        counts = seed_large(session)
    finally:
        session.close()

    print_counts("Large demo dataset loaded:", counts)
    logger.info("Seeded %d rows across %d tables", sum(counts.values()), len(counts))


if __name__ == "__main__":
    setup_logging()
    main()
