from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order, Payment

FREE_PAYMENT_GATEWAYS: tuple[dict[str, str | bool], ...] = (
    {
        "code": "manual_free",
        "name": "Manual Free",
        "description": "Internal free gateway. No third-party signup, no gateway fee.",
        "requires_external_account": False,
    },
    {
        "code": "mock_free",
        "name": "Mock Free Sandbox",
        "description": "Simulation gateway for testing success/failure flows with zero gateway fee.",
        "requires_external_account": False,
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


def _calculate_base_amount(order: Order) -> Decimal:
    base = Decimal(order.subtotal) - Decimal(order.discount_total) + Decimal(order.shipping_total)
    if base < Decimal("0.00"):
        return Decimal("0.00")
    return _money(base)


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
    simulate_failure: bool,
    metadata: dict,
) -> tuple[Payment, Order, PaymentQuote]:
    if provider not in SUPPORTED_GATEWAYS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported payment gateway")

    if order.payment_status == "paid":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order already paid")

    quote = build_payment_quote(
        order,
        apply_tax=apply_tax,
        tax_mode=tax_mode,
        tax_value=Decimal(tax_value),
    )

    payment_status = "paid"
    paid_at = datetime.now(timezone.utc)

    # A controllable failure path for QA/UAT when using the mock gateway.
    if provider == "mock_free" and simulate_failure:
        payment_status = "failed"
        paid_at = None

    payment = Payment(
        order_id=order.id,
        provider=provider,
        transaction_ref=_build_transaction_ref(provider),
        amount=quote.total_amount,
        currency=currency,
        status=payment_status,
        paid_at=paid_at,
        raw_payload_json={
            "gateway": provider,
            "gateway_fee": str(quote.gateway_fee),
            "apply_tax": apply_tax,
            "tax_mode": tax_mode,
            "tax_value": str(Decimal(tax_value)),
            "tax_amount": str(quote.tax_amount),
            "base_amount": str(quote.base_amount),
            "total_amount": str(quote.total_amount),
            "metadata": metadata,
            "simulate_failure": simulate_failure,
        },
    )

    db.add(payment)

    if payment_status == "paid":
        order.tax_total = quote.tax_amount
        order.grand_total = quote.total_amount
        order.payment_status = "paid"
        if order.status in {"placed", "pending"}:
            order.status = "processing"
    else:
        order.payment_status = "unpaid"

    db.add(order)
    db.flush()
    db.refresh(payment)
    db.refresh(order)

    return payment, order, quote
