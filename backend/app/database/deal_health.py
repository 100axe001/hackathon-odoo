"""Data access for Deal Health. Every function is prefixed db_."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import QuoteStatus
from app.models.health import DealHealthFlag
from app.models.quotation import Quotation, QuotationLine


def db_list_open_quotations(session: Session) -> list[Quotation]:
    """Quotations still in play. A confirmed or rejected deal cannot stall."""
    return list(
        session.scalars(
            select(Quotation)
            .where(
                Quotation.status.notin_([QuoteStatus.CONFIRMED, QuoteStatus.REJECTED])
            )
            .options(
                selectinload(Quotation.lines).selectinload(QuotationLine.product),
                selectinload(Quotation.customer),
            )
            .order_by(Quotation.id)
        ).all()
    )


def db_rep_discount_history(
    session: Session, rep_id: int, exclude_quotation_id: int
) -> list[Decimal]:
    """A rep's past quotation-level discounts, excluding the one being scored.

    Including it would drag the baseline toward the very value under test, which
    is how an anomaly hides itself.
    """
    from app.utils.deal_health import health_util_effective_discount

    rows = session.scalars(
        select(Quotation)
        .where(Quotation.rep_id == rep_id, Quotation.id != exclude_quotation_id)
        .options(selectinload(Quotation.lines))
    ).all()
    return [health_util_effective_discount(q) for q in rows if q.lines]


def db_replace_flags(session: Session, flags: list[dict]) -> list[DealHealthFlag]:
    """Recompute the board.

    Flags are derived state, so they are rebuilt rather than accumulated -
    otherwise a deal that came back to life would keep its stale warning. Rows a
    human has acted on are kept, so an escalation is not silently undone.
    """
    acted = {
        (f.quotation_id, f.type): f
        for f in session.scalars(
            select(DealHealthFlag).where(DealHealthFlag.action_taken.isnot(None))
        ).all()
    }

    for flag in session.scalars(
        select(DealHealthFlag).where(DealHealthFlag.action_taken.is_(None))
    ).all():
        session.delete(flag)
    session.flush()

    created = []
    for payload in flags:
        key = (payload["quotation_id"], payload["type"])
        if key in acted:
            created.append(acted[key])
            continue
        flag = DealHealthFlag(**payload)
        session.add(flag)
        created.append(flag)

    session.flush()
    return created


def db_get_flag(session: Session, flag_id: int) -> DealHealthFlag | None:
    return session.get(DealHealthFlag, flag_id)


def db_mark_flag_action(
    session: Session, flag: DealHealthFlag, action: str
) -> DealHealthFlag:
    flag.action_taken = action
    flag.resolved_at = datetime.now(UTC)
    session.flush()
    return flag
