from uuid import uuid4

from fastapi.testclient import TestClient

from tests.helpers import create_category, create_product


def _seed_variant(client: TestClient, admin_headers: dict[str, str]) -> int:
    suffix = uuid4().hex[:8]
    category = create_category(client, admin_headers, name=f"Users {suffix}", slug=f"users-{suffix}")
    product = create_product(
        client,
        admin_headers,
        category_id=category["id"],
        slug=f"user-order-{suffix}",
        sku=f"USR-{suffix}",
        name=f"User Product {suffix}",
    )
    return product["variants"][0]["id"]


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


def test_admin_can_list_selected_user_orders(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    variant_id = _seed_variant(client, admin_auth_headers)
    me_response = client.get("/api/v1/auth/me", headers=customer_auth_headers)
    assert me_response.status_code == 200, me_response.text
    customer_id = me_response.json()["id"]

    add_response = client.post(
        "/api/v1/cart/items",
        headers=customer_auth_headers,
        json={"variant_id": variant_id, "quantity": 1},
    )
    assert add_response.status_code == 201, add_response.text

    checkout_response = client.post(
        "/api/v1/orders/checkout",
        headers=customer_auth_headers,
        json={"shipping_total": "5.00"},
    )
    assert checkout_response.status_code == 201, checkout_response.text

    response = client.get(f"/api/v1/users/{customer_id}/orders", headers=admin_auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["user_id"] == customer_id
    assert body[0]["order_number"]
