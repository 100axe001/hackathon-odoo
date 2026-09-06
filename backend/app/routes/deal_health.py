"""Deal Health: stalled deals, discount anomalies, delivery slippage.

Advisory only. Nothing here influences approval routing - that stays with the
deterministic engine, and keeping the two apart is the point.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deal_health import (
    db_get_flag,
    db_mark_flag_action,
    db_replace_flags,
)
from app.logging.setup_logging import get_logger
from app.models.enums import FlagAction, FlagType
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.deal_health import (
    DealHealthData,
    DealHealthResponse,
    ErrorResponse,
    FlagActionData,
    FlagActionResponse,
    FlagRow,
)
from app.utils.deal_health import health_util_compute_flags

logger = get_logger(__name__)
router = APIRouter()


def _not_found(what: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorResponse(
            success=False, error="Not Found", message=what
        ).model_dump(),
    )


def _to_row(flag) -> FlagRow:
    return FlagRow(
        id=f"f{flag.id}",
        quotation_id=f"q{flag.quotation_id}",
        deal=f"{flag.quotation.customer.name} — {flag.quotation.number}",
        issue=flag.issue,
        severity=flag.severity,
        flagged=flag.flagged_at.strftime("%b %d, %Y"),
        action=flag.action_taken,
    )


@router.get(
    "",
    response_model=DealHealthResponse,
    responses={500: {"model": ErrorResponse}},
)
def get_deal_health(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> DealHealthResponse:
    """Recompute the board and return it grouped by flag type."""
    flags = db_replace_flags(db, health_util_compute_flags(db))
    db.commit()

    grouped = {
        FlagType.STALLED: [],
        FlagType.DISCOUNT_ANOMALY: [],
        FlagType.DELIVERY_SLIPPAGE: [],
    }
    for flag in flags:
        try:
            grouped[flag.type].append(_to_row(flag))
        except Exception as e:
            # One unreadable flag must not blank the whole dashboard.
            logger.warning("Skipping flag %s: %s", flag.id, e)

    return DealHealthResponse(
        success=True,
        message=f"Successfully retrieved {len(flags)} flags",
        data=DealHealthData(
            stalled=grouped[FlagType.STALLED],
            anomalies=grouped[FlagType.DISCOUNT_ANOMALY],
            slippage=grouped[FlagType.DELIVERY_SLIPPAGE],
        ),
    )


def _act(db: Session, flag_id: str, action: str, user: User) -> FlagActionResponse:
    raw = flag_id[1:] if flag_id.startswith("f") else flag_id
    flag = db_get_flag(db, int(raw))
    if flag is None:
        raise _not_found(f"No flag {flag_id}")

    db_mark_flag_action(db, flag, action)
    db.commit()
    logger.info("%s %s flag %s", user.full_name, action.lower(), flag_id)

    return FlagActionResponse(
        success=True,
        message=f"Flag {action.lower()}",
        data=FlagActionData(id=flag_id, action=action),
    )


@router.post(
    "/{flag_id}/escalate",
    response_model=FlagActionResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def escalate(
    flag_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> FlagActionResponse:
    return _act(db, flag_id, FlagAction.ESCALATED, user)


@router.post(
    "/{flag_id}/nudge",
    response_model=FlagActionResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def nudge(
    flag_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> FlagActionResponse:
    return _act(db, flag_id, FlagAction.NUDGED, user)
