from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class CheckoutRequest(BaseModel):
    shipping_address_id: int | None = None
    billing_address_id: int | None = None
    coupon_code: str | None = Field(
        default=None,
        min_length=2,
        max_length=64,
        description="Optional coupon code to apply at checkout.",
    )
    shipping_total: Decimal = Field(default=0, ge=0)
    tax_total: Decimal = Field(
        default=0,
        ge=0,
        description="Deprecated. Taxes are applied at payment time via /orders/{order_id}/pay.",
    )


class OrderItemRead(ORMModel):
    id: int
    variant_id: int
    variant_sku: str | None = None
    product_id: int | None = None
    product_slug: str | None = None
    product_image_url: str | None = None
    product_image_alt: str | None = None
    product_name_snapshot: str
    sku_snapshot: str
    quantity: int
    unit_price: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    line_total: Decimal


class OrderRead(ORMModel):
    id: int
    user_id: int
    order_number: str
    customer_email: str | None = None
    customer_name: str | None = None
    status: str
    payment_status: str
    fulfillment_status: str
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    shipping_total: Decimal
    grand_total: Decimal
    shipping_address_id: int | None
    billing_address_id: int | None
    payment_provider: str | None = None
    payment_transaction_ref: str | None = None
    payment_record_status: str | None = None
    payment_amount: Decimal | None = None
    payment_currency: str | None = None
    payment_paid_at: datetime | None = None
    placed_at: datetime
    items: list[OrderItemRead] = []


class OrderPageRead(BaseModel):
    items: list[OrderRead]
    total: int
    limit: int
    offset: int
