"""Request and response models for the customer portal."""

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.auth import ErrorResponse  # noqa: F401  re-exported for routes


class PortalLine(BaseModel):
    id: str
    product: str
    qty: int
    price: float
    discount_pct: float
    amount: float


class PortalComment(BaseModel):
    line: str | None
    author: str
    body: str | None
    counter_discount_pct: float | None
    created_at: str


class PortalQuotationData(BaseModel):
    id: str
    number: str
    customer: str
    status: str
    total: float
    lines: list[PortalLine]
    comments: list[PortalComment]

    # Whether this customer can still counter or confirm, and if not, why. The
    # screen used to offer both buttons in every state, so confirming an
    # already-confirmed quotation looked like the button had done nothing.
    can_act: bool
    blocked_reason: str | None = None


class PortalQuotationResponse(BaseModel):
    success: bool
    message: str
    data: PortalQuotationData


class PortalSummary(BaseModel):
    id: str
    number: str
    status: str
    total: float


class PortalListResponse(BaseModel):
    success: bool
    message: str
    data: list[PortalSummary]


class NegotiateRequest(BaseModel):
    counter_discount_pct: float | None = Field(default=None, ge=0, le=100)
    requested_delivery_date: date | None = None
    note: str | None = None


class NegotiateData(BaseModel):
    status: str
    counter_discount_pct: float | None
    message: str


class NegotiateResponse(BaseModel):
    success: bool
    message: str
    data: NegotiateData


class ConfirmData(BaseModel):
    status: str
    risk_level: str
    reentered_approval: bool
    required_approval: list[str]
    explanation: str


class ConfirmResponse(BaseModel):
    success: bool
    message: str
    data: ConfirmData


class PortalShipment(BaseModel):
    """Where one part of an order is shipping from."""

    warehouse: str | None
    product: str
    qty: int


class PortalOrder(BaseModel):
    """A deal the customer has agreed to, and how far along it is."""

    id: str
    number: str
    status: str
    total: float
    fulfillment: str
    shipments: list[PortalShipment]


class PortalOrdersResponse(BaseModel):
    success: bool
    message: str
    data: list[PortalOrder]


class PortalInvoice(BaseModel):
    id: str
    number: str
    document: str
    order: str
    amount: float
    paid: float
    balance_due: float
    status: str
    issue_date: str
    due_date: str


class PortalSubscription(BaseModel):
    plan: str
    cycle: str
    qty: int
    amount: float
    next_bill: str
    status: str


class PortalBillingData(BaseModel):
    invoices: list[PortalInvoice]
    subscriptions: list[PortalSubscription]
    total_outstanding: float


class PortalBillingResponse(BaseModel):
    success: bool
    message: str
    data: PortalBillingData


class PortalProfileData(BaseModel):
    """Who the customer is, as the platform sees them.

    The tier is shown because it decides the discount ceiling their rep is
    working against - it explains why a counter-offer was accepted or refused.
    """

    company: str
    tier: str
    contact_name: str
    contact_email: str
    open_quotations: int
    orders: int
    outstanding: float


class PortalProfileResponse(BaseModel):
    success: bool
    message: str
    data: PortalProfileData
