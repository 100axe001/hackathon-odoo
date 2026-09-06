"""Who may act on a quotation outside the approval chain. No FastAPI imports.

Deleting and fulfilling are both answered here rather than in their routes: the
same function answers the endpoint and fills the flag the screens render, which
is what stops a button offering something the server will refuse.
"""

from app.models.enums import QuoteStatus, UserRole
from app.models.identity import User
from app.models.quotation import Quotation


def lifecycle_util_delete_block(
    quotation: Quotation, user: User, *, billed: bool
) -> str | None:
    """Why this caller may not delete this quotation, or None if they may.

    Ownership first, because it is the answer that does not depend on the state
    of the deal: a manager looking at a rep's quotation should be told it is not
    theirs, not that it has been invoiced.
    """
    if quotation.rep_id != user.id:
        return "You can only delete a quotation you created."
    if billed:
        return (
            f"{quotation.number} has been billed. Cancel the subscription or "
            "credit the invoice instead - deleting it would erase money the "
            "customer already owes or has paid."
        )
    if quotation.status == QuoteStatus.CONFIRMED:
        return (
            f"{quotation.number} has been confirmed by the customer. It is an "
            "order now, not a draft."
        )
    return None


def lifecycle_util_can_delete(
    quotation: Quotation, user: User, *, billed: bool
) -> bool:
    return lifecycle_util_delete_block(quotation, user, billed=billed) is None


def lifecycle_util_fulfillment_block(quotation: Quotation, user: User) -> str | None:
    """Why this caller may not fulfil this order, or None if they may.

    The deal's own rep ships it, and an admin may step in for anyone. There is
    no warehouse role in the brief's five, so the owner is the person who knows
    the deal - and leaving it open to every internal role meant finance could
    accept a split, reserve stock and mark an order shipped on a deal it had
    never seen.
    """
    if user.role == UserRole.ADMIN:
        return None
    if quotation.rep_id != user.id:
        handler = quotation.rep.full_name if quotation.rep else "another rep"
        return (
            f"{quotation.number} is handled by {handler}. "
            "Only the rep who owns the order, or an admin, can fulfil it."
        )
    return None


def lifecycle_util_can_fulfil(quotation: Quotation, user: User) -> bool:
    return lifecycle_util_fulfillment_block(quotation, user) is None


__all__ = [
    "lifecycle_util_can_delete",
    "lifecycle_util_can_fulfil",
    "lifecycle_util_delete_block",
    "lifecycle_util_fulfillment_block",
]
