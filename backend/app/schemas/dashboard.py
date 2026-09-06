"""Request and response models for the dashboard and product catalogue."""

from pydantic import BaseModel, Field

from app.schemas.auth import ErrorResponse  # noqa: F401  re-exported for routes


class ActivityRow(BaseModel):
    id: str
    text: str
    timestamp: str


class DashboardData(BaseModel):
    pending_approvals: int
    open_quotations: int
    at_risk_deals: int
    recent_activity: list[ActivityRow]


class DashboardResponse(BaseModel):
    success: bool
    message: str
    data: DashboardData


class ProductRow(BaseModel):
    id: str
    name: str
    category: str
    variants: int
    price: float
    unit: str
    tax: str
    status: str


class ListProductsResponse(BaseModel):
    success: bool
    message: str
    data: list[ProductRow]


class PricelistRow(BaseModel):
    tier: str
    currency: str
    rule: str


class ProductStockRow(BaseModel):
    """This product at one warehouse, and what the replenishment rule says."""

    warehouse: str
    region: str
    active: bool
    on_hand: int
    reserved: int
    available: int
    reorder_point: int
    reorder_qty: int
    needs_restock: bool


class ProductDetailData(BaseModel):
    id: str
    name: str
    category: str
    price: float
    cost_price: float
    unit: str
    tax: str
    description: str | None
    subscription: bool
    cadence: str | None
    qty_on_hand: int
    variants: list[dict]
    pricelists: list[PricelistRow]

    # Where the stock actually is. qty_on_hand alone is a single number that
    # cannot answer "can we ship this from one place", which is the question
    # the warehouse split exists to settle.
    stock: list[ProductStockRow] = []
    total_available: int = 0


class ProductDetailResponse(BaseModel):
    success: bool
    message: str
    data: ProductDetailData


class SaveProductRequest(BaseModel):
    """The catalogue fields Screen 17 may change.

    qty_on_hand and variants are deliberately absent: stock moves through
    fulfillment, and variants are display-only.
    """

    name: str = Field(min_length=1, max_length=160)
    category: str = Field(min_length=1, max_length=60)
    unit_price: float = Field(ge=0)
    cost_price: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=24)
    tax_pct: float = Field(ge=0, le=100)
    description: str | None = None
    is_subscription: bool = False
    recurring_cycle: str | None = Field(default=None, max_length=20)
