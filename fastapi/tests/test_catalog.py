from fastapi.testclient import TestClient

from tests.helpers import create_category, create_product


def test_non_admin_cannot_create_category(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/categories",
        headers=customer_auth_headers,
        json={"name": "Electronics", "slug": "electronics", "description": "desc", "is_active": True},
    )
    assert response.status_code == 403


def test_admin_duplicate_category_slug_fails(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    create_category(client, admin_auth_headers, name="Electronics", slug="electronics")

    response = client.post(
        "/api/v1/categories",
        headers=admin_auth_headers,
        json={"name": "Electronics 2", "slug": "electronics", "description": "desc", "is_active": True},
    )
    assert response.status_code == 409


def test_create_product_with_missing_category_fails(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/products",
        headers=admin_auth_headers,
        json={
            "category_id": 999,
            "name": "Ghost Product",
            "slug": "ghost-product",
            "description": "desc",
            "brand": "Brand",
            "status": "active",
            "images": [],
            "variants": [],
        },
    )
    assert response.status_code == 404


def test_create_product_duplicate_slug_fails(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    category = create_category(client, admin_auth_headers, name="Phones", slug="phones")
    create_product(client, admin_auth_headers, category_id=category["id"], slug="iphone-15", sku="SKU-1")

    response = client.post(
        "/api/v1/products",
        headers=admin_auth_headers,
        json={
            "category_id": category["id"],
            "name": "iPhone Duplicate",
            "slug": "iphone-15",
            "description": "desc",
            "brand": "Apple",
            "status": "active",
            "images": [],
            "variants": [
                {
                    "sku": "SKU-2",
                    "attributes_json": {"color": "blue"},
                    "price": "899.99",
                    "currency": "INR",
                    "is_active": True,
                }
            ],
        },
    )

    assert response.status_code == 409


def test_create_product_duplicate_sku_fails(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    category = create_category(client, admin_auth_headers, name="Tablets", slug="tablets")
    create_product(client, admin_auth_headers, category_id=category["id"], slug="tablet-a", sku="SKU-SHARED")

    response = client.post(
        "/api/v1/products",
        headers=admin_auth_headers,
        json={
            "category_id": category["id"],
            "name": "Tablet B",
            "slug": "tablet-b",
            "description": "desc",
            "brand": "BrandX",
            "status": "active",
            "images": [],
            "variants": [
                {
                    "sku": "SKU-SHARED",
                    "attributes_json": {"size": "10in"},
                    "price": "499.99",
                    "currency": "INR",
                    "is_active": True,
                }
            ],
        },
    )

    assert response.status_code == 409


def test_get_missing_product_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/products/99999")
    assert response.status_code == 404
