from fastapi.testclient import TestClient

from tests.helpers import create_category


def _sample_products() -> list[dict]:
    return [
        {
            "id": 101,
            "title": "Demo Import Product",
            "description": "Imported using test payload",
            "category": "demo-import",
            "price": 49.99,
            "discountPercentage": 10,
            "brand": "Demo Brand",
            "sku": "DEMO-IMPORT-101",
            "weight": 1.2,
            "stock": 25,
            "images": ["https://example.com/demo-import-1.jpg"],
            "thumbnail": "https://example.com/demo-import-thumb.jpg",
        }
    ]


def test_customer_cannot_import_products(client: TestClient, customer_auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/products/import/json",
        headers=customer_auth_headers,
        json={"products": _sample_products()},
    )
    assert response.status_code == 403


def test_admin_can_import_products_from_json(client: TestClient, admin_auth_headers: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/products/import/json",
        headers=admin_auth_headers,
        json={"products": _sample_products()},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created_products"] == 1
    assert body["errors"] == []

    products = client.get("/api/v1/products", params={"q": "Demo Import Product"})
    assert products.status_code == 200
    assert any(item["name"] == "Demo Import Product" for item in products.json())


def test_vendor_can_create_product(client: TestClient, admin_auth_headers: dict[str, str], vendor_auth_headers: dict[str, str]) -> None:
    category = create_category(client, admin_auth_headers, name="Vendor Category", slug="vendor-category")

    response = client.post(
        "/api/v1/products",
        headers=vendor_auth_headers,
        json={
            "category_id": category["id"],
            "name": "Vendor Product",
            "slug": "vendor-product",
            "description": "Created by vendor",
            "brand": "Vendor Brand",
            "status": "active",
            "images": [{"image_url": "https://example.com/vendor-product.jpg", "is_primary": True}],
            "variants": [{"sku": "VEN-001", "attributes_json": {"size": "M"}, "price": "19.99"}],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Vendor Product"


def test_import_dummyjson_endpoint_with_mocked_fetch(
    client: TestClient,
    admin_auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.api.v1.endpoints.products.fetch_dummyjson_products",
        lambda limit, skip: _sample_products(),
    )
    response = client.post(
        "/api/v1/products/import/dummyjson",
        headers=admin_auth_headers,
        json={"limit": 1, "skip": 0, "update_existing": False},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "dummyjson"
    assert body["created_products"] == 1
