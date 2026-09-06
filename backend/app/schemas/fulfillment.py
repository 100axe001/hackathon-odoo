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
    handled_by: str = ""

    # Whose queue this belongs in. The screen defaults to your own orders, and
    # matching on the handler's name client-side would break on two people who
    # share one.
    mine: bool = False


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


class WarehouseLeg(BaseModel):
    """One warehouse's whole contribution to an order - the parcel it ships."""

    warehouse_id: int | None
    warehouse: str
    region: str
    units: int
    product_lines: int
    cost: float


class BackorderRow(BaseModel):
    """Outstanding demand, and whether anywhere can cover it now."""

    product_id: int
    product: str
    qty: int
    available_now: int
    sources: list[str]


class SplitData(BaseModel):
    id: str
    number: str
    customer: str
    status: str
    warehouses: list[SplitRow]
    total_shipments: int
    total_cost: float
    backordered: int
    complete: bool

    # What the screen needs to explain itself: the parcels rather than the
    # rows, what is still outstanding and where it could come from, and which
    # actions are legal from here.
    legs: list[WarehouseLeg] = []
    backorder: list[BackorderRow] = []
    ordered_units: int = 0
    fulfilled_units: int = 0
    can_consolidate: bool = False
    can_ship: bool = False
    shipped_at: str | None = None
    nothing_to_ship: bool = False
    handled_by: str = ""

    # Decided by the server, never by the screen: the same rule answers this and
    # the fulfillment endpoints, so a button cannot offer what the API will refuse.
    can_act: bool = False


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
