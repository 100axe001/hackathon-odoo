"""Request and response models for quotations and approvals."""

from pydantic import BaseModel, Field

from app.schemas.auth import ErrorResponse  # noqa: F401  re-exported for routes


class QuotationSummary(BaseModel):
    id: str
    customer_name: str
    amount: float
    status: str


class ListQuotationsResponse(BaseModel):
    success: bool
    message: str
    data: list[QuotationSummary]


class LineData(BaseModel):
    id: str
    product: str
    qty: int
    price: float
    discount_pct: float
    limit_pct: float
    status: str


class QuotationDetailData(BaseModel):
    id: str
    number: str
    customer_name: str
    price_list: str
    lines: list[LineData]
    margin: float
    margin_pct: float
    net_total: float

    # The builder needs the stage to know whether it is still editable. Without
    # it the screen kept offering "Submit for Approval" on a quotation that had
    # already been submitted.
    status: str
    risk_level: str | None = None

    # Set only while a Draft is a Draft because a reviewer sent it back. The rep
    # otherwise had no way to tell that from a quotation never submitted, and
    # the reason lived in an audit trail their screen does not show.
    returned_by: str | None = None
    returned_note: str | None = None


class QuotationDetailResponse(BaseModel):
    success: bool
    message: str
    data: QuotationDetailData


class CreateQuotationRequest(BaseModel):
    """Only the customer. rep_id is taken from the session, never from here -
    accepting it would let a rep file a quotation under someone else's name."""

    customer_id: int


class CreateQuotationResponse(BaseModel):
    success: bool
    message: str
    data: "QuotationDetailData"


class StageChangeRequest(BaseModel):
    status: str


class StageChangeResponse(BaseModel):
    success: bool
    message: str
    data: QuotationSummary


class UpsellSuggestion(BaseModel):
    product_id: int
    product: str
    margin_delta: float
    promo_tag: str | None


class UpsellResponse(BaseModel):
    success: bool
    message: str
    data: list[UpsellSuggestion]


class AddLineRequest(BaseModel):
    product_id: int
    qty: int = Field(default=1, ge=1)


class AddLineResponse(BaseModel):
    success: bool
    message: str
    data: "QuotationDetailData"


class PatchDiscountRequest(BaseModel):
    """One line edit. Both fields are optional so the builder can send whichever
    control the rep touched, but sending neither is a no-op and is rejected."""

    discount_pct: float | None = Field(default=None, ge=0, le=100)
    qty: int | None = Field(default=None, ge=1, le=100000)


class LineStatusData(BaseModel):
    status: str
    over_by_pct: float
    allowed_discount_pct: float
    qty: int
    line_total: float
    margin: float
    margin_pct: float


class PatchDiscountResponse(BaseModel):
    success: bool
    message: str
    data: LineStatusData


class SubmitData(BaseModel):
    risk_level: str
    decided_by: str
    blended_score: float
    required_approval: list[str]
    status: str
    explanation: str


class SubmitResponse(BaseModel):
    success: bool
    message: str
    data: SubmitData


class ApprovalRow(BaseModel):
    id: str
    quotation: str
    customer: str
    blended_risk: str
    stage: str
    assigned_to: str


class ListApprovalsResponse(BaseModel):
    success: bool
    message: str
    data: list[ApprovalRow]


class FlaggedLine(BaseModel):
    line: str
    discount_given: float
    limit_allowed: float
    over_by: float


class AuditRow(BaseModel):
    user: str
    action: str
    date: str
    note: str | None


class StepRow(BaseModel):
    role: str
    status: str
    acted_by: str | None


class ApprovalDetailData(BaseModel):
    id: str
    quotation: str
    customer: str
    blended_risk: str
    customer_tier: str
    explanation: str
    lines: list[FlaggedLine]
    stage: str
    steps: list[StepRow]
    audit_trail: list[AuditRow]


class ApprovalDetailResponse(BaseModel):
    success: bool
    message: str
    data: ApprovalDetailData


class DecisionRequest(BaseModel):
    decision: str = Field(pattern="^(approve|return|reject)$")
    comment: str | None = None


class DecisionData(BaseModel):
    status: str
    stage: str | None

    # "forward" | "back" | "stopped" - where the decision sent the quotation.
    direction: str = "forward"
    complete: bool


class DecisionResponse(BaseModel):
    success: bool
    message: str
    data: DecisionData


class ThreadMessage(BaseModel):
    """One entry in the conversation with the customer."""

    author: str
    role: str
    body: str | None
    counter_discount_pct: float | None
    created_at: str


class ThreadResponse(BaseModel):
    success: bool
    message: str
    data: list[ThreadMessage]


class ReplyRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class JourneyStage(BaseModel):
    """One step of quotation-to-cash, and where this deal stands on it."""

    key: str
    label: str
    state: str  # done | current | todo | skipped
    detail: str


class NextAction(BaseModel):
    """What to do next, and who has to do it."""

    label: str
    path: str
    role: str


class JourneyData(BaseModel):
    number: str
    customer: str
    stages: list[JourneyStage]
    next_action: NextAction | None = None


class JourneyResponse(BaseModel):
    success: bool
    message: str
    data: JourneyData
