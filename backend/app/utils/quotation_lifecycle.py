"""When a quotation may be thrown away. No FastAPI imports.

Deleting is the one destructive action an ordinary user has, so the rule lives
here rather than in the route: the same function answers the endpoint and fills
the can_delete flag the screens render, which is what stops a button offering
something the server will refuse.
"""

from app.models.enums import QuoteStatus
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


__all__ = ["lifecycle_util_can_delete", "lifecycle_util_delete_block"]
