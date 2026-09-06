"""Where a deal stands on the quotation-to-cash path, and what happens next.

One place computes this so every screen agrees. Without it the app was a set of
tabs that each knew their own step and nothing about the one before or after,
which left the person driving to work out where to go next.

No FastAPI imports.
"""

from dataclasses import dataclass

from app.models.enums import FulfilStatus, InvoiceStatus, QuoteStatus

DONE, CURRENT, TODO, SKIPPED = "done", "current", "todo", "skipped"


@dataclass(frozen=True)
class Stage:
    key: str
    label: str
    state: str
    detail: str


@dataclass(frozen=True)
class Next:
    label: str
    path: str
    role: str


def _build_state(quotation, invoices) -> tuple[str, str, str, str, str]:
    """The state of each of the five stages, in order."""
    status = quotation.status
    priced = bool(quotation.lines)
    approved = status in (QuoteStatus.APPROVED, QuoteStatus.CONFIRMED)
    shipped = quotation.fulfillment_status in (
        FulfilStatus.SPLIT_ACCEPTED,
        FulfilStatus.OVERRIDDEN,
        FulfilStatus.SHIPPED,
    )
    billed = bool(invoices)
    settled = bool(invoices) and all(
        inv.status == InvoiceStatus.PAID for inv in invoices if inv.amount > 0
    )

    build = DONE if priced and status != QuoteStatus.DRAFT else CURRENT
    if status == QuoteStatus.DRAFT:
        build = CURRENT

    if status == QuoteStatus.PENDING_APPROVAL:
        approval = CURRENT
    elif approved or status == QuoteStatus.NEGOTIATION:
        # A quotation that never needed a reviewer skipped this rather than
        # completing it, and saying "done" would overstate what happened.
        approval = DONE if quotation.risk_level not in (None, "LOW") else SKIPPED
    elif status == QuoteStatus.REJECTED:
        approval = DONE
    else:
        approval = TODO

    if shipped:
        fulfil = DONE
    elif approved:
        fulfil = CURRENT
    else:
        fulfil = TODO

    if settled:
        billing, payment = DONE, DONE
    elif billed:
        billing, payment = DONE, CURRENT
    elif shipped:
        billing, payment = CURRENT, TODO
    else:
        billing, payment = TODO, TODO

    return build, approval, fulfil, billing, payment


def journey_util_stages(quotation, invoices) -> list[Stage]:
    build, approval, fulfil, billing, payment = _build_state(quotation, invoices)
    outstanding = sum(
        float(inv.amount) - float(inv.paid_amount) for inv in invoices if inv.amount > 0
    )

    return [
        Stage(
            "build",
            "Build",
            build,
            f"{len(quotation.lines)} line(s)" if quotation.lines else "No lines yet",
        ),
        Stage(
            "approval",
            "Approval",
            approval,
            _approval_detail(quotation, approval),
        ),
        Stage(
            "fulfillment",
            "Fulfillment",
            fulfil,
            _fulfillment_detail(quotation, fulfil),
        ),
        Stage(
            "billing",
            "Billing",
            billing,
            f"{len(invoices)} document(s)" if invoices else "Not invoiced",
        ),
        Stage(
            "payment",
            "Payment",
            payment,
            "Settled" if payment == DONE else f"${outstanding:,.2f} outstanding",
        ),
    ]


def _approval_detail(quotation, state: str) -> str:
    if state == SKIPPED:
        return "Within limits, no review needed"
    pending = [s for s in quotation.steps if s.status == "PENDING"]
    if state == CURRENT and pending:
        return f"Waiting on {pending[0].required_role.replace('_', ' ').title()}"
    if quotation.risk_level:
        return f"{quotation.risk_level} risk"
    return "Not submitted"


def _fulfillment_detail(quotation, state: str) -> str:
    if state == DONE:
        return "Stock reserved"
    if state == CURRENT:
        return "Ready to split"
    return "Waiting on approval"


def journey_util_next(quotation, invoices, stages: list[Stage]) -> Next | None:
    """The single next thing, named with the role that has to do it.

    Returning one action rather than a list is deliberate: the point is to end
    the guessing, and offering three choices puts it straight back.
    """
    qid = f"q{quotation.id}"
    current = next((s for s in stages if s.state == CURRENT), None)
    if current is None:
        return None

    if current.key == "build":
        return Next("Submit for approval", f"/quotations/{qid}", "Sales Rep")
    if current.key == "approval":
        pending = [s for s in quotation.steps if s.status == "PENDING"]
        role = (
            pending[0].required_role.replace("_", " ").title()
            if pending
            else "Sales Manager"
        )
        return Next("Review this quotation", f"/approvals/{qid}", role)
    if current.key == "fulfillment":
        return Next("Split across warehouses", f"/fulfillment/{qid}", "Sales Rep")
    if current.key == "billing":
        return Next("Review billing", "/subscriptions", "Finance")
    unpaid = next((inv for inv in invoices if inv.status != InvoiceStatus.PAID), None)
    if unpaid:
        return Next("Record payment", f"/invoices/i{unpaid.id}", "Finance")
    return None


__all__ = ["Next", "Stage", "journey_util_next", "journey_util_stages"]
