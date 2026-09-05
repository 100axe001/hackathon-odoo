"""Deterministic demo data.

Never enter demo data through the UI - reset_db.py drops everything, and a
record created by clicking around will not survive it.
"""

from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.logging.setup_logging import get_logger
from app.models.enums import UserRole
from app.models.identity import Customer, DiscountTier, User
from app.utils.security import security_util_hash_password

logger = get_logger(__name__)

PASSWORD = "dealflow123"

TIERS = [("Bronze", 5), ("Silver", 10), ("Gold", 15)]


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
    ("manager@dealflow360.com", "Maya Shah", UserRole.SALES_MANAGER, None),
    ("finance@dealflow360.com", "Riya Iyer", UserRole.FINANCE, None),
    ("admin@dealflow360.com", "Sam Okafor", UserRole.ADMIN, None),
    ("customer@acmecorp.com", "Devon Cole", UserRole.CUSTOMER, "Acme Corp"),
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

    session.commit()
    logger.info(
        "Seeded %d tiers, %d customers, %d users",
        len(TIERS),
        len(CUSTOMERS),
        len(USERS),
    )


def main() -> None:
    session = SessionLocal()
    try:
        seed(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()
