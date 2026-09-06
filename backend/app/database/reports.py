"""Aggregates for the reporting screen. Every function is prefixed db_."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypedDict

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.models.catalog import Product
from app.models.enums import AuditAction, QuoteStatus
from app.models.identity import User
from app.models.quotation import AuditLog, Quotation, QuotationLine


class TopProductRow(TypedDict):
    """The single most-quoted product, and how many lines earned it that spot."""

    name: str
    quotation_lines: int


@dataclass(frozen=True)
class ReportFilters:
    """The four filters PS 4-A7 names, resolved to columns we actually store.

    "Sales team" is a rep here: the data model has reps, not teams, and
    inventing a team column would make the filter look real while grouping on
    nothing. Every field is optional; None means "do not narrow on this".
    """

    days: int | None = None
    rep: str | None = None
    category: str | None = None

    @property
    def since(self) -> datetime | None:
        return datetime.now(UTC) - timedelta(days=self.days) if self.days else None


_UNFILTERED = ReportFilters()


def _narrow(query, filters: ReportFilters, *, joined_lines: bool = True):
    """Apply the active filters to a query already joined to lines and rep.

    Category filters through the product, so it only narrows queries that reach
    the line table - which every aggregate here does.
    """
    if filters.since is not None:
        query = query.where(Quotation.created_at >= filters.since)
    if filters.rep:
        query = query.where(User.full_name == filters.rep)
    if filters.category and joined_lines:
        query = query.where(Product.category == filters.category)
    return query


# Net value computed from the lines rather than read from Quotation.total_net_value.
# That column is only written when a quotation is scored, so a draft that nobody
# has opened yet would report as zero and quietly understate the pipeline.
_NET = func.coalesce(
    func.sum(
        QuotationLine.unit_price
        * QuotationLine.qty
        * (100 - QuotationLine.discount_pct)
        / 100
    ),
    0,
)


def db_count_quotations(session: Session, filters: ReportFilters = _UNFILTERED) -> int:
    query = _narrow(
        select(func.count(func.distinct(Quotation.id)))
        .select_from(Quotation)
        .join(User, Quotation.rep_id == User.id)
        .outerjoin(QuotationLine, QuotationLine.quotation_id == Quotation.id)
        .outerjoin(Product, Product.id == QuotationLine.product_id),
        filters,
    )
    return session.scalar(query) or 0


def db_avg_approval_hours(session: Session) -> float | None:
    """Mean hours between a submission and the decision that closed it.

    Returns None when nothing has been approved yet, so the screen can say so
    rather than printing a misleading zero.
    """
    submits = {
        row.quotation_id: row.created_at
        for row in session.scalars(
            select(AuditLog).where(AuditLog.action == AuditAction.SUBMIT)
        ).all()
    }
    approvals = [
        row
        for row in session.scalars(
            select(AuditLog).where(AuditLog.action == AuditAction.APPROVE)
        ).all()
        if row.quotation_id in submits
    ]
    if not approvals:
        return None

    spans = [
        (row.created_at - submits[row.quotation_id]).total_seconds() / 3600
        for row in approvals
    ]
    return sum(spans) / len(spans)


def db_status_breakdown(
    session: Session, filters: ReportFilters = _UNFILTERED
) -> list[tuple[str, int, float]]:
    """Count and value per status, for the pipeline table."""
    rows = session.execute(
        _narrow(
            select(
                Quotation.status,
                func.count(func.distinct(Quotation.id)),
                _NET,
            )
            .join(User, Quotation.rep_id == User.id)
            .outerjoin(QuotationLine, QuotationLine.quotation_id == Quotation.id)
            .outerjoin(Product, Product.id == QuotationLine.product_id),
            filters,
        ).group_by(Quotation.status)
    ).all()
    order = list(QuoteStatus)
    return sorted(
        [(r[0], r[1], float(r[2])) for r in rows],
        key=lambda r: order.index(r[0]) if r[0] in order else 99,
    )


def db_rep_breakdown(
    session: Session, filters: ReportFilters = _UNFILTERED
) -> list[tuple[str, int, float, int]]:
    """Per-rep volume, value, and how many of their quotes needed review."""
    rows = session.execute(
        _narrow(
            select(
                User.full_name,
                func.count(func.distinct(Quotation.id)),
                _NET,
                func.coalesce(
                    func.sum(func.cast(QuotationLine.excess_pt > 0, Integer)), 0
                ),
            )
            .join(Quotation, Quotation.rep_id == User.id)
            .outerjoin(QuotationLine, QuotationLine.quotation_id == Quotation.id)
            .outerjoin(Product, Product.id == QuotationLine.product_id),
            filters,
        )
        .group_by(User.full_name)
        .order_by(func.count(func.distinct(Quotation.id)).desc())
    ).all()
    return [(r[0], r[1], float(r[2]), int(r[3])) for r in rows]


def db_top_product(
    session: Session, filters: ReportFilters = _UNFILTERED
) -> TopProductRow | None:
    """The product appearing on the most quotation lines.

    None when nothing has been quoted yet, so the screen can say so rather than
    naming an arbitrary product.
    """
    row = session.execute(
        _narrow(
            select(Product.name, func.count(QuotationLine.id))
            .join(QuotationLine, QuotationLine.product_id == Product.id)
            .join(Quotation, Quotation.id == QuotationLine.quotation_id)
            .join(User, Quotation.rep_id == User.id),
            filters,
        )
        .group_by(Product.name)
        .order_by(func.count(QuotationLine.id).desc())
        .limit(1)
    ).first()
    return TopProductRow(name=row[0], quotation_lines=int(row[1])) if row else None


def db_filter_options(session: Session) -> tuple[list[str], list[str]]:
    """The reps and categories that actually appear in the data.

    Built from the rows rather than hardcoded, so a dropdown can never offer a
    filter that matches nothing.
    """
    reps = list(
        session.scalars(
            select(User.full_name)
            .join(Quotation, Quotation.rep_id == User.id)
            .distinct()
            .order_by(User.full_name)
        ).all()
    )
    categories = list(
        session.scalars(
            select(Product.category).distinct().order_by(Product.category)
        ).all()
    )
    return reps, categories
