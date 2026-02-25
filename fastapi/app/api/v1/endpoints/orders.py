from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.order import Order, OrderItem
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.schemas.order import CheckoutRequest, OrderRead
from app.schemas.payment import OrderPaymentRequest, OrderPaymentResult, PaymentGatewayRead, PaymentQuoteRead
from app.services.order import create_order_from_active_cart
from app.services.payment import FREE_PAYMENT_GATEWAYS, build_payment_quote, process_order_payment

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
        "Taxes are not applied at checkout; they are applied at payment time."
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
    summary="List free payment gateway options",
    description="Returns built-in free gateway options. No mandatory third-party payment account is required.",
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
    "/{order_id}/pay",
    response_model=OrderPaymentResult,
    summary="Pay order with free gateway",
    description=(
        "Processes payment for the order using a free gateway option. "
        "Tax is charged only here (when payment is attempted), not at checkout."
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
        simulate_failure=payment_payload.simulate_failure,
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
