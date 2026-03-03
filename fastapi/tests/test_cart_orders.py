import hashlib
import hmac
import json
from decimal import Decimal
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
    assert {"razorpay_upi", "razorpay_card"} == codes


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
        json={"provider": "razorpay_upi", "apply_tax": True, "tax_mode": "percent", "tax_value": "10.00"},
    )
    assert quote_response.status_code == 200

    pay_response = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=customer_auth_headers,
        json={"provider": "razorpay_upi", "apply_tax": True, "tax_mode": "percent", "tax_value": "10.00"},
    )
    assert pay_response.status_code == 400
    assert "Direct /pay is disabled" in pay_response.json()["detail"]
    assert quote_response.json()["tax_amount"] != "0.00"


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


def test_admin_cannot_use_legacy_pay_endpoint(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)

    pay_response = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=admin_auth_headers,
        json={"provider": "razorpay_card", "apply_tax": True, "tax_mode": "fixed", "tax_value": "3.50"},
    )

    assert pay_response.status_code == 400
    assert "Direct /pay is disabled" in pay_response.json()["detail"]


def test_quote_rejects_non_razorpay_provider(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)

    quote_response = client.post(
        f"/api/v1/orders/{order['id']}/payment/quote",
        headers=customer_auth_headers,
        json={
            "provider": "manual_free",
            "apply_tax": True,
            "tax_mode": "percent",
            "tax_value": "8.00",
        },
    )

    assert quote_response.status_code == 422


def test_legacy_pay_endpoint_is_consistently_disabled(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)

    first = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=customer_auth_headers,
        json={"provider": "razorpay_upi"},
    )
    assert first.status_code == 400

    second = client.post(
        f"/api/v1/orders/{order['id']}/pay",
        headers=customer_auth_headers,
        json={"provider": "razorpay_upi"},
    )
    assert second.status_code == 400


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


def test_delivery_charge_applied_for_subtotal_below_1000(
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

    checkout_response = client.post(
        "/api/v1/orders/checkout",
        headers=customer_auth_headers,
        json={"shipping_total": "0.00"},
    )
    assert checkout_response.status_code == 201, checkout_response.text
    order = checkout_response.json()
    assert order["shipping_total"] == "100.00"


def test_checkout_applies_coupon_discount(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
) -> None:
    variant_id = _seed_variant(client, admin_auth_headers)
    add_item_response = client.post(
        "/api/v1/cart/items",
        headers=customer_auth_headers,
        json={"variant_id": variant_id, "quantity": 2},
    )
    assert add_item_response.status_code == 201, add_item_response.text

    coupon_response = client.post(
        "/api/v1/coupons",
        headers=admin_auth_headers,
        json={
            "code": "SAVE10",
            "type": "percent",
            "value": "10.00",
            "is_active": True,
        },
    )
    assert coupon_response.status_code == 201, coupon_response.text

    checkout_response = client.post(
        "/api/v1/orders/checkout",
        headers=customer_auth_headers,
        json={"coupon_code": "SAVE10"},
    )
    assert checkout_response.status_code == 201, checkout_response.text
    order = checkout_response.json()
    assert order["discount_total"] != "0.00"
    assert order["grand_total"] != order["subtotal"]


def test_razorpay_create_order_and_verify_signature_flow(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)
    expected_amount_paise = int((Decimal(order["grand_total"]) * Decimal("100")).quantize(Decimal("1")))

    monkeypatch.setattr("app.services.payment._require_razorpay_credentials", lambda: ("rzp_test_key", "test_secret"))

    def fake_razorpay_request(method: str, path: str, payload: dict | None = None) -> dict:
        if method == "POST" and path == "/orders":
            assert payload is not None
            return {
                "id": "order_rzp_test_1",
                "amount": payload["amount"],
                "currency": payload["currency"],
                "status": "created",
            }
        if method == "GET" and path == "/payments/pay_test_1":
            return {
                "id": "pay_test_1",
                "order_id": "order_rzp_test_1",
                "amount": expected_amount_paise,
                "currency": "INR",
                "status": "captured",
                "method": "upi",
            }
        raise AssertionError(f"Unexpected Razorpay call {method} {path}")

    monkeypatch.setattr("app.services.payment._razorpay_request", fake_razorpay_request)

    create_response = client.post(
        f"/api/v1/orders/{order['id']}/payment/razorpay/order",
        headers=customer_auth_headers,
        json={"provider": "razorpay_upi"},
    )
    assert create_response.status_code == 200, create_response.text
    create_body = create_response.json()
    assert create_body["razorpay_order_id"] == "order_rzp_test_1"

    signature = hmac.new(
        b"test_secret",
        b"order_rzp_test_1|pay_test_1",
        hashlib.sha256,
    ).hexdigest()
    verify_response = client.post(
        f"/api/v1/orders/{order['id']}/payment/razorpay/verify",
        headers=customer_auth_headers,
        json={
            "provider": "razorpay_upi",
            "razorpay_order_id": "order_rzp_test_1",
            "razorpay_payment_id": "pay_test_1",
            "razorpay_signature": signature,
        },
    )
    assert verify_response.status_code == 200, verify_response.text
    verify_body = verify_response.json()
    assert verify_body["payment"]["status"] == "paid"
    assert verify_body["order"]["payment_status"] == "paid"
    assert verify_body["payment"]["transaction_ref"] == "pay_test_1"


def test_razorpay_webhook_marks_order_paid(
    client: TestClient,
    customer_auth_headers: dict[str, str],
    admin_auth_headers: dict[str, str],
    monkeypatch,
) -> None:
    order = _create_order(client, customer_auth_headers, admin_auth_headers)
    monkeypatch.setattr("app.services.payment._require_razorpay_webhook_secret", lambda: "whsec_test")

    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_webhook_1",
                    "amount": int((Decimal(order["grand_total"]) * Decimal("100")).quantize(Decimal("1"))),
                    "currency": "INR",
                    "status": "captured",
                    "notes": {
                        "internal_order_id": str(order["id"]),
                        "provider": "razorpay_upi",
                    },
                }
            }
        },
    }
    raw_payload = json.dumps(webhook_payload, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(b"whsec_test", raw_payload, hashlib.sha256).hexdigest()

    webhook_response = client.post(
        "/api/v1/orders/payment/razorpay/webhook",
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
        content=raw_payload,
    )
    assert webhook_response.status_code == 200, webhook_response.text
    assert webhook_response.json()["status"] == "processed"

    order_response = client.get(f"/api/v1/orders/{order['id']}", headers=customer_auth_headers)
    assert order_response.status_code == 200
    assert order_response.json()["payment_status"] == "paid"
