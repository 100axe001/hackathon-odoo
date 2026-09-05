"""Authentication: sign up, sign in, current session, sign out."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.users import db_create_user, db_email_exists, db_get_user_by_email
from app.logging.setup_logging import get_logger
from app.models.enums import UserRole
from app.models.identity import User
from app.routes.dependencies import get_current_user, get_db
from app.schemas.auth import (
    ErrorResponse,
    LoginRequest,
    LogoutResponse,
    SessionResponse,
    SignupRequest,
    UserData,
)
from app.utils.security import (
    security_util_create_token,
    security_util_hash_password,
    security_util_verify_password,
)

logger = get_logger(__name__)
router = APIRouter()


def _invalid_credentials() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ErrorResponse(
            success=False,
            error="Unauthorized",
            # Deliberately does not say which half was wrong: telling an
            # attacker the email exists is free reconnaissance.
            message="Incorrect email or password",
        ).model_dump(),
    )


def _email_taken() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=ErrorResponse(
            success=False,
            error="Conflict",
            message="An account with that email already exists",
        ).model_dump(),
    )


def _internal_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=ErrorResponse(
            success=False, error="Internal Server Error", message=message
        ).model_dump(),
    )


def _to_user_data(user: User) -> UserData:
    return UserData(id=user.id, name=user.full_name, email=user.email, role=user.role)


def _set_session_cookie(response: Response, user: User) -> None:
    token = security_util_create_token(user.id, user.role)
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


@router.post(
    "/login",
    response_model=SessionResponse,
    responses={code: {"model": ErrorResponse} for code in (401, 500)},
)
def login(
    payload: LoginRequest, response: Response, db: Session = Depends(get_db)
) -> SessionResponse:
    """Exchange credentials for a session cookie."""
    user = db_get_user_by_email(db, payload.email)

    # Verify even when the user is missing, so a wrong email and a wrong
    # password take the same time and cannot be told apart by timing.
    stored = user.password_hash if user else "$2b$12$" + "." * 53
    ok = security_util_verify_password(payload.password, stored)

    if not user or not ok:
        logger.info("Failed login for %s", payload.email)
        raise _invalid_credentials()

    _set_session_cookie(response, user)
    logger.info("User %s signed in as %s", user.email, user.role)

    return SessionResponse(success=True, message="Signed in", data=_to_user_data(user))


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=SessionResponse,
    responses={code: {"model": ErrorResponse} for code in (409, 500)},
)
def signup(
    payload: SignupRequest, response: Response, db: Session = Depends(get_db)
) -> SessionResponse:
    """Create an internal account and sign it in.

    Self-signup always yields SALES_REP. Manager, finance and admin are granted
    by an admin, never chosen by the person signing up - otherwise anyone could
    register themselves as the approver of their own discounts.
    """
    if db_email_exists(db, payload.email):
        raise _email_taken()

    try:
        user = db_create_user(
            db,
            email=payload.email,
            password_hash=security_util_hash_password(payload.password),
            full_name=payload.full_name,
            role=UserRole.SALES_REP,
        )
    except Exception as e:
        logger.error("Signup failed for %s: %s", payload.email, e)
        raise _internal_error("Unable to create the account") from e

    _set_session_cookie(response, user)
    logger.info("Created account %s", user.email)

    return SessionResponse(
        success=True, message="Account created", data=_to_user_data(user)
    )


@router.get(
    "/me",
    response_model=SessionResponse,
    responses={code: {"model": ErrorResponse} for code in (401, 500)},
)
def me(user: User = Depends(get_current_user)) -> SessionResponse:
    """Who the caller is. The frontend calls this on load to restore a session."""
    return SessionResponse(
        success=True, message="Session active", data=_to_user_data(user)
    )


@router.post("/logout", response_model=LogoutResponse)
def logout(response: Response) -> LogoutResponse:
    """Clear the session cookie.

    No authentication required: signing out while already signed out should
    succeed quietly rather than error.
    """
    response.delete_cookie(settings.cookie_name, path="/")
    return LogoutResponse(success=True, message="Signed out")
