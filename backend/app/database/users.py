"""Data access for users. Every function here is prefixed db_."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import User


def db_get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.lower().strip()))


def db_get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)


def db_create_user(
    session: Session,
    *,
    email: str,
    password_hash: str,
    full_name: str,
    role: str,
    customer_id: int | None = None,
) -> User:
    user = User(
        email=email.lower().strip(),
        password_hash=password_hash,
        full_name=full_name.strip(),
        role=role,
        customer_id=customer_id,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def db_email_exists(session: Session, email: str) -> bool:
    return db_get_user_by_email(session, email) is not None
