from uuid import uuid4

from fastapi.testclient import TestClient

from tests.helpers import create_category, create_product


def _seed_product(client: TestClient, admin_headers: dict[str, str]) -> int:
    suffix = uuid4().hex[:8]
    category = create_category(client, admin_headers, name=f"Books {suffix}", slug=f"books-{suffix}")
    product = create_product(
        client,
        admin_headers,
        category_id=category["id"],
        slug=f"book-{suffix}",
        sku=f"BOOK-{suffix}",
        name=f"Book {suffix}",
    )
    return product["id"]


def test_create_review_for_missing_product_fails(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/reviews",
        headers=customer_auth_headers,
        json={"product_id": 9999, "rating": 5, "title": "Great", "comment": "Nice"},
    )
    assert response.status_code == 404


def test_create_duplicate_review_fails(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    product_id = _seed_product(client, admin_auth_headers)

    first = client.post(
        "/api/v1/reviews",
        headers=customer_auth_headers,
        json={"product_id": product_id, "rating": 4, "title": "Good", "comment": "Works"},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/reviews",
        headers=customer_auth_headers,
        json={"product_id": product_id, "rating": 5, "title": "Great", "comment": "Even better"},
    )
    assert second.status_code == 409


def test_non_admin_cannot_create_coupon(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/coupons",
        headers=customer_auth_headers,
        json={"code": "SAVE10", "type": "percent", "value": "10.00", "is_active": True},
    )
    assert response.status_code == 403


def test_duplicate_coupon_code_fails(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    payload = {"code": "SAVE20", "type": "percent", "value": "20.00", "is_active": True}
    assert client.post("/api/v1/coupons", headers=admin_auth_headers, json=payload).status_code == 201

    response = client.post("/api/v1/coupons", headers=admin_auth_headers, json=payload)
    assert response.status_code == 409


def test_update_missing_address_fails(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.patch(
        "/api/v1/addresses/me/9999",
        headers=customer_auth_headers,
        json={"city": "New City"},
    )
    assert response.status_code == 404


def test_delete_missing_address_fails(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.delete("/api/v1/addresses/me/9999", headers=customer_auth_headers)
    assert response.status_code == 404
