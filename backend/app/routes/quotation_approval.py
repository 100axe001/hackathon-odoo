"""Approval endpoints that hang off a quotation URL.

Separate module from approvals.py because these mount under /quotations while
the review queue mounts under /approvals. The paths are fixed by
docs/architecture/api-contract.md, which the frontend was written against.
"""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.quotations import db_get_quotation, db_list_audit
from app.database.users import db_get_user_by_id
from app.logging.setup_logging import get_logger
from app.models.enums import AuditAction, QuoteStatus, StepStatus
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.quotations import (
    ApprovalDetailData,
    ApprovalDetailResponse,
    AuditRow,
    DecisionData,
    DecisionRequest,
    DecisionResponse,
    ErrorResponse,
    FlaggedLine,
    StepRow,
)
from app.utils.approval import (
    approval_util_close_chain,
    approval_util_current_step,
    approval_util_is_complete,
    record_audit,
)
from app.utils.quotation_pricing import pricing_util_explain, pricing_util_score

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


# "returnd" is what f"{decision}d" produced, and it reached the reviewer.
_PAST_TENSE = {"approve": "approved", "return": "returned", "reject": "rejected"}

_DIRECTION = {"approve": "forward", "return": "back", "reject": "stopped"}


def _stage_label(quotation, step) -> str:
    """Where the chain stands. An ended chain is not the same as a finished one.

    Without the first two branches a returned or rejected quotation reported
    "Complete", which is what an approved one reports.
    """
    if step is not None:
        return step.required_role
    if quotation.status == QuoteStatus.REJECTED:
        return "Rejected"
    if any(s.status == StepStatus.RETURNED for s in quotation.steps):
        return "Returned for revision"
    return "Complete"


def _parse_id(raw: str) -> int:
    try:
        return int(raw[1:] if raw.startswith("q") else raw)
    except ValueError as e:
        raise _not_found(f"No quotation {raw}") from e


@router.get(
    "/{quotation_id}/approval-detail",
    response_model=ApprovalDetailResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def approval_detail(
    quotation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> ApprovalDetailResponse:
    """Why this quotation was flagged, plus the chain and the audit trail."""
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    result = pricing_util_score(db, quotation)
    db.commit()

    flagged = [
        FlaggedLine(
            line=line.product.name,
            discount_given=float(line.discount_pct),
            limit_allowed=float(line.allowed_discount_pct),
            over_by=float(line.excess_pt),
        )
        for line in quotation.lines
    ]

    audit = []
    for entry in db_list_audit(db, quotation.id):
        actor = db_get_user_by_id(db, entry.user_id)
        audit.append(
            AuditRow(
                user=actor.full_name if actor else "Unknown",
                action=entry.action,
                date=entry.created_at.strftime("%b %d, %H:%M"),
                note=entry.note,
            )
        )

    step = approval_util_current_step(quotation)

    return ApprovalDetailResponse(
        success=True,
        message="Approval detail retrieved",
        data=ApprovalDetailData(
            id=f"q{quotation.id}",
            quotation=quotation.number,
            customer=quotation.customer.name,
            blended_risk=quotation.risk_level or "LOW",
            customer_tier=quotation.customer.tier.name,
            # Generated from the calculation, never hardcoded - PS section 5.
            explanation=pricing_util_explain(result),
            lines=flagged,
            stage=_stage_label(quotation, step),
            steps=[
                StepRow(
                    role=s.required_role,
                    status=s.status,
                    acted_by=(
                        db_get_user_by_id(db, s.acted_by).full_name
                        if s.acted_by
                        else None
                    ),
                )
                for s in quotation.steps
            ],
            audit_trail=audit,
        ),
    )


@router.post(
    "/{quotation_id}/approve",
    response_model=DecisionResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 404, 409, 500)},
)
def decide(
    quotation_id: str,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> DecisionResponse:
    """Approve, return, or reject the step currently waiting on this caller."""
    quotation = db_get_quotation(db, _parse_id(quotation_id), user)
    if quotation is None:
        raise _not_found(f"No quotation {quotation_id}")

    # The whole premise of the product: a rep cannot sign off their own
    # discount, whatever role they otherwise hold.
    if quotation.rep_id == user.id:
        raise _forbidden("You cannot approve your own quotation")

    # A pending step is not on its own enough. Returning a quotation sets it back
    # to Draft while leaving the later steps PENDING, so without this an approver
    # could still act on that chain and drive a Draft straight to Approved -
    # exactly the bypass the approval routing exists to prevent.
    if quotation.status != QuoteStatus.PENDING_APPROVAL:
        raise _conflict(
            f"This quotation is {quotation.status}, not awaiting approval. "
            "It must be submitted again before anyone can act on it."
        )

    step = approval_util_current_step(quotation)
    if step is None:
        raise _conflict("This quotation is not waiting on an approval")

    if step.required_role != user.role:
        raise _forbidden(
            f"This step is waiting on {step.required_role}, not {user.role}"
        )

    step.acted_by = user.id
    step.acted_at = datetime.now(UTC)
    step.comment = payload.comment

    if payload.decision == "approve":
        step.status = StepStatus.APPROVED
        action = AuditAction.APPROVE
        if approval_util_is_complete(quotation):
            quotation.status = QuoteStatus.APPROVED
    elif payload.decision == "reject":
        step.status = StepStatus.REJECTED
        quotation.status = QuoteStatus.REJECTED
        action = AuditAction.REJECT
        # Nobody after this reviewer is waiting on anything any more.
        approval_util_close_chain(quotation, StepStatus.REJECTED)
    else:
        step.status = StepStatus.RETURNED
        # Back to the rep to revise. Re-submitting rebuilds the chain from the
        # new risk level, so a smaller discount needs fewer reviewers.
        quotation.status = QuoteStatus.DRAFT
        action = AuditAction.RETURN
        # And the reviewers after this one are no longer waiting: leaving them
        # PENDING made a returned quotation report the next role as its stage,
        # so the app said the deal had moved forward when it had gone back.
        approval_util_close_chain(quotation, StepStatus.RETURNED)

    record_audit(
        db,
        quotation=quotation,
        user_id=user.id,
        action=action,
        note=payload.comment,
    )
    db.commit()

    next_step = approval_util_current_step(quotation)
    logger.info(
        "%s %s %s -> %s",
        user.full_name,
        _PAST_TENSE[payload.decision],
        quotation.number,
        quotation.status,
    )

    return DecisionResponse(
        success=True,
        message=f"Quotation {_PAST_TENSE[payload.decision]}",
        data=DecisionData(
            status=quotation.status,
            stage=next_step.required_role if next_step else None,
            # Which way the deal just moved. The screen used to infer this from
            # the next stage being empty, which read a return as an approval by
            # the last reviewer in the chain.
            direction=_DIRECTION[payload.decision],
            complete=approval_util_is_complete(quotation),
        ),
    )
