"""Test fixtures. Each test module gets a database of its own state."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

os.environ.setdefault("TEST_MODE", "true")

# `import app.models.identity` binds the name `app` to our package, which would
# shadow the FastAPI instance if that were also called `app`. Importing the
# models first and aliasing the instance keeps the two apart.
import app.models  # noqa: E402,F401  registers every model
from app.database.connection import Base, SessionLocal, engine  # noqa: E402
from main import app as fastapi_app  # noqa: E402
from seed import seed  # noqa: E402


@pytest.fixture(scope="function", autouse=True)
def fresh_database():
    """Drop, recreate and reseed around every test.

    Slower than a shared database, but it means one test cannot leave state that
    makes another pass or fail by accident.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session: Session = SessionLocal()
    try:
        seed(session)
    finally:
        session.close()

    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(fastapi_app)


@pytest.fixture
def rep_client(client: TestClient) -> TestClient:
    """A client already signed in as a sales rep."""
    client.post(
        "/auth/login",
        json={"email": "rep@dealflow360.com", "password": "dealflow123"},
    )
    return client
