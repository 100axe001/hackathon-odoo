"""Approval chain construction and the audit trail. No FastAPI imports."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.config import ApprovalRule
from app.models.enums import AuditAction, RiskLevel, StepStatus
from app.models.quotation import ApprovalStep, AuditLog, Quotation


def approval_util_required_roles(session: Session, risk_level: str) -> list[str]:
    """The reviewer chain for a risk level, in order.

    Read from approval_rules rather than hardcoded, so Screen 18 genuinely
    drives the routing instead of decorating it.
    """
    rows = session.scalars(
        select(ApprovalRule)
        .where(ApprovalRule.level == risk_level)
        .order_by(ApprovalRule.step_order)
    ).all()
    return [r.role for r in rows]


def approval_util_build_chain(
    session: Session, quotation: Quotation, risk_level: str
) -> list[ApprovalStep]:
    """Replace the quotation's chain with the one its risk level requires.

    Rebuilt rather than appended to: a returned quotation that comes back with
    a smaller discount should need fewer reviewers, not carry the old ones.
    """
    for step in list(quotation.steps):
        session.delete(step)
    session.flush()

    steps = [
        ApprovalStep(
            quotation_id=quotation.id,
            step_order=order,
            required_role=role,
            status=StepStatus.PENDING,
        )
        for order, role in enumerate(
            approval_util_required_roles(session, risk_level), start=1
        )
    ]
    session.add_all(steps)
    session.flush()
    return steps


def approval_util_close_chain(quotation: Quotation, outcome: str) -> None:
    """End the chain when a reviewer sends the quotation back or kills it.

    Only the acting step used to change, which left every later step PENDING on
    a quotation that was no longer in review. The chain then read as though the
    deal had moved on to the next reviewer - the approval screen announced the
    next role, and the kanban refused to move the card because an approval
    looked outstanding - when in fact it had gone back to the rep.
    """
    for step in quotation.steps:
        if step.status == StepStatus.PENDING:
            step.status = outcome


def approval_util_returned_step(quotation: Quotation) -> ApprovalStep | None:
    """The step that sent this quotation back, if that is why it is a Draft.

    The rep needs to see that a human returned it and what they asked for;
    without it a returned quotation is indistinguishable from one never
    submitted.
    """
    returned = [
        s
        for s in quotation.steps
        if s.status == StepStatus.RETURNED and s.acted_by is not None
    ]
    if not returned:
        return None
    return max(returned, key=lambda s: s.step_order)


def approval_util_current_step(quotation: Quotation) -> ApprovalStep | None:
    """The step waiting on someone, or None when the chain is finished."""
    return next((s for s in quotation.steps if s.status == StepStatus.PENDING), None)


def approval_util_is_complete(quotation: Quotation) -> bool:
    return bool(quotation.steps) and all(
        s.status == StepStatus.APPROVED for s in quotation.steps
    )


def record_audit(
    session: Session,
    *,
    quotation: Quotation,
    user_id: int,
    action: str,
    note: str | None = None,
) -> AuditLog:
    """Append one audit row and mark the quotation as touched.

    The only place last_activity_at is set. Activity means a person did
    something, which is what the stalled-deal check needs to measure - not that
    some column happened to change.
    """
    entry = AuditLog(
        quotation_id=quotation.id, user_id=user_id, action=action, note=note
    )
    session.add(entry)
    quotation.last_activity_at = datetime.now(UTC)
    session.flush()
    return entry


def approval_util_needs_approval(risk_level: str) -> bool:
    return risk_level != RiskLevel.LOW


__all__ = [
    "AuditAction",
    "approval_util_build_chain",
    "approval_util_close_chain",
    "approval_util_current_step",
    "approval_util_is_complete",
    "approval_util_needs_approval",
    "approval_util_required_roles",
    "approval_util_returned_step",
    "record_audit",
]
