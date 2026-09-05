"""Backend administration: accounts, and the configuration screens."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.users import db_create_user, db_email_exists
from app.logging.setup_logging import get_logger
from app.models.enums import UserRole
from app.models.identity import Customer, User
from app.routes.dependencies import get_db, require_roles
from app.schemas.admin import (
    CreateUserRequest,
    CreateUserResponse,
    CustomerOption,
    ErrorResponse,
    ListCustomersResponse,
    UserData,
)
from app.utils.security import security_util_hash_password

logger = get_logger(__name__)
router = APIRouter()

# Account creation is an admin power. Self-signup deliberately cannot reach it -
# see the comment in routes/auth.py.
require_admin = require_roles({UserRole.ADMIN})


def _conflict(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False, error="Conflict", message=message
        ).model_dump(),
    )


def _bad_request(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=ErrorResponse(
            success=False, error="Bad Request", message=message
        ).model_dump(),
    )


@router.get(
    "/customers",
    response_model=ListCustomersResponse,
    responses={code: {"model": ErrorResponse} for code in (403, 500)},
)
def list_customers(
    db: Session = Depends(get_db), user: User = Depends(require_admin)
) -> ListCustomersResponse:
    """Companies a portal account can be attached to."""
    rows = [
        CustomerOption(id=c.id, name=c.name, tier=c.tier.name)
        for c in db.scalars(select(Customer).order_by(Customer.name)).all()
    ]
    return ListCustomersResponse(
        success=True, message=f"Successfully retrieved {len(rows)} customers", data=rows
    )


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateUserResponse,
    responses={code: {"model": ErrorResponse} for code in (400, 403, 409, 500)},
)
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_admin),
) -> CreateUserResponse:
    """Create an account with a chosen role.

    This is the only path to a CUSTOMER account, and to any privileged internal
    role. Signup cannot reach it, so nobody can register themselves as the
    approver of their own discounts.
    """
    if db_email_exists(db, payload.email):
        raise _conflict("An account with that email already exists")

    if payload.role == UserRole.CUSTOMER:
        if payload.customer_id is None:
            raise _bad_request("A customer account must be linked to a customer")
        if db.get(Customer, payload.customer_id) is None:
            raise _bad_request(f"No customer {payload.customer_id}")
    elif payload.customer_id is not None:
        raise _bad_request("Only a CUSTOMER account may be linked to a customer")

    created = db_create_user(
        db,
        email=payload.email,
        password_hash=security_util_hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        customer_id=payload.customer_id,
    )
    logger.info("%s created account %s (%s)", user.email, created.email, created.role)

    return CreateUserResponse(
        success=True,
        message="Account created",
        data=UserData(
            id=created.id,
            name=created.full_name,
            email=created.email,
            role=created.role,
        ),
    )
