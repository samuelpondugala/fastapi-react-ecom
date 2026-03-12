from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel
from app.schemas.order import OrderRead


class PaymentGatewayRead(BaseModel):
    code: str
    name: str
    description: str
    requires_external_account: bool = False
    gateway_fee_note: str = "No gateway fee"
    methods: list[str] = Field(default_factory=list)
    category: str = "online"


class OrderPaymentRequest(BaseModel):
    provider: Literal[
        "razorpay_upi",
        "razorpay_card",
    ] = Field(
        default="razorpay_upi",
        description="Payment gateway option.",
    )
    currency: str = Field(default="INR", min_length=3, max_length=3)

    apply_tax: bool = Field(
        default=False,
        description="Apply tax only at payment time. If false, no tax is charged.",
    )
    tax_mode: Literal["none", "fixed", "percent"] = Field(
        default="none",
        description="Tax mode used only when apply_tax=true.",
    )
    tax_value: Decimal = Field(
        default=Decimal("0.00"),
        ge=0,
        description="For fixed: amount. For percent: percentage value (e.g. 18 for 18%).",
    )

    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tax_inputs(self) -> "OrderPaymentRequest":
        if not self.apply_tax:
            self.tax_mode = "none"
            self.tax_value = Decimal("0.00")
            return self

        if self.tax_mode == "none":
            raise ValueError("tax_mode must be fixed or percent when apply_tax=true")

        return self


class RazorpayOrderCreateRequest(BaseModel):
    provider: Literal["razorpay_upi", "razorpay_card"] = Field(
        default="razorpay_upi",
        description="Razorpay checkout mode.",
    )
    metadata: dict = Field(default_factory=dict)


class RazorpayOrderCreateRead(BaseModel):
    key_id: str
    provider: str
    internal_order_id: int
    order_number: str
    razorpay_order_id: str
    amount: int
    currency: str
    status: str


class RazorpayPaymentVerifyRequest(BaseModel):
    provider: Literal["razorpay_upi", "razorpay_card"] = Field(default="razorpay_upi")
    razorpay_order_id: str = Field(min_length=6, max_length=128)
    razorpay_payment_id: str = Field(min_length=6, max_length=128)
    razorpay_signature: str = Field(min_length=32, max_length=256)
    metadata: dict = Field(default_factory=dict)


class PaymentRead(ORMModel):
    id: int
    order_id: int
    provider: str
    transaction_ref: str
    amount: Decimal
    currency: str
    status: str
    paid_at: datetime | None
    raw_payload_json: dict | None


class PaymentQuoteRead(BaseModel):
    base_amount: Decimal
    tax_amount: Decimal
    gateway_fee: Decimal
    total_amount: Decimal


class OrderPaymentResult(BaseModel):
    order: OrderRead
    payment: PaymentRead
    quote: PaymentQuoteRead
