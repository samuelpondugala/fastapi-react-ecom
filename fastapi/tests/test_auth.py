from fastapi.testclient import TestClient


def test_register_user_success(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "StrongPass123!", "full_name": "New User"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "newuser@example.com"
    assert body["role"] == "customer"


def test_register_duplicate_email_fails(client: TestClient) -> None:
    payload = {"email": "dupe@example.com", "password": "StrongPass123!", "full_name": "Dup User"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


def test_login_wrong_password_fails(client: TestClient, create_user) -> None:
    create_user(email="user@example.com", password="CorrectPass123!")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "WrongPass123!"},
    )

    assert response.status_code == 401


def test_login_inactive_user_fails(client: TestClient, create_user) -> None:
    create_user(email="inactive@example.com", password="StrongPass123!", is_active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "StrongPass123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User is inactive"


def test_auth_me_requires_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_login_requires_email_or_username(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"password": "StrongPass123!"},
    )
    assert response.status_code == 422


def test_login_with_username_success(client: TestClient, create_user) -> None:
    create_user(email="ecomadmin@example.com", password="ecom@123admin", role="admin")

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "ecomadmin", "password": "ecom@123admin"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_with_seeded_display_name_success(client: TestClient, create_user) -> None:
    create_user(
        email="staff-account@example.com",
        password="ecom@123vendor",
        role="vendor",
        full_name="ecomvendor",
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "ecomvendor", "password": "ecom@123vendor"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()
