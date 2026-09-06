"""Response models for the Deal Health dashboard."""

from pydantic import BaseModel

from app.schemas.auth import ErrorResponse  # noqa: F401  re-exported for routes


class FlagRow(BaseModel):
    id: str
    quotation_id: str
    deal: str
    issue: str
    severity: str
    flagged: str
    action: str | None


class DealHealthData(BaseModel):
    stalled: list[FlagRow]
    anomalies: list[FlagRow]
    slippage: list[FlagRow]


class DealHealthResponse(BaseModel):
    success: bool
    message: str
    data: DealHealthData


class FlagActionData(BaseModel):
    id: str
    action: str


class FlagActionResponse(BaseModel):
    success: bool
    message: str
    data: FlagActionData
