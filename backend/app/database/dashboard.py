"""Data access for the dashboard summary. Every function is prefixed db_."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import QuoteStatus
from app.models.quotation import AuditLog, Quotation


def db_count_pending_approvals(session: Session) -> int:
    return (
        session.scalar(
            select(func.count())
            .select_from(Quotation)
            .where(Quotation.status == QuoteStatus.PENDING_APPROVAL)
        )
        or 0
    )


def db_count_open_quotations(session: Session) -> int:
    """Everything still in play - a confirmed or rejected deal is not open."""
    return (
        session.scalar(
            select(func.count())
            .select_from(Quotation)
            .where(
                Quotation.status.notin_([QuoteStatus.CONFIRMED, QuoteStatus.REJECTED])
            )
        )
        or 0
    )


def db_recent_audit_log(session: Session, limit: int = 10) -> list[AuditLog]:
    """The newest audit entries, which the dashboard renders as activity."""
    return list(
        session.scalars(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        ).all()
    )


def db_get_quotation_number(session: Session, quotation_id: int) -> str | None:
    """Unscoped on purpose: the activity feed names the quotation an audit entry
    refers to, and that entry is already only visible to internal roles."""
    quotation = session.get(Quotation, quotation_id)
    return quotation.number if quotation else None
