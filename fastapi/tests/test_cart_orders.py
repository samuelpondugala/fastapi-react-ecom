from uuid import uuid4

from fastapi.testclient import TestClient

from tests.helpers import create_category, create_product


def _seed_variant(client: TestClient, admin_headers: dict[str, str]) -> int:
    suffix = uuid4().hex[:8]
    category = create_category(client, admin_headers, name=f"Phones {suffix}", slug=f"phones-{suffix}")
    product = create_product(
        client,
        admin_headers,
        category_id=category["id"],
        slug=f"phone-{suffix}",
        sku=f"SKU-{suffix}",
        name=f"Phone {suffix}",
    )
    return product["variants"][0]["id"]


def _create_order(client: TestClient, customer_headers: dict[str, str], admin_headers: dict[str, str]) -> dict:
    variant_id = _seed_variant(client, admin_headers)
    add_item_response = client.post(
        "/api/v1/cart/items",
        headers=customer_headers,
        json={"variant_id": variant_id, "quantity": 1},
    )
    assert add_item_response.status_code == 201

    checkout_response = client.post(
        "/api/v1/orders/checkout",
        headers=customer_headers,
        json={"shipping_total": "5.00", "tax_total": "99.00"},
    )
    assert checkout_response.status_code == 201
    return checkout_response.json()


def test_add_cart_item_invalid_variant_fails(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/cart/items",
        headers=customer_auth_headers,
        json={"variant_id": 9999, "quantity": 1},
    )
    assert response.status_code == 404


