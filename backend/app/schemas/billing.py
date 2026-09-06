"""Request and response models for subscriptions and invoices."""

from pydantic import BaseModel, Field

from app.schemas.auth import ErrorResponse  # noqa: F401  re-exported for routes


class SubscriptionRow(BaseModel):
    id: str
    customer: str
    plan: str
    cycle: str
    next_bill: str
    status: str


class ListSubscriptionsResponse(BaseModel):
    success: bool
    message: str
    data: list[SubscriptionRow]


class BillingLine(BaseModel):
    product: str
    qty: int
    amount: float


class RecurringLine(BaseModel):
    plan: str
    cycle: str
    next_bill: str
    amount: float


class ScheduleRow(BaseModel):
    due_date: str
    amount: float
    is_prorated: bool
    note: str | None


class BillingDetailData(BaseModel):
    id: str
    customer: str
    status: str
    # PS 4-B7 requires these to be shown separately, so they arrive separately.
    one_time_lines: list[BillingLine]
    recurring_lines: list[RecurringLine]
    schedule: list[ScheduleRow]


class BillingDetailResponse(BaseModel):
    success: bool
    message: str
    data: BillingDetailData


class ModifyRequest(BaseModel):
    qty: int = Field(ge=0)


class ProrationData(BaseModel):
    amount: float
    is_credit: bool
    remaining_days: int
    cycle_days: int
    price_delta: float
    new_qty: int
    explanation: str


class ModifyResponse(BaseModel):
    success: bool
    message: str
    data: ProrationData


class CancelData(BaseModel):
    status: str
    credit_amount: float
    credit_note: str | None
    explanation: str


class CancelResponse(BaseModel):
    success: bool
    message: str
    data: CancelData


class InvoiceRow(BaseModel):
    id: str
    invoice_no: str
    customer: str
    amount: float
    status: str
    due_date: str
    line_type: str


class ListInvoicesResponse(BaseModel):
    success: bool
    message: str
    data: list[InvoiceRow]


class InvoiceLineRow(BaseModel):
    description: str
    qty: int
    amount: float
    is_recurring: bool


class InvoiceDetailData(BaseModel):
    id: str
    invoice_no: str
    customer: str
    stage: str
    status: str
    amount: float
    paid_amount: float
    due_date: str
    lines: list[InvoiceLineRow]

    # What is actually still owed, and who settled it. All of this was already
    # stored; none of it reached the screen, so a part-paid invoice looked the
    # same as an unpaid one apart from a badge.
    balance_due: float
    issue_date: str
    doc_type: str
    paid_at: str | None = None
    paid_method: str | None = None
    recorded_by: str | None = None


class InvoiceDetailResponse(BaseModel):
    success: bool
    message: str
    data: InvoiceDetailData


class RecordPaymentRequest(BaseModel):
    amount: float = Field(gt=0)
    method: str = "BANK_TRANSFER"
    reference: str | None = None


class RecordPaymentResponse(BaseModel):
    success: bool
    message: str
    data: InvoiceDetailData
