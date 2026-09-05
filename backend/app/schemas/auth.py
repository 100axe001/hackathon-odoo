"""Request and response models for authentication."""

from pydantic import BaseModel, EmailStr, Field


class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    message: str


class ErrorResponseEnvelope(BaseModel):
    """How an ErrorResponse actually reaches the client.

    HTTPException nests whatever it is given under `detail`, so documenting
    ErrorResponse alone would describe a shape no client ever receives.
    """

    detail: ErrorResponse


# ############################
# Request
# ############################


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=120)


# ############################
# Response
# ############################


class UserData(BaseModel):
    id: int
    name: str
    email: str
    role: str


class SessionResponse(BaseModel):
    success: bool
    message: str
    data: UserData


class LogoutResponse(BaseModel):
    success: bool
    message: str
    data: None = None
