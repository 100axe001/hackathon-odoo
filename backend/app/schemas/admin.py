"""Request and response models for backend administration."""

from pydantic import BaseModel, EmailStr, Field

from app.schemas.auth import ErrorResponse, UserData  # noqa: F401  re-exported


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=120)
    role: str = Field(pattern="^(SALES_REP|SALES_MANAGER|FINANCE|ADMIN|CUSTOMER)$")

    # Required when role is CUSTOMER: it is what scopes them to their own
    # quotations. A customer without one would sign in and see nothing.
    customer_id: int | None = None


class CreateUserResponse(BaseModel):
    success: bool
    message: str
    data: UserData


class CustomerOption(BaseModel):
    id: int
    name: str
    tier: str


class ListCustomersResponse(BaseModel):
    success: bool
    message: str
    data: list[CustomerOption]
