"""The dashboard summary."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.dashboard import (
    db_count_open_quotations,
    db_get_quotation_number,
    db_recent_audit_log,
)
from app.database.quotations import db_list_pending_approvals
from app.database.users import db_get_user_by_id
from app.logging.setup_logging import get_logger
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.dashboard import (
    ActivityRow,
    DashboardData,
    DashboardResponse,
    ErrorResponse,
)
from app.utils.approval import approval_util_in_queue
from app.utils.deal_health import health_util_compute_flags

logger = get_logger(__name__)
router = APIRouter()


def _ago(then: datetime) -> str:
    if then.tzinfo is None:
        then = then.replace(tzinfo=UTC)
    delta = datetime.now(UTC) - then

    if delta.days >= 1:
        return f"{delta.days}d ago"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h ago"
    return f"{max(1, delta.seconds // 60)}m ago"


_ACTION_TEXT = {
    "SUBMIT": "submitted for approval",
    "APPROVE": "approved",
    "REJECT": "rejected",
    "RETURN": "returned for revision",
    "RESUBMIT": "resubmitted",
    "DISCOUNT_EDIT": "discount edited",
    "NEGOTIATE": "counter-offer received",
    "CONFIRM": "confirmed by the customer",
}


@router.get(
    "/summary",
    response_model=DashboardResponse,
    responses={500: {"model": ErrorResponse}},
)
def summary(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> DashboardResponse:
    """Counts computed from the data, and the real audit trail as activity."""
    # Scoped the same way the queue is: a count that includes deals waiting on
    # somebody else sends a reviewer to a screen with nothing on it for them.
    pending = sum(
        1
        for quotation in db_list_pending_approvals(db)
        if approval_util_in_queue(quotation, user)
    )
    open_quotes = db_count_open_quotations(db)
    # Computed rather than counted from stored rows: those only exist once
    # someone opens the Deal Health board, so the landing page would say zero
    # while three deals were flagged.
    at_risk = len({flag["quotation_id"] for flag in health_util_compute_flags(db)})

    activity = []
    for entry in db_recent_audit_log(db):
        number = db_get_quotation_number(db, entry.quotation_id)
        actor = db_get_user_by_id(db, entry.user_id)
        verb = _ACTION_TEXT.get(entry.action, entry.action.lower())
        activity.append(
            ActivityRow(
                id=f"a{entry.id}",
                text=(
                    f"{number if number is not None else 'A quotation'} {verb}"
                    f"{f' by {actor.full_name}' if actor else ''}"
                ),
                timestamp=_ago(entry.created_at),
            )
        )

    return DashboardResponse(
        success=True,
        message="Dashboard retrieved",
        data=DashboardData(
            pending_approvals=pending,
            open_quotations=open_quotes,
            at_risk_deals=at_risk or 0,
            recent_activity=activity,
        ),
    )
