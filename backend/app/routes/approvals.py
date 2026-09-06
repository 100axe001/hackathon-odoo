"""Approvals: the review queue, the risk breakdown, and the decision."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.quotations import (
    db_list_pending_approvals,
)
from app.logging.setup_logging import get_logger
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.quotations import (
    ApprovalRow,
    ErrorResponse,
    ListApprovalsResponse,
)
from app.utils.approval import (
    approval_util_current_step,
)

logger = get_logger(__name__)
router = APIRouter()


def _not_found(what: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorResponse(
            success=False, error="Not Found", message=what
        ).model_dump(),
    )


def _forbidden(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ErrorResponse(
            success=False, error="Forbidden", message=message
        ).model_dump(),
    )


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False, error="Conflict", message=message
        ).model_dump(),
    )


def _parse_id(raw: str) -> int:
    try:
        return int(raw[1:] if raw.startswith("q") else raw)
    except ValueError as e:
        raise _not_found(f"No quotation {raw}") from e


@router.get(
    "",
    response_model=ListApprovalsResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_approvals(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListApprovalsResponse:
    """Everything waiting on a reviewer."""
    rows = []
    for quotation in db_list_pending_approvals(db):
        try:
            step = approval_util_current_step(quotation)
            rows.append(
                ApprovalRow(
                    id=f"q{quotation.id}",
                    quotation=quotation.number,
                    customer=quotation.customer.name,
                    blended_risk=quotation.risk_level or "LOW",
                    stage=step.required_role if step else "Complete",
                    assigned_to=step.required_role if step else "-",
                    # Nobody signs off their own discount. Saying so in the
                    # queue beats letting a reviewer open their own quotation
                    # and meet a 403 at the last click.
                    own=quotation.rep_id == user.id,
                )
            )
        except Exception as e:
            logger.warning("Skipping approval row %s: %s", quotation.id, e)

    return ListApprovalsResponse(
        success=True,
        message=f"Successfully retrieved {len(rows)} approvals",
        data=rows,
    )
