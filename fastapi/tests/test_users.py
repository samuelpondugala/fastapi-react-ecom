from fastapi.testclient import TestClient


def test_customer_cannot_list_users(client: TestClient, customer_auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/users", headers=customer_auth_headers)
    assert response.status_code == 403


def test_admin_can_list_users(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/users", headers=admin_auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_customer_cannot_get_other_user_profile(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    create_user,
) -> None:
    other = create_user(email="other@example.com", password="OtherPass123!")

    response = client.get(f"/api/v1/users/{other.id}", headers=customer_auth_headers)
    assert response.status_code == 403


def test_admin_get_nonexistent_user_returns_404(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/users/9999", headers=admin_auth_headers)
    assert response.status_code == 404


def test_update_me_password_validation_error(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.patch(
        "/api/v1/users/me",
        headers=customer_auth_headers,
        json={"password": "short"},
    )
    assert response.status_code == 422
