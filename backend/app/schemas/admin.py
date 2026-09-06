"""Request and response models for backend administration."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.auth import ErrorResponse, UserData  # noqa: F401  re-exported


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=120)
    role: str = Field(pattern="^(SALES_REP|SALES_MANAGER|FINANCE|ADMIN|CUSTOMER)$")

    # Required when role is CUSTOMER: it is what scopes them to their own
    # quotations. A customer without one would sign in and see nothing.
    customer_id: int | None = None


class CreateUserResponse(BaseModel):
    success: bool
    message: str
    data: UserData


class CustomerOption(BaseModel):
    id: int
    name: str
    tier: str


class ListCustomersResponse(BaseModel):
    success: bool
    message: str
    data: list[CustomerOption]


# ############################
# Discount configuration
# ############################


class TierCeiling(BaseModel):
    tier: str
    max_discount: float


class CategoryCeilingRow(BaseModel):
    category: str
    max_discount: float


class RoutingRule(BaseModel):
    range: str
    approval: str


class ChainRow(BaseModel):
    """The chain for one risk level, as roles in the order they must act.

    Sent alongside the prose in RoutingRule because the screen needs both: the
    sentence to read, and the roles to edit.
    """

    level: str
    roles: list[str]


class SaveRoutingRulesRequest(BaseModel):
    """The whole chain, in order. Sent complete because a level that loses a
    step has to actually lose it."""

    rules: list["RoutingRuleInput"]


class RoutingRuleInput(BaseModel):
    level: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    step_order: int = Field(ge=1, le=5)
    role: str = Field(pattern="^(SALES_MANAGER|FINANCE|ADMIN)$")


class UpsellRuleData(BaseModel):
    min_margin_pct: float
    max_suggestions: int


class UpsellRuleResponse(BaseModel):
    success: bool
    message: str
    data: UpsellRuleData


class SaveUpsellRuleRequest(BaseModel):
    min_margin_pct: float = Field(ge=0, le=100)
    max_suggestions: int = Field(ge=1, le=20)


class DiscountConfigData(BaseModel):
    tier_ceilings: list[TierCeiling]
    category_ceilings: list[CategoryCeilingRow]
    routing_rules: list[RoutingRule]
    chain: list[ChainRow]


class DiscountConfigResponse(BaseModel):
    success: bool
    message: str
    data: DiscountConfigData


class SaveDiscountConfigRequest(BaseModel):
    tier_ceilings: list[TierCeiling]
    category_ceilings: list[CategoryCeilingRow]


# ############################
# Warehouses
# ############################


class WarehouseRow(BaseModel):
    id: int | None = None
    name: str
    region: str = ""
    shipping_cost_weight: float = 1.0
    active: bool = True

    # What is actually in it. A warehouse row that shows only a name and a
    # shipping weight cannot answer whether it is worth keeping open.
    product_lines: int = 0
    units_on_hand: int = 0
    units_reserved: int = 0
    units_available: int = 0
    below_reorder: int = 0
    fulfilled_lines: int = 0


class ListWarehousesResponse(BaseModel):
    success: bool
    message: str
    data: list[WarehouseRow]


class SaveWarehousesRequest(BaseModel):
    warehouses: list[WarehouseRow]


# ############################
# Subscription plans
# ############################


class PlanRow(BaseModel):
    id: int | None = None
    name: str
    cycle: str
    price: float
    proration_enabled: bool = True
    refund_window_days: int = 365
    cancellation_fee_pct: float = 0


class ListPlansResponse(BaseModel):
    success: bool
    message: str
    data: list[PlanRow]


class SavePlansRequest(BaseModel):
    plans: list[PlanRow]
