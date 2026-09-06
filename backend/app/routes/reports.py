"""Reporting aggregates."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.reports import (
    ReportFilters,
    db_avg_approval_hours,
    db_count_quotations,
    db_filter_options,
    db_rep_breakdown,
    db_status_breakdown,
    db_top_product,
)
from app.logging.setup_logging import get_logger
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal
from app.schemas.reports import (
    ErrorResponse,
    FilterOptions,
    ReportsData,
    ReportsResponse,
    RepRow,
    StatusRow,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "",
    response_model=ReportsResponse,
    responses={500: {"model": ErrorResponse}},
)
def get_reports(
    days: int | None = Query(default=None, ge=1, le=3650),
    rep: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> ReportsResponse:
    """Numbers computed from the data, not stored counters.

    The three filters narrow every aggregate together, so the headline figures
    and the tables below them always describe the same slice.
    """
    filters = ReportFilters(days=days, rep=rep, category=category)
    try:
        by_status = db_status_breakdown(db, filters)
        by_rep = db_rep_breakdown(db, filters)
        top = db_top_product(db, filters)
        reps, categories = db_filter_options(db)

        return ReportsResponse(
            success=True,
            message="Reports retrieved",
            data=ReportsData(
                quotes_created=db_count_quotations(db, filters),
                avg_approval_hours=db_avg_approval_hours(db),
                top_product=top["name"] if top else "-",
                pipeline_value=sum(row[2] for row in by_status),
                by_status=[
                    StatusRow(status=s, count=c, value=v) for s, c, v in by_status
                ],
                by_rep=[
                    RepRow(rep=r, quotations=q, value=v, flagged_lines=f)
                    for r, q, v, f in by_rep
                ],
                filter_options=FilterOptions(reps=reps, categories=categories),
            ),
        )
    except Exception as e:
        logger.error("Reports failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                success=False,
                error="Internal Server Error",
                message=f"Unable to build reports: {e}",
            ).model_dump(),
        ) from e
