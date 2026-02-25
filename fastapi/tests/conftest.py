import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DEFAULT_ADMIN_PASSWORD", "AdminTestPassword@123")

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User

TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    class_=Session,
    future=True,
)


@pytest.fixture(scope="session", autouse=True)
def override_db_dependency() -> Generator[None, None, None]:
    def _override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_db() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def create_user(db_session: Session):
    def _create_user(
        *,
        email: str,
        password: str,
        role: str = "customer",
        is_active: bool = True,
        full_name: str = "Test User",
    ) -> User:
        user = User(
            email=email,
            password_hash=get_password_hash(password),
            role=role,
            is_active=is_active,
            full_name=full_name,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture
def login_and_get_headers(client: TestClient, create_user):
    def _login(*, email: str, password: str, role: str = "customer") -> dict[str, str]:
        create_user(email=email, password=password, role=role)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, response.text
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login


@pytest.fixture
def admin_auth_headers(login_and_get_headers):
    return login_and_get_headers(email="admin@example.com", password="AdminPass123!", role="admin")


@pytest.fixture
def vendor_auth_headers(login_and_get_headers):
    return login_and_get_headers(email="vendor@example.com", password="VendorPass123!", role="vendor")


@pytest.fixture
def customer_auth_headers(login_and_get_headers):
    return login_and_get_headers(email="customer@example.com", password="CustomerPass123!", role="customer")
