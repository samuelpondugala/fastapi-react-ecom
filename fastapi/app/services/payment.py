from __future__ import annotations

import base64
import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import Order, Payment

RAZORPAY_API_BASE_URL = "https://api.razorpay.com/v1"

FREE_PAYMENT_GATEWAYS: tuple[dict[str, object], ...] = (
    {
        "code": "razorpay_upi",
        "name": "Razorpay UPI",
        "description": "UPI collection flow via Razorpay integration (configured in production).",
        "requires_external_account": True,
        "gateway_fee_note": "Gateway fee depends on your Razorpay plan",
        "methods": ["upi"],
        "category": "upi",
    },
    {
        "code": "razorpay_card",
        "name": "Razorpay Cards",
        "description": "Credit/Debit card payments via Razorpay.",
        "requires_external_account": True,
        "gateway_fee_note": "Gateway fee depends on your Razorpay plan",
        "methods": ["credit_card", "debit_card"],
        "category": "card",
    },
)

SUPPORTED_GATEWAYS = {gateway["code"] for gateway in FREE_PAYMENT_GATEWAYS}


@dataclass
class PaymentQuote:
    base_amount: Decimal
    tax_amount: Decimal
    gateway_fee: Decimal
    total_amount: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))


def _build_transaction_ref(provider: str) -> str:
    suffix = uuid.uuid4().hex[:16].upper()
    return f"{provider.upper()}-{suffix}"


def _require_razorpay_credentials() -> tuple[str, str]:
    settings = get_settings()
    key_id = (settings.RAZORPAY_KEY_ID or "").strip()
    key_secret = (settings.RAZORPAY_KEY_SECRET or "").strip()
    if not key_id or not key_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Razorpay credentials are not configured on server",
        )
    return key_id, key_secret


def _require_razorpay_webhook_secret() -> str:
    settings = get_settings()
    webhook_secret = (settings.RAZORPAY_WEBHOOK_SECRET or "").strip()
    if not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Razorpay webhook secret is not configured on server",
        )
    return webhook_secret