def test_update_missing_cart_item_fails(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.patch(
        "/api/v1/cart/items/9999",
        headers=customer_auth_headers,
        json={"quantity": 2},
    )
    assert response.status_code == 404


def test_checkout_empty_cart_fails(
    client: TestClient,
    customer_auth_headers: dict[str, str],
) -> None:
    response = client.post(
        "/api/v1/orders/checkout",
        headers=customer_auth_headers,
        json={"shipping_total": "5.00", "tax_total": "1.00"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"


def test_checkout_invalid_shipping_address_fails(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    variant_id = _seed_variant(client, admin_auth_headers)

    add_item_response = client.post(
        "/api/v1/cart/items",
        headers=customer_auth_headers,
        json={"variant_id": variant_id, "quantity": 1},
    )
    assert add_item_response.status_code == 201

    response = client.post(
        "/api/v1/orders/checkout",
        headers=customer_auth_headers,
        json={"shipping_address_id": 9999, "shipping_total": "5.00", "tax_total": "1.00"},
    )
    assert response.status_code == 404


def test_user_cannot_view_other_users_order(
    client: TestClient,
    login_and_get_headers,
    admin_auth_headers: dict[str, str],
) -> None:
    buyer1_headers = login_and_get_headers(email="buyer1@example.com", password="Buyer1Pass123!")
    buyer2_headers = login_and_get_headers(email="buyer2@example.com", password="Buyer2Pass123!")

    order = _create_order(client, buyer1_headers, admin_auth_headers)
    response = client.get(f"/api/v1/orders/{order['id']}", headers=buyer2_headers)
    assert response.status_code == 403


def test_free_gateway_list_endpoint(client: TestClient, customer_auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/orders/payment-gateways/free", headers=customer_auth_headers)
    assert response.status_code == 200
    codes = {gateway["code"] for gateway in response.json()}
    assert {"manual_free", "mock_free"}.issubset(codes)


def test_tax_is_not_applied_at_checkout_but_at_payment(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)

    # Checkout ignores provided tax_total now; tax is deferred to payment stage.
    assert order["tax_total"] == "0.00"

    quote_response = client.post(
        f"/api/v1/orders/{order['id']}/payment/quote",
        headers=customer_auth_headers,
        json={"provider": "manual_free", "apply_tax": True, "tax_mode": "percent", "tax_value": "10.00"},
    )
    assert quote_response.status_code == 200

    pay_response = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=customer_auth_headers,
        json={"provider": "manual_free", "apply_tax": True, "tax_mode": "percent", "tax_value": "10.00"},
    )
    assert pay_response.status_code == 200

    body = pay_response.json()
    assert body["payment"]["status"] == "paid"
    assert body["order"]["payment_status"] == "paid"
    assert body["quote"]["tax_amount"] != "0.00"
    assert body["order"]["tax_total"] == body["quote"]["tax_amount"]


def test_user_cannot_pay_other_users_order(
    client: TestClient,
    login_and_get_headers,
    admin_auth_headers: dict[str, str],
) -> None:
    buyer1_headers = login_and_get_headers(email="buyer1@example.com", password="Buyer1Pass123!")
    buyer2_headers = login_and_get_headers(email="buyer2@example.com", password="Buyer2Pass123!")

    order = _create_order(client, buyer1_headers, admin_auth_headers)
    response = client.post(f"/api/v1/orders/{order['id']}/pay", headers=buyer2_headers)
    assert response.status_code == 403


def test_admin_can_pay_any_order(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)

    pay_response = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=admin_auth_headers,
        json={"provider": "manual_free", "apply_tax": True, "tax_mode": "fixed", "tax_value": "3.50"},
    )

    assert pay_response.status_code == 200
    assert pay_response.json()["order"]["payment_status"] == "paid"
    assert pay_response.json()["order"]["status"] == "processing"


def test_mock_gateway_failure_does_not_mark_order_paid(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)

    pay_response = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=customer_auth_headers,
        json={
            "provider": "mock_free",
            "apply_tax": True,
            "tax_mode": "percent",
            "tax_value": "8.00",
            "simulate_failure": True,
        },
    )

    assert pay_response.status_code == 200
    assert pay_response.json()["payment"]["status"] == "failed"
    assert pay_response.json()["order"]["payment_status"] == "unpaid"


def test_cannot_pay_order_twice(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)

    first = client.post(f"/api/v1/orders/{order['id']}/pay", headers=customer_auth_headers)
    assert first.status_code == 200

    second = client.post(f"/api/v1/orders/{order['id']}/pay", headers=customer_auth_headers)
    assert second.status_code == 409


def test_cart_is_usable_after_checkout_conversion(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    variant_id = _seed_variant(client, admin_auth_headers)

    add_item_response = client.post(
        "/api/v1/cart/items",
        headers=customer_auth_headers,
        json={"variant_id": variant_id, "quantity": 1},
    )
    assert add_item_response.status_code == 201

    checkout_response = client.post(
        "/api/v1/orders/checkout",
        headers=customer_auth_headers,
        json={"shipping_total": "5.00"},
    )
    assert checkout_response.status_code == 201

    # Regression: this used to fail with 500 because cart creation violated
    # the unique carts.user_id constraint after checkout conversion.
    cart_after_checkout = client.get("/api/v1/cart/me", headers=customer_auth_headers)
    assert cart_after_checkout.status_code == 200, cart_after_checkout.text
    assert cart_after_checkout.json()["status"] == "active"
    assert cart_after_checkout.json()["items"] == []

    add_again = client.post(
        "/api/v1/cart/items",
        headers=customer_auth_headers,
        json={"variant_id": variant_id, "quantity": 2},
    )
    assert add_again.status_code == 201, add_again.text
    assert len(add_again.json()["items"]) == 1


def test_cart_and_order_responses_include_product_media_fields(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    variant_id = _seed_variant(client, admin_auth_headers)

    add_item_response = client.post(
        "/api/v1/cart/items",
        headers=customer_auth_headers,
        json={"variant_id": variant_id, "quantity": 1},
    )
    assert add_item_response.status_code == 201, add_item_response.text

    cart_response = client.get("/api/v1/cart/me", headers=customer_auth_headers)
    assert cart_response.status_code == 200, cart_response.text
    cart_item = cart_response.json()["items"][0]
    assert cart_item["product_id"] is not None
    assert cart_item["product_name"]
    assert cart_item["product_image_url"]
    assert cart_item["variant_sku"]

    checkout_response = client.post(
        "/api/v1/orders/checkout",
        headers=customer_auth_headers,
        json={"shipping_total": "5.00"},
    )
    assert checkout_response.status_code == 201, checkout_response.text
    created_order = checkout_response.json()
    created_item = created_order["items"][0]
    assert created_item["product_id"] == cart_item["product_id"]
    assert created_item["product_image_url"]
    assert created_item["variant_sku"]

    list_response = client.get("/api/v1/orders/me?limit=5", headers=customer_auth_headers)
    assert list_response.status_code == 200, list_response.text
    listed_item = list_response.json()[0]["items"][0]
    assert listed_item["product_image_url"]
    assert listed_item["product_slug"]

    detail_response = client.get(f"/api/v1/orders/{created_order['id']}", headers=customer_auth_headers)
    assert detail_response.status_code == 200, detail_response.text
    detail_item = detail_response.json()["items"][0]
    assert detail_item["product_image_url"]
    assert detail_item["product_slug"]
