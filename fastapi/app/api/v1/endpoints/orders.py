import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.order import CheckoutRequest, OrderRead
from app.schemas.payment import (
    OrderPaymentRequest,
    OrderPaymentResult,
    PaymentGatewayRead,
    PaymentQuoteRead,
    RazorpayOrderCreateRead,
    RazorpayOrderCreateRequest,
    RazorpayPaymentVerifyRequest,
)
from app.services.order import create_order_from_active_cart
from app.services.payment import (
    FREE_PAYMENT_GATEWAYS,
    build_payment_quote,
    create_razorpay_checkout_order,
    process_order_payment,
    process_razorpay_webhook_payload,
    verify_and_record_razorpay_payment,
)

router = APIRouter()


ORDER_DETAIL_LOAD = (
    selectinload(Order.items)
    .selectinload(OrderItem.variant)
    .selectinload(ProductVariant.product)
    .selectinload(Product.images)
)


def _authorize_order_access(order: Order, current_user: User) -> None:
    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.scalar(select(Order).options(ORDER_DETAIL_LOAD).where(Order.id == order_id))
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.post(
    "/checkout",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create order from active cart",
    description=(
        "Converts the active cart into an order. "
        "Taxes are not applied at checkout; they are applied at payment time. "
        "Delivery is free for subtotal >= 1000, else 100 is applied."
    ),
)
def checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Order:
    order = create_order_from_active_cart(
        db=db,
        user_id=current_user.id,
        shipping_address_id=payload.shipping_address_id,
        billing_address_id=payload.billing_address_id,
        shipping_total=payload.shipping_total,
        tax_total=payload.tax_total,
        coupon_code=payload.coupon_code,
    )
    db.commit()
    return db.scalar(select(Order).options(ORDER_DETAIL_LOAD).where(Order.id == order.id))


@router.get("/me", response_model=list[OrderRead], summary="List my orders")
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
) -> list[Order]:
    statement = (
        select(Order)
        .options(ORDER_DETAIL_LOAD)
        .where(Order.user_id == current_user.id)
        .order_by(Order.id.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(statement).all())


@router.get(
    "/payment-gateways/free",
    response_model=list[PaymentGatewayRead],
    summary="List payment gateway options",
    description="Returns currently enabled payment providers.",
)
def list_free_gateways() -> list[PaymentGatewayRead]:
    return [PaymentGatewayRead(**gateway) for gateway in FREE_PAYMENT_GATEWAYS]


@router.post(
    "/{order_id}/payment/quote",
    response_model=PaymentQuoteRead,
    summary="Get payment quote for an order",
    description="Calculates base amount, tax (if requested), and total before charging.",
)
def get_payment_quote(
    order_id: int,
    payload: OrderPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaymentQuoteRead:
    order = _get_order_or_404(db, order_id)
    _authorize_order_access(order, current_user)
    quote = build_payment_quote(
        order,
        apply_tax=payload.apply_tax,
        tax_mode=payload.tax_mode,
        tax_value=payload.tax_value,
    )
    return PaymentQuoteRead(
        base_amount=quote.base_amount,
        tax_amount=quote.tax_amount,
        gateway_fee=quote.gateway_fee,
        total_amount=quote.total_amount,
    )


@router.get("/{order_id}", response_model=OrderRead, summary="Get order by id")
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Order:
    order = _get_order_or_404(db, order_id)
    _authorize_order_access(order, current_user)
    return order


@router.post(
    "/{order_id}/payment/razorpay/order",
    response_model=RazorpayOrderCreateRead,
    summary="Create Razorpay checkout order",
)
def create_razorpay_order(
    order_id: int,
    payload: RazorpayOrderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RazorpayOrderCreateRead:
    order = _get_order_or_404(db, order_id)
    _authorize_order_access(order, current_user)
    checkout_order = create_razorpay_checkout_order(
        order,
        provider=payload.provider,
        metadata=payload.metadata,
    )
    return RazorpayOrderCreateRead(**checkout_order)


@router.post(
    "/{order_id}/payment/razorpay/verify",
    response_model=OrderPaymentResult,
    summary="Verify Razorpay payment signature and mark order paid",
)
def verify_razorpay_payment(
    order_id: int,
    payload: RazorpayPaymentVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderPaymentResult:
    order = _get_order_or_404(db, order_id)
    _authorize_order_access(order, current_user)
    payment, order, quote = verify_and_record_razorpay_payment(
        db=db,
        order=order,
        provider=payload.provider,
        razorpay_order_id=payload.razorpay_order_id,
        razorpay_payment_id=payload.razorpay_payment_id,
        razorpay_signature=payload.razorpay_signature,
        metadata=payload.metadata,
    )
    db.commit()

    return OrderPaymentResult(
        order=OrderRead.model_validate(order),
        payment=payment,
        quote=PaymentQuoteRead(
            base_amount=quote.base_amount,
            tax_amount=quote.tax_amount,
            gateway_fee=quote.gateway_fee,
            total_amount=quote.total_amount,
        ),
    )


@router.post(
    "/payment/razorpay/webhook",
    summary="Razorpay webhook callback",
    description="Verifies Razorpay webhook signature and updates order payment state.",
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook JSON payload") from exc

    result = process_razorpay_webhook_payload(
        db=db,
        raw_body=raw_body,
        signature=x_razorpay_signature,
        payload=payload,
    )
    db.commit()
    return result


@router.post(
    "/{order_id}/pay",
    response_model=OrderPaymentResult,
    summary="Legacy direct payment endpoint",
    description=(
        "Direct payment is disabled for real gateways. "
        "Use Razorpay create-order and verify endpoints instead."
    ),
)
def pay_order(
    order_id: int,
    payload: OrderPaymentRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderPaymentResult:
    order = _get_order_or_404(db, order_id)
    _authorize_order_access(order, current_user)

    payment_payload = payload or OrderPaymentRequest()
    payment, order, quote = process_order_payment(
        db=db,
        order=order,
        provider=payment_payload.provider,
        currency=payment_payload.currency,
        apply_tax=payment_payload.apply_tax,
        tax_mode=payment_payload.tax_mode,
        tax_value=payment_payload.tax_value,
        metadata=payment_payload.metadata,
    )
    db.commit()

    return OrderPaymentResult(
        order=OrderRead.model_validate(order),
        payment=payment,
        quote=PaymentQuoteRead(
            base_amount=quote.base_amount,
            tax_amount=quote.tax_amount,
            gateway_fee=quote.gateway_fee,
            total_amount=quote.total_amount,
        ),
    )
