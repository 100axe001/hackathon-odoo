"""Request and response models for fulfillment."""

from pydantic import BaseModel, Field

from app.schemas.auth import ErrorResponse  # noqa: F401  re-exported for routes


class ReservedByRow(BaseModel):
    """Who a slice of the reserved quantity is held for."""

    customer: str
    quotation: str
    qty: int


class StockRow(BaseModel):
    warehouse: str
    product: str
    in_stock: int
    reserved: int
    available: int
    reorder_point: int
    reorder_qty: int
    needs_restock: bool

    # Whose the reserved units are. Empty when nothing is reserved on this row.
    reserved_for: list[ReservedByRow] = []


class ListStockResponse(BaseModel):
    success: bool
    message: str
    data: list[StockRow]


class OrderRow(BaseModel):
    id: str
    order: str
    customer: str
    status: str
    warehouses: str


class ListOrdersResponse(BaseModel):
    success: bool
    message: str
    data: list[OrderRow]


class SplitRow(BaseModel):
    # Ids as well as names: the override posts back rows the server has to
    # attribute, and matching on a display name would break the moment a
    # warehouse is renamed.
    warehouse_id: int | None
    product_id: int
    warehouse: str
    product: str
    qty_fulfilled: int
    est_shipments: int
    cost: float


class SplitData(BaseModel):
    id: str
    customer: str
    status: str
    warehouses: list[SplitRow]
    total_shipments: int
    total_cost: float
    backordered: int
    complete: bool


class SplitResponse(BaseModel):
    success: bool
    message: str
    data: SplitData


class OverrideLine(BaseModel):
    warehouse_id: int
    product_id: int
    qty: int = Field(ge=0)


class OverrideRequest(BaseModel):
    allocations: list[OverrideLine]


class RestockRequest(BaseModel):
    warehouse_id: int
    product_id: int
    qty: int = Field(default=50, ge=1)
