import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings


def test_security_headers_present(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "content-security-policy" in response.headers
    assert response.headers["content-security-policy"] == "default-src 'self'; frame-ancestors 'none'; base-uri 'self';"


def test_docs_csp_allows_swagger_assets(client: TestClient) -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    csp = response.headers.get("content-security-policy", "")
    assert "https://cdn.jsdelivr.net" in csp
    assert "style-src" in csp
    assert "script-src" in csp


def test_readiness_endpoint_works(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_prod_settings_reject_default_jwt_secret() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            JWT_SECRET_KEY="change-this-in-production",
            DEFAULT_ADMIN_PASSWORD="AnotherStrongPassword@123",
        )


def test_prod_settings_reject_debug_true() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DEBUG=True,
            JWT_SECRET_KEY="real-secret-key",
            DEFAULT_ADMIN_PASSWORD="AnotherStrongPassword@123",
        )


def test_prod_settings_reject_default_admin_password() -> None:
    with pytest.raises(ValidationError):
        Settings(
            APP_ENV="production",
            DEBUG=False,
            JWT_SECRET_KEY="real-secret-key",
            DEFAULT_ADMIN_PASSWORD="Admin@1234",
        )
