"""Invoices and payments."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.billing import db_get_invoice, db_list_invoices, db_record_payment
from app.logging.setup_logging import get_logger
from app.models.enums import DocType, FulfilStatus, InvoiceStatus, UserRole
from app.models.identity import User
from app.routes.dependencies import get_db, require_internal, require_roles
from app.schemas.billing import (
    ErrorResponse,
    InvoiceDetailData,
    InvoiceDetailResponse,
    InvoiceLineRow,
    InvoiceRow,
    ListInvoicesResponse,
    RecordPaymentRequest,
    RecordPaymentResponse,
)

logger = get_logger(__name__)

# Reading is internal; settling is Finance's job.
require_finance = require_roles({UserRole.FINANCE, UserRole.ADMIN})
router = APIRouter()

# The wireframe's lifecycle on Screen 13.
_STAGES = ["Order Confirmed", "Shipped", "Invoiced", "Paid"]


def _not_found(what: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ErrorResponse(
            success=False, error="Not Found", message=what
        ).model_dump(),
    )


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False, error="Conflict", message=message
        ).model_dump(),
    )


def _parse_id(raw: str) -> int:
    try:
        return int(raw[1:] if raw.startswith("i") else raw)
    except ValueError as e:
        raise _not_found(f"No invoice {raw}") from e


def _stage(invoice) -> str:
    """Where this invoice sits in the order lifecycle.

    Keyed off fulfillment as well as payment: the wireframe's note is that
    nothing is billed before it ships, so the stepper has to reflect shipping.
    """
    if invoice.status == InvoiceStatus.PAID:
        return "Paid"
    shipped = invoice.quotation.fulfillment_status in (
        FulfilStatus.SPLIT_ACCEPTED,
        FulfilStatus.OVERRIDDEN,
        FulfilStatus.SHIPPED,
    )
    return "Invoiced" if shipped else "Order Confirmed"


def _to_detail(invoice) -> InvoiceDetailData:
    return InvoiceDetailData(
        id=f"i{invoice.id}",
        invoice_no=invoice.number,
        customer=invoice.customer.name,
        stage=_stage(invoice),
        status=invoice.status,
        amount=float(invoice.amount),
        paid_amount=float(invoice.paid_amount),
        due_date=invoice.due_date.strftime("%b %d, %Y"),
        issue_date=invoice.issue_date.strftime("%b %d, %Y"),
        doc_type=invoice.doc_type,
        # Never negative: an overpayment is settled, not owed back on this line.
        balance_due=float(
            max(
                Decimal("0"),
                Decimal(str(invoice.amount)) - Decimal(str(invoice.paid_amount)),
            )
        ),
        paid_at=invoice.paid_at.strftime("%b %d, %Y") if invoice.paid_at else None,
        paid_method=invoice.paid_method,
        recorded_by=invoice.recorder.full_name if invoice.recorder else None,
        lines=[
            InvoiceLineRow(
                description=line.description,
                qty=line.qty,
                amount=float(line.amount),
                is_recurring=line.is_recurring,
            )
            for line in invoice.lines
        ],
    )


@router.get(
    "",
    response_model=ListInvoicesResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_invoices(
    db: Session = Depends(get_db), user: User = Depends(require_internal)
) -> ListInvoicesResponse:
    rows = []
    for invoice in db_list_invoices(db):
        try:
            rows.append(
                InvoiceRow(
                    id=f"i{invoice.id}",
                    invoice_no=invoice.number,
                    customer=invoice.customer.name,
                    amount=float(invoice.amount),
                    status=invoice.status,
                    due_date=invoice.due_date.strftime("%b %d, %Y"),
                    line_type=invoice.line_type,
                )
            )
        except (TypeError, ValueError, AttributeError) as e:
            logger.warning("Skipping invoice %s: %s", invoice.id, e)

    return ListInvoicesResponse(
        success=True, message=f"Successfully retrieved {len(rows)} invoices", data=rows
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceDetailResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 500)},
)
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_internal),
) -> InvoiceDetailResponse:
    invoice = db_get_invoice(db, _parse_id(invoice_id))
    if invoice is None:
        raise _not_found(f"No invoice {invoice_id}")

    return InvoiceDetailResponse(
        success=True, message="Invoice retrieved", data=_to_detail(invoice)
    )


@router.post(
    "/{invoice_id}/record-payment",
    response_model=RecordPaymentResponse,
    responses={code: {"model": ErrorResponse} for code in (404, 409, 500)},
)
def record_payment(
    invoice_id: str,
    payload: RecordPaymentRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_finance),
) -> RecordPaymentResponse:
    """Record a payment and update the status. PS section 9 step 8.

    Finance and admin only. PS section 3 puts reconciliation with Finance and
    Operations, and letting the rep who sold the deal also mark it paid removes
    the separation that makes the audit trail worth having. Reading an invoice
    stays open to every internal role.
    """
    invoice = db_get_invoice(db, _parse_id(invoice_id))
    if invoice is None:
        raise _not_found(f"No invoice {invoice_id}")

    if invoice.doc_type == DocType.CREDIT_NOTE:
        # A credit note is money owed to the customer; paying one is meaningless.
        raise _conflict("A credit note cannot take a payment")

    if invoice.status == InvoiceStatus.PAID:
        raise _conflict("This invoice is already paid")

    db_record_payment(
        db,
        invoice,
        amount=Decimal(str(payload.amount)),
        method=payload.method,
        user_id=user.id,
    )
    db.commit()
    logger.info(
        "%s recorded %s on %s -> %s",
        user.full_name,
        payload.amount,
        invoice.number,
        invoice.status,
    )

    return RecordPaymentResponse(
        success=True,
        message=f"Payment recorded, invoice is now {invoice.status}",
        data=_to_detail(invoice),
    )
