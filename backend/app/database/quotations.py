"""Data access for quotations. Every function is prefixed db_."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.billing import Invoice, Subscription
from app.models.config import CategoryCeiling, RiskThreshold
from app.models.enums import QuoteStatus, UserRole
from app.models.identity import Customer, User
from app.models.quotation import AuditLog, Quotation, QuotationLine
from app.utils.blended import RiskThresholds

# Seeded numbers look like "Q-1042", so a new one keeps reading as a quote
# number rather than a row id.
_NUMBER_PREFIX = "Q-"
_NUMBER_FLOOR = 1000


def _visible(query, user: User):
    """Row scoping. A rep sees their own quotations, a customer sees theirs."""
    if user.role == UserRole.SALES_REP:
        return query.where(Quotation.rep_id == user.id)
    if user.role == UserRole.CUSTOMER:
        return query.where(Quotation.customer_id == user.customer_id)
    return query


def db_list_quotations(session: Session, user: User) -> list[Quotation]:
    query = _visible(
        select(Quotation).options(
            selectinload(Quotation.lines), selectinload(Quotation.customer)
        ),
        user,
    ).order_by(Quotation.id)
    return list(session.scalars(query).all())


def db_get_quotation(
    session: Session, quotation_id: int, user: User
) -> Quotation | None:
    """Fetch one, scoped. Returns None when it exists but is not the caller's."""
    query = _visible(
        select(Quotation)
        .where(Quotation.id == quotation_id)
        .options(
            selectinload(Quotation.lines).selectinload(QuotationLine.product),
            selectinload(Quotation.steps),
            selectinload(Quotation.customer),
        ),
        user,
    )
    return session.scalar(query)


def db_next_quotation_number(session: Session) -> str:
    """The next free "Q-nnnn", derived from the highest number already stored.

    Read from the rows rather than a counter table: there are no migrations
    here and reset_db.py reseeds from scratch, so a stored sequence would drift
    away from the data on the very first reset.
    """
    highest = _NUMBER_FLOOR
    for number in session.scalars(select(Quotation.number)).all():
        suffix = number.removeprefix(_NUMBER_PREFIX)
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{_NUMBER_PREFIX}{highest + 1}"


def db_create_quotation(
    session: Session, *, customer_id: int, rep_id: int
) -> Quotation:
    """Open an empty draft. The caller supplies rep_id; the request never does."""
    quotation = Quotation(
        number=db_next_quotation_number(session),
        customer_id=customer_id,
        rep_id=rep_id,
        status=QuoteStatus.DRAFT,
    )
    session.add(quotation)
    session.commit()
    session.refresh(quotation)
    return quotation


def db_set_quotation_status(
    session: Session, quotation: Quotation, new_status: str
) -> Quotation:
    """Persist a pipeline stage change. Which moves are legal is decided above.

    Bumps last_activity_at because a rep moving a card is real activity, and the
    stalled-deal check reads that column. Without it a deal being actively worked
    on the board would keep accruing "no activity in N days" and get flagged.
    """
    quotation.status = new_status
    quotation.last_activity_at = datetime.now(UTC)
    session.commit()
    session.refresh(quotation)
    return quotation


def db_delete_quotation(session: Session, quotation: Quotation) -> None:
    """Remove a quotation and everything hanging off it.

    Lines, approval steps, the audit trail, the customer conversation, health
    flags and allocations all carry ON DELETE CASCADE, so the database takes
    them. Invoices and subscriptions deliberately do not - the caller checks for
    those first, and the missing cascade is the backstop if it ever forgets.
    """
    session.delete(quotation)
    session.commit()


def db_billed_quotation_ids(session: Session) -> set[int]:
    """Quotations that have an invoice or a subscription against them.

    Read in one query rather than per row: the list screen needs this for every
    quotation it shows, and asking once per row turned a page render into eighty
    round trips.
    """
    invoiced = session.scalars(select(Invoice.quotation_id).distinct()).all()
    subscribed = session.scalars(select(Subscription.quotation_id).distinct()).all()
    return set(invoiced) | set(subscribed)


def db_get_line(session: Session, line_id: int) -> QuotationLine | None:
    return session.get(QuotationLine, line_id)


def db_get_customer(session: Session, customer_id: int) -> Customer | None:
    return session.get(Customer, customer_id)


def db_get_category_ceiling(session: Session, category: str) -> Decimal | None:
    row = session.scalar(
        select(CategoryCeiling).where(CategoryCeiling.category == category)
    )
    return Decimal(str(row.max_discount_pct)) if row else None


def db_get_risk_thresholds(session: Session) -> RiskThresholds:
    """Load the cut-points, falling back to the documented defaults.

    A missing configuration row must not silently disable governance, so the
    fallback matches risk-engine-and-ml.md 3.5 rather than being permissive.
    """
    rows = session.scalars(select(RiskThreshold)).all()
    values = {(r.rule_type, r.level): Decimal(str(r.min_excess_pt)) for r in rows}
    defaults = RiskThresholds()

    return RiskThresholds(
        worst_medium_pt=values.get(("WORST_LINE", "MEDIUM"), defaults.worst_medium_pt),
        worst_high_pt=values.get(("WORST_LINE", "HIGH"), defaults.worst_high_pt),
        blended_medium_pt=values.get(("BLENDED", "MEDIUM"), defaults.blended_medium_pt),
        blended_high_pt=values.get(("BLENDED", "HIGH"), defaults.blended_high_pt),
    )


def db_upsell_candidates(session: Session, quotation: Quotation) -> list:
    """Products paired with what is already on the quotation.

    Anything already on the quote is excluded - suggesting a line the rep just
    added would be noise.
    """
    from app.models.health import ProductPairing

    on_quote = {line.product_id for line in quotation.lines}
    if not on_quote:
        return []

    pairs = session.scalars(
        select(ProductPairing)
        .where(ProductPairing.product_a_id.in_(on_quote))
        .options(selectinload(ProductPairing.product_b))
        .order_by(ProductPairing.rank.desc())
    ).all()

    seen, candidates = set(), []
    for pair in pairs:
        product = pair.product_b
        if product.id in on_quote or product.id in seen or not product.active:
            continue
        seen.add(product.id)
        candidates.append(product)
    return candidates


def db_get_product(session: Session, product_id: int):
    from app.models.catalog import Product

    return session.get(Product, product_id)


def db_list_audit(session: Session, quotation_id: int) -> list[AuditLog]:
    return list(
        session.scalars(
            select(AuditLog)
            .where(AuditLog.quotation_id == quotation_id)
            .order_by(AuditLog.created_at, AuditLog.id)
        ).all()
    )


def db_list_pending_approvals(session: Session) -> list[Quotation]:
    from app.models.enums import QuoteStatus

    return list(
        session.scalars(
            select(Quotation)
            .where(Quotation.status == QuoteStatus.PENDING_APPROVAL)
            .options(selectinload(Quotation.steps), selectinload(Quotation.customer))
            .order_by(Quotation.id)
        ).all()
    )
