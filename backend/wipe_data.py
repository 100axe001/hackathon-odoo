"""Empty every demo table, leaving the schema in place.

DESTRUCTIVE. This deletes every row in the application tables - quotations,
customers, invoices, users, catalogue and configuration alike. It is not the
normal path for the demo: `reset_db.py` drops, recreates and reseeds in seconds
and is what you almost always want. Reach for this one only when the tables have
to be emptied without touching the schema, for instance before `seed_large.py`
loads the stress-test dataset.

Run it with an explicit `--yes`. Without that argument it prints the row counts
it would remove and exits having changed nothing.

    ./.venv/bin/python wipe_data.py           # dry run, prints what it would do
    ./.venv/bin/python wipe_data.py --yes     # actually deletes
"""

import argparse
import sys

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database.connection import Base, SessionLocal
from app.logging.setup_logging import get_logger, setup_logging
from app.models.billing import (
    BillingSchedule,
    Invoice,
    InvoiceLine,
    Subscription,
    SubscriptionPlan,
)
from app.models.catalog import PriceList, Product
from app.models.config import (
    ApprovalRule,
    CategoryCeiling,
    RiskThreshold,
    UpsellRule,
)
from app.models.fulfillment import FulfillmentAllocation, StockLevel, Warehouse
from app.models.health import DealHealthFlag, ProductPairing
from app.models.identity import Customer, DiscountTier, User
from app.models.negotiation import NegotiationMessage
from app.models.quotation import ApprovalStep, AuditLog, Quotation, QuotationLine

logger = get_logger(__name__)

# Child before parent, and this order is the whole safety of the script: a
# delete that would leave a foreign key pointing at nothing is refused by
# Postgres, so getting the sequence wrong fails loudly instead of quietly
# corrupting the demo. Every module under app/models is represented.
DELETE_ORDER: list[type[Base]] = [
    AuditLog,
    NegotiationMessage,
    DealHealthFlag,
    FulfillmentAllocation,
    ApprovalStep,
    BillingSchedule,
    InvoiceLine,
    Invoice,
    Subscription,
    QuotationLine,
    Quotation,
    StockLevel,
    ProductPairing,
    PriceList,
    SubscriptionPlan,
    Warehouse,
    Product,
    User,
    Customer,
    DiscountTier,
    CategoryCeiling,
    RiskThreshold,
    ApprovalRule,
    UpsellRule,
]


def count_rows(session: Session) -> dict[str, int]:
    """Current row count per table, in the order a wipe would visit them."""
    counts: dict[str, int] = {}
    for model in DELETE_ORDER:
        counts[model.__tablename__] = (
            session.scalar(select(func.count()).select_from(model)) or 0
        )
    return counts


def wipe(session: Session) -> dict[str, int]:
    """Delete every row and return what each table gave up.

    Committed as one transaction: a wipe that stopped halfway would leave the
    database in a state neither seed script expects to find.
    """
    removed: dict[str, int] = {}
    for model in DELETE_ORDER:
        result = session.execute(delete(model))
        removed[model.__tablename__] = result.rowcount or 0
    session.commit()
    return removed


def print_counts(title: str, counts: dict[str, int]) -> None:
    print(title)
    for table, count in counts.items():
        print(f"  {table:<26} {count:>6}")
    print(f"  {'TOTAL':<26} {sum(counts.values()):>6}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Delete every demo row, leaving the schema in place. Destructive - "
            "reset_db.py is the normal path for the demo."
        )
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="actually delete; without it this is a dry run",
    )
    args = parser.parse_args(argv)

    session = SessionLocal()
    try:
        if not args.yes:
            print_counts(
                "Dry run - nothing was deleted. Would remove:", count_rows(session)
            )
            print("\nRe-run with --yes to delete these rows.")
            return 0

        removed = wipe(session)
        print_counts("Deleted:", removed)
        logger.info(
            "Wiped %d rows across %d tables", sum(removed.values()), len(removed)
        )
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    setup_logging()
    sys.exit(main())
