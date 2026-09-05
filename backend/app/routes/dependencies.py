"""Dependencies shared by the route modules."""

from collections.abc import Callable, Generator, Iterable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.connection import get_session
from app.database.users import db_get_user_by_id
from app.models.enums import INTERNAL_ROLES, UserRole
from app.models.identity import User
from app.schemas.auth import ErrorResponse
from app.utils.security import security_util_decode_token


def get_db() -> Generator[Session, None, None]:
    yield from get_session()


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=ErrorResponse(
            success=False, error="Unauthorized", message=message
        ).model_dump(),
    )


def _forbidden(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=ErrorResponse(
            success=False, error="Forbidden", message=message
        ).model_dump(),
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the caller from the session cookie.

    The cookie is httpOnly, so the browser sends it automatically and page
    scripts cannot read it.
    """
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise _unauthorized("Not signed in")

    claims = security_util_decode_token(token)
    if not claims:
        raise _unauthorized("Session expired or invalid")

    user = db_get_user_by_id(db, int(claims["sub"]))
    if user is None:
        # The token verified but the account is gone - treat it as signed out.
        raise _unauthorized("Account no longer exists")

    return user


def require_roles(allowed: Iterable[str]) -> Callable[[User], User]:
    """Gate a route to a set of roles.

    This is the half that protects data. The frontend's route guard only decides
    what to render; it is not access control.
    """
    allowed = frozenset(allowed)

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise _forbidden(f"Role {user.role} may not access this resource")
        return user

    return _dependency


# Every internal route depends on this; every /portal route uses require_customer.
require_internal = require_roles(INTERNAL_ROLES)
require_customer = require_roles({UserRole.CUSTOMER})
