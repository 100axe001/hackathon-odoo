"""Response models for the reporting screen."""

from pydantic import BaseModel

from app.schemas.auth import ErrorResponse  # noqa: F401  re-exported for routes


class StatusRow(BaseModel):
    status: str
    count: int
    value: float


class RepRow(BaseModel):
    rep: str
    quotations: int
    value: float
    flagged_lines: int


class FilterOptions(BaseModel):
    reps: list[str]
    categories: list[str]


class ReportsData(BaseModel):
    quotes_created: int
    avg_approval_hours: float | None
    top_product: str
    pipeline_value: float
    by_status: list[StatusRow]
    by_rep: list[RepRow]
    filter_options: FilterOptions


class ReportsResponse(BaseModel):
    success: bool
    message: str
    data: ReportsData