def _razorpay_request(method: str, path: str, payload: dict | None = None) -> dict:
    key_id, key_secret = _require_razorpay_credentials()
    auth_token = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {auth_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(payload).encode("utf-8") if payload is not None else None

    request = Request(
        f"{RAZORPAY_API_BASE_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="ignore")
        try:
            body_json = json.loads(response_text)
            message = body_json.get("error", {}).get("description") or body_json.get("message")
        except json.JSONDecodeError:
            message = response_text or "Razorpay API request failed"
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=message) from exc
    except URLError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to reach Razorpay API") from exc


def _calculate_base_amount(order: Order) -> Decimal:
    base = Decimal(order.subtotal) - Decimal(order.discount_total) + Decimal(order.shipping_total)
    if base < Decimal("0.00"):
        return Decimal("0.00")
    return _money(base)


def create_razorpay_checkout_order(
    order: Order,
    *,
    provider: str,
    metadata: dict | None = None,
) -> dict[str, object]:
    if provider not in {"razorpay_upi", "razorpay_card"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported Razorpay provider")

    if order.payment_status == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already paid")

    key_id, _ = _require_razorpay_credentials()
    amount_inr = _calculate_base_amount(order)
    amount_paise = int((amount_inr * Decimal("100")).quantize(Decimal("1")))
    notes = {
        "internal_order_id": str(order.id),
        "order_number": order.order_number,
        "provider": provider,
    }
    if metadata:
        notes.update({str(key): str(value) for key, value in metadata.items()})

    gateway_order = _razorpay_request(
        "POST",
        "/orders",
        {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": order.order_number,
            "notes": notes,
        },
    )
    return {
        "key_id": key_id,
        "provider": provider,
        "internal_order_id": order.id,
        "order_number": order.order_number,
        "razorpay_order_id": gateway_order.get("id"),
        "amount": int(gateway_order.get("amount", amount_paise)),
        "currency": str(gateway_order.get("currency", "INR")),
        "status": str(gateway_order.get("status", "created")),
    }


def _verify_razorpay_signature(*, razorpay_order_id: str, razorpay_payment_id: str, razorpay_signature: str) -> None:
    _, key_secret = _require_razorpay_credentials()
    message = f"{razorpay_order_id}|{razorpay_payment_id}".encode("utf-8")
    expected = hmac.new(key_secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, razorpay_signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay signature")


def verify_and_record_razorpay_payment(
    db: Session,
    *,
    order: Order,
    provider: str,
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
    metadata: dict | None = None,
) -> tuple[Payment, Order, PaymentQuote]:
    if provider not in {"razorpay_upi", "razorpay_card"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported Razorpay provider")

    _verify_razorpay_signature(
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
    )

    existing_payment = db.scalar(select(Payment).where(Payment.transaction_ref == razorpay_payment_id))
    if existing_payment:
        if existing_payment.order_id != order.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Payment reference belongs to another order")
        order.payment_status = "paid"
        if order.status in {"placed", "pending", "confirmed"}:
            order.status = "processing"
        db.add(order)
        db.flush()
        db.refresh(order)
        quote = PaymentQuote(
            base_amount=_calculate_base_amount(order),
            tax_amount=Decimal(order.tax_total or 0),
            gateway_fee=Decimal("0.00"),
            total_amount=Decimal(order.grand_total or 0),
        )
        return existing_payment, order, quote

    if order.payment_status == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already paid")

    payment_details = _razorpay_request("GET", f"/payments/{razorpay_payment_id}")
    if str(payment_details.get("order_id") or "") != razorpay_order_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Razorpay order id mismatch")

    expected_amount_paise = int((_calculate_base_amount(order) * Decimal("100")).quantize(Decimal("1")))
    actual_amount_paise = int(payment_details.get("amount") or 0)
    if actual_amount_paise != expected_amount_paise:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount mismatch from Razorpay")

    payment_currency = str(payment_details.get("currency") or "INR").upper()
    if payment_currency != "INR":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unexpected payment currency")

    payment_status = str(payment_details.get("status") or "").lower()
    if payment_status == "authorized":
        captured = _razorpay_request(
            "POST",
            f"/payments/{razorpay_payment_id}/capture",
            {"amount": actual_amount_paise, "currency": "INR"},
        )
        payment_status = str(captured.get("status") or "").lower()
        payment_details = captured

    if payment_status not in {"captured", "paid"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment not captured by Razorpay")

    amount_inr = _money(Decimal(actual_amount_paise) / Decimal("100"))
    payment = Payment(
        order_id=order.id,
        provider=provider,
        transaction_ref=razorpay_payment_id,
        amount=amount_inr,
        currency="INR",
        status="paid",
        paid_at=datetime.now(timezone.utc),
        raw_payload_json={
            "gateway": "razorpay",
            "provider": provider,
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
            "metadata": metadata or {},
            "gateway_payment": payment_details,
        },
    )
    db.add(payment)

    order.payment_status = "paid"
    order.tax_total = Decimal("0.00")
    order.grand_total = amount_inr
    if order.status in {"placed", "pending", "confirmed"}:
        order.status = "processing"
    db.add(order)
    db.flush()
    db.refresh(payment)
    db.refresh(order)

    quote = PaymentQuote(
        base_amount=amount_inr,
        tax_amount=Decimal(order.tax_total or 0),
        gateway_fee=Decimal("0.00"),
        total_amount=amount_inr,
    )
    return payment, order, quote


def process_razorpay_webhook_payload(
    db: Session,
    *,
    raw_body: bytes,
    signature: str | None,
    payload: dict,
) -> dict[str, object]:
    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Razorpay webhook signature")

    webhook_secret = _require_razorpay_webhook_secret()
    expected_signature = hmac.new(webhook_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Razorpay webhook signature")

    event = str(payload.get("event") or "")
    if event not in {"payment.captured", "order.paid"}:
        return {"status": "ignored", "event": event}

    payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    payment_id = str(payment_entity.get("id") or "")
    if not payment_id:
        return {"status": "ignored", "event": event, "reason": "missing_payment_id"}

    notes = payment_entity.get("notes") or {}
    internal_order_id_raw = notes.get("internal_order_id")
    if internal_order_id_raw is None:
        return {"status": "ignored", "event": event, "reason": "missing_internal_order_id"}

    try:
        internal_order_id = int(internal_order_id_raw)
    except (TypeError, ValueError):
        return {"status": "ignored", "event": event, "reason": "invalid_internal_order_id"}

    order = db.scalar(select(Order).where(Order.id == internal_order_id))
    if not order:
        return {"status": "ignored", "event": event, "reason": "order_not_found"}

    existing_payment = db.scalar(select(Payment).where(Payment.transaction_ref == payment_id))
    if not existing_payment:
        amount_paise = int(payment_entity.get("amount") or 0)
        amount_inr = _money(Decimal(amount_paise) / Decimal("100"))
        currency = str(payment_entity.get("currency") or "INR").upper()
        provider = str(notes.get("provider") or "razorpay")
        db.add(
            Payment(
                order_id=order.id,
                provider=provider,
                transaction_ref=payment_id,
                amount=amount_inr,
                currency=currency,
                status="paid",
                paid_at=datetime.now(timezone.utc),
                raw_payload_json={
                    "gateway": "razorpay_webhook",
                    "event": event,
                    "payment": payment_entity,
                },
            )
        )
        order.grand_total = amount_inr
        order.tax_total = Decimal("0.00")

    order.payment_status = "paid"
    if order.status in {"placed", "pending", "confirmed"}:
        order.status = "processing"
    db.add(order)
    db.flush()
    db.refresh(order)
    return {"status": "processed", "event": event, "order_id": order.id, "payment_id": payment_id}


def _calculate_tax(base_amount: Decimal, apply_tax: bool, tax_mode: str, tax_value: Decimal) -> Decimal:
    if not apply_tax:
        return Decimal("0.00")

    if tax_mode == "fixed":
        return _money(tax_value)

    if tax_mode == "percent":
        return _money(base_amount * (tax_value / Decimal("100")))

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tax mode")


def build_payment_quote(order: Order, *, apply_tax: bool, tax_mode: str, tax_value: Decimal) -> PaymentQuote:
    base_amount = _calculate_base_amount(order)
    tax_amount = _calculate_tax(base_amount, apply_tax, tax_mode, Decimal(tax_value))
    gateway_fee = Decimal("0.00")
    total_amount = _money(base_amount + tax_amount + gateway_fee)

    return PaymentQuote(
        base_amount=base_amount,
        tax_amount=tax_amount,
        gateway_fee=gateway_fee,
        total_amount=total_amount,
    )


def process_order_payment(
    db: Session,
    *,
    order: Order,
    provider: str,
    currency: str,
    apply_tax: bool,
    tax_mode: str,
    tax_value: Decimal,
    metadata: dict,
) -> tuple[Payment, Order, PaymentQuote]:
    if provider not in SUPPORTED_GATEWAYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported payment gateway")

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "Direct /pay is disabled for real gateways. "
            "Use /orders/{order_id}/payment/razorpay/order and /orders/{order_id}/payment/razorpay/verify."
        ),
    )
