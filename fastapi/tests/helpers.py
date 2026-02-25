from fastapi.testclient import TestClient


def create_category(
    client: TestClient,
    admin_headers: dict[str, str],
    *,
    name: str = "Electronics",
    slug: str = "electronics",
) -> dict:
    response = client.post(
        "/api/v1/categories",
        headers=admin_headers,
        json={
            "name": name,
            "slug": slug,
            "description": "Category description",
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_product(
    client: TestClient,
    admin_headers: dict[str, str],
    *,
    category_id: int,
    slug: str = "iphone-15",
    sku: str = "SKU-IPHONE-15",
    name: str = "iPhone 15",
) -> dict:
    response = client.post(
        "/api/v1/products",
        headers=admin_headers,
        json={
            "category_id": category_id,
            "name": name,
            "slug": slug,
            "description": "Product description",
            "brand": "Apple",
            "status": "active",
            "images": [
                {
                    "image_url": "https://example.com/image.jpg",
                    "alt_text": "product image",
                    "sort_order": 0,
                    "is_primary": True,
                }
            ],
            "variants": [
                {
                    "sku": sku,
                    "attributes_json": {"color": "black", "storage": "128GB"},
                    "price": "999.99",
                    "compare_at_price": "1099.99",
                    "currency": "USD",
                    "weight": "0.200",
                    "is_active": True,
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
