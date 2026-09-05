"""Enum values shared by models and schemas.

Stored as VARCHAR with a CHECK constraint rather than a native Postgres enum -
altering a native enum mid-build is painful and we add statuses often.
"""

from enum import StrEnum


class UserRole(StrEnum):
    SALES_REP = "SALES_REP"
    SALES_MANAGER = "SALES_MANAGER"
    FINANCE = "FINANCE"
    ADMIN = "ADMIN"
    CUSTOMER = "CUSTOMER"


# Everyone who works inside the company. A CUSTOMER is deliberately excluded:
# these are the roles allowed on internal routes.
INTERNAL_ROLES = frozenset(
    {UserRole.SALES_REP, UserRole.SALES_MANAGER, UserRole.FINANCE, UserRole.ADMIN}
)


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DecidedBy(StrEnum):
    NONE = "NONE"
    WORST_LINE = "WORST_LINE"
    BLENDED = "BLENDED"
    BOTH = "BOTH"


class RuleType(StrEnum):
    WORST_LINE = "WORST_LINE"
    BLENDED = "BLENDED"


class QuoteStatus(StrEnum):
    DRAFT = "Draft"
    PENDING_APPROVAL = "Pending Approval"
    APPROVED = "Approved"
    NEGOTIATION = "Negotiation"
    CONFIRMED = "Confirmed"
    REJECTED = "Rejected"


class StepStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RETURNED = "RETURNED"


class AuditAction(StrEnum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    RETURN = "RETURN"
    RESUBMIT = "RESUBMIT"
    DISCOUNT_EDIT = "DISCOUNT_EDIT"
    NEGOTIATE = "NEGOTIATE"
    CONFIRM = "CONFIRM"


class LineType(StrEnum):
    ONE_TIME = "ONE_TIME"
    RECURRING = "RECURRING"
